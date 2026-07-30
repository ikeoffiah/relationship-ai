"""Screening photos before they are delivered.

Images between partners are not a neutral surface. A relationship app that
carries them carries an NCII and coercion problem, and a legal obligation if a
minor ever reaches the platform. "We could not see it" is a defence available
to an end-to-end-encrypted messenger and deliberately not to us — the server
holds the keys precisely so that Bliss can coach the conversation, and the same
access is what makes this possible at all.

Screening runs after the upload responds and before the photo is delivered:
the uploader's own optimistic bubble is already on screen, but nothing reaches
the partner until a message is sent, and a blocked photo can never be attached
to one.
"""

import base64
import logging
import os

from celery import shared_task

from .models import MessageMedia

log = logging.getLogger(__name__)

MODERATION_MODEL = os.environ.get("OPENAI_MODERATION_MODEL", "omni-moderation-latest")
MODERATION_TIMEOUT = 30.0

#: Categories that block delivery outright rather than merely being recorded.
#: Deliberately narrow. This is a couple's private thread, and two adults
#: sending each other photographs is the product working — over-blocking here
#: would be both a betrayal and useless, since the categories that matter are
#: the ones about someone who did not consent or could not.
BLOCKING_CATEGORIES = (
    "sexual/minors",
    "violence/graphic",
)


@shared_task(name="chat.moderate_image")
def moderate_image(media_id) -> str | None:
    """Screen one uploaded photo. Returns the verdict, or None if unavailable.

    Fails open, and that is a real decision rather than an oversight. Failing
    closed would mean an OpenAI outage silently stops couples sending each
    other photographs, which is a bigger and more certain harm than the window
    this leaves. The incident record is what makes the window auditable.
    """
    if not os.environ.get("OPENAI_API_KEY"):
        return None

    from utils.encryption import DecryptionError, decrypt_bytes

    from . import assist, storage

    media = MessageMedia.objects.filter(
        id=media_id, kind=MessageMedia.KIND_IMAGE, deleted_at__isnull=True
    ).select_related("relationship").first()
    if media is None:
        return None

    try:
        # The thumbnail, not the full image: it is a twentieth of the bytes and
        # every category here is legible at 320px.
        key = media.thumb_key or media.storage_key
        image = decrypt_bytes(storage.get(key), str(media.relationship_id))
    except (storage.StorageError, DecryptionError):
        log.exception("moderation_unreadable media=%s", media_id)
        return None

    data_url = f"data:image/jpeg;base64,{base64.b64encode(image).decode()}"

    try:
        response = assist._get_client().with_options(
            timeout=MODERATION_TIMEOUT
        ).moderations.create(
            model=MODERATION_MODEL,
            input=[{"type": "image_url", "image_url": {"url": data_url}}],
        )
        result = response.results[0]
    except Exception as exc:
        log.info("moderation_unavailable media=%s: %s", media_id, exc)
        return None

    flagged = _flagged_categories(result)
    blocking = [c for c in flagged if c in BLOCKING_CATEGORIES]

    if blocking:
        _record_incident(media, blocking)
        # Destroy first, mark second. The bytes are the harm; a row saying they
        # were blocked is only bookkeeping.
        try:
            media.destroy()
        except storage.StorageError:
            # Left unreferenced, so the orphan sweep collects it.
            log.exception("blocked_media_not_destroyed media=%s", media_id)
        log.warning("moderation_blocked media=%s categories=%s", media_id, blocking)
        return "blocked"

    if flagged:
        log.info("moderation_flagged media=%s categories=%s", media_id, flagged)
        return "flagged"
    return "ok"


def _flagged_categories(result) -> list[str]:
    categories = getattr(result, "categories", None)
    if categories is None:
        return []
    as_dict = categories.model_dump() if hasattr(categories, "model_dump") else dict(categories)
    return [name.replace("_", "/") for name, hit in as_dict.items() if hit]


def _record_incident(media: MessageMedia, categories: list[str]) -> None:
    """Open a SafetyIncident so a blocked photo is visible to a human.

    Follows the existing model's anonymisation: the uploader is recorded as the
    first eight characters of their id and nothing more. The media id goes in
    ``action_taken`` because a reviewer needs something to act on, and it is an
    opaque UUID that identifies nobody without database access anyway.

    Never raises. Safety bookkeeping failing must not be the reason the bytes
    survive; the destroy above is the part that actually matters.
    """
    try:
        from apps.safety.models import SafetyIncident

        SafetyIncident.objects.create(
            user_id_anon=str(media.uploader_id)[:8],
            severity="critical" if "sexual/minors" in categories else "high",
            category="media_blocked",
            safety_score=1.0,
            layer_detected=1,
            action_taken=(
                f"Image blocked by automated screening ({', '.join(categories)}) "
                f"and destroyed before delivery. media_id={media.id}"
            ),
        )
    except Exception:
        log.exception("moderation_incident_not_recorded media=%s", media.id)
