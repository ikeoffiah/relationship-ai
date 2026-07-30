"""Turning a voice note into text Bliss can read.

Not a feature. ``assist._thread_context`` builds Bliss's entire view of the
conversation out of message bodies and skips the ones that are empty, so an
untranscribed voice note is not merely unreadable — it is *invisible*. The same
goes for the rolling summary and the nudge machinery.

The sharper problem is the contempt vocabulary, which runs on a draft before it
is sent. Voice has no draft. Untranscribed, the harshest thing anyone says in
the relationship can be the one thing every coaching and safety mechanism in
the product cannot see, and voice is exactly where the loaded messages go.

So this exists to keep the couple's own conversation legible to the thing that
is supposed to be helping them with it, and it is gated on the couple's own
assist switch: with assistance off, no audio leaves the process.
"""

import logging
import os

from celery import shared_task

from .models import MessageMedia

log = logging.getLogger(__name__)

#: Half the price of whisper-1 at time of writing ($0.003/min against $0.006),
#: and billed by audio input token rather than by the minute — so real spend
#: moves with speech density. Overridable for the same reason the chat models
#: are: pricing and quality both move.
TRANSCRIBE_MODEL = os.environ.get("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe")

#: Generous. Nobody is waiting on this — the voice note is already in the
#: thread and playable before a word of it has been transcribed.
TRANSCRIBE_TIMEOUT = 60.0


def should_transcribe(relationship) -> bool:
    """Whether this couple has consented to their voice notes being read.

    ``assist_enabled`` is the switch the couple already has for "Bliss reads
    this thread", and transcription is squarely inside what that promises.
    Giving it a second, separate toggle would mean a couple who turned
    assistance off could still have their audio sent to a model, which is
    exactly the surprise the switch exists to prevent.
    """
    from . import assist

    if not os.environ.get("OPENAI_API_KEY"):
        return False
    return assist.settings_for(relationship).assist_enabled


@shared_task(name="chat.transcribe_voice_note")
def transcribe_voice_note(media_id) -> str | None:
    """Transcribe one voice note and store the text against its media row.

    Never raises into anything that matters. A failure leaves the note
    perfectly playable and simply invisible to Bliss, which is the same
    position we were in before this ran.
    """
    from utils.encryption import DecryptionError, decrypt_bytes

    from . import storage

    media = MessageMedia.objects.filter(
        id=media_id, kind=MessageMedia.KIND_VOICE, deleted_at__isnull=True
    ).select_related("relationship").first()
    if media is None:
        return None

    if not should_transcribe(media.relationship):
        media.transcript_status = MessageMedia.TRANSCRIPT_SKIPPED
        media.save(update_fields=["transcript_status"])
        return None

    try:
        audio = decrypt_bytes(storage.get(media.storage_key), str(media.relationship_id))
    except (storage.StorageError, DecryptionError):
        log.exception("transcription_unreadable media=%s", media_id)
        return _fail(media)

    try:
        from . import assist

        # The audio is passed as a named tuple of (filename, bytes) rather than
        # written to a temp file. Plaintext audio should not touch the disk of
        # a worker that might be sharing a host with anything else.
        response = assist._get_client().with_options(
            timeout=TRANSCRIBE_TIMEOUT
        ).audio.transcriptions.create(
            model=TRANSCRIBE_MODEL,
            file=(f"{media.id}.m4a", audio, media.mime or "audio/mp4"),
            # No language hint on purpose: couples code-switch, and forcing a
            # language is how you get a confident transcript of the wrong one.
        )
        text = (getattr(response, "text", "") or "").strip()
    except Exception as exc:
        log.info("transcription_unavailable media=%s: %s", media_id, exc)
        return _fail(media)

    if not text:
        return _fail(media)

    media.transcript = text
    media.transcript_status = MessageMedia.TRANSCRIPT_OK
    media.save(update_fields=["transcript_ciphertext", "transcript_status"])
    log.info("transcription_ok media=%s chars=%s", media_id, len(text))
    return text


def _fail(media: MessageMedia) -> None:
    media.transcript_status = MessageMedia.TRANSCRIPT_FAILED
    media.save(update_fields=["transcript_status"])
    return None
