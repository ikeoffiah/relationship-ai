"""Background work for the couple thread.

Everything here is deliberately off the request path. The send-time check has a
2.5s budget and most sends never reach a model at all; summarising costs a full
extra round-trip, so it happens after the fact, on a worker.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import CoupleMessage, MessageMedia, Relationship, ThreadSummary

log = logging.getLogger(__name__)

# How long an uploaded file may sit without a message referencing it. Long
# enough to survive a user who picks a photo, gets distracted, and sends it
# twenty minutes later; short enough that abandoned uploads are not storage we
# pay for and would have to enumerate at erasure time.
ORPHAN_TTL_HOURS = 24

# Refresh once the thread has moved on by this many messages. Low enough that
# the summary stays current, high enough that a chatty evening does not queue a
# summarisation per message.
REFRESH_EVERY_MESSAGES = 20

# How much of the tail the summariser reads.
SUMMARISE_WINDOW = 60

_SUMMARY_SYSTEM = (
    "Summarise this couple's recent conversation for an assistant that will "
    "use it as background. Capture recurring themes, what each partner seems "
    "to need, anything that is clearly a sore spot, and the overall warmth or "
    "strain of the exchange. Be factual and brief — at most 120 words. "
    "Do not give advice, do not take a side, and do not quote messages."
)


def summary_is_stale(relationship) -> bool:
    total = CoupleMessage.objects.filter(
        relationship=relationship, deleted_at__isnull=True
    ).count()
    summary = ThreadSummary.objects.filter(relationship=relationship).first()
    covered = summary.covered_message_count if summary else 0
    return total - covered >= REFRESH_EVERY_MESSAGES


@shared_task(name="chat.sweep_orphan_media")
def sweep_orphan_media() -> int:
    """Delete media that no message points at.

    Two ways a blob ends up unreferenced, and this collects both:

    * **Never sent.** The cost of the two-step upload in views.upload_media —
      a client uploads a photo and then does not send it, because the app was
      killed or the user changed their mind.
    * **Sent, then deleted while storage was unavailable.** delete_message
      detaches the media and asks for the bytes; if that call fails, the row is
      left behind with nothing referencing it.

    Filtering on "no message references this" rather than on ``attached_at``
    is what catches the second case. An attached row whose message let go of it
    is exactly as unreachable as one that was never sent, and keying off
    ``attached_at`` alone would leave those blobs live for ever with nothing
    able to find them again.

    One row at a time, and a failure on one does not abandon the rest: storage
    can refuse a single delete, and the next run retries that row because it is
    still unreferenced.
    """
    cutoff = timezone.now() - timedelta(hours=ORPHAN_TTL_HOURS)
    orphans = MessageMedia.objects.filter(
        messages__isnull=True, deleted_at__isnull=True, created_at__lt=cutoff
    )

    swept = 0
    for media in orphans.iterator():
        try:
            media.destroy()
            swept += 1
        except Exception:
            log.exception("orphan_media_sweep_failed media=%s", media.id)

    if swept:
        log.info("orphan_media_swept count=%s", swept)
    return swept


@shared_task(name="chat.refresh_thread_summary")
def refresh_thread_summary(relationship_id) -> str | None:
    """Rewrite the rolling summary for one thread."""
    from . import assist

    relationship = Relationship.objects.filter(id=relationship_id).first()
    if relationship is None:
        return None
    if not assist.settings_for(relationship).assist_enabled:
        return None

    messages = list(
        CoupleMessage.objects.filter(
            relationship=relationship,
            deleted_at__isnull=True,
            kind=CoupleMessage.KIND_TEXT,
        ).order_by("-created_at")[:SUMMARISE_WINDOW]
    )
    if not messages:
        return None
    messages.reverse()

    transcript = "\n".join(f"{m.sender_id}: {m.body}" for m in messages if m.body)
    if not transcript:
        return None

    text = assist._complete(
        _SUMMARY_SYSTEM,
        transcript,
        timeout=20.0,  # generous: nobody is waiting on this
        max_tokens=200,
    )
    if not text:
        return None

    total = CoupleMessage.objects.filter(
        relationship=relationship, deleted_at__isnull=True
    ).count()
    ThreadSummary.objects.update_or_create(
        relationship=relationship,
        defaults={"summary": text, "covered_message_count": total},
    )
    log.info("thread_summary_refreshed relationship=%s", relationship_id)
    return text
