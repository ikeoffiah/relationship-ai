"""Turning an uploaded file into something safe to store.

Two jobs, both of which must happen before a byte is encrypted or persisted:
decide what the file actually *is*, and strip what it should not be carrying.

The metadata strip is the part most likely to matter in practice. Phone photos
carry GPS coordinates, and a couple's shared album quietly becoming a location
history is a more probable harm than anything the encryption defends against.
Re-encoding through Pillow drops every EXIF tag as a side effect of decoding to
pixels and writing a fresh file — it is not a filter that can miss a tag.
"""

import io
import logging

from PIL import Image, ImageOps

log = logging.getLogger(__name__)

# ── Ceilings (docs/chat-media.md §3.6) ──────────────────────────────────────

MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_VOICE_BYTES = 2 * 1024 * 1024
MAX_VOICE_MS = 120_000

#: Long edge of the stored image. Comfortably above any phone screen, well
#: below what a modern camera produces.
IMAGE_MAX_EDGE = 1600
IMAGE_QUALITY = 82

THUMB_MAX_EDGE = 320
THUMB_QUALITY = 70

#: Waveform buckets sent by the client. Enough to look like speech, few enough
#: to sit in a row of bars on a phone.
WAVEFORM_BUCKETS = 48

IMAGE_MIME = "image/jpeg"
VOICE_MIMES = ("audio/mp4", "audio/aac", "audio/m4a", "audio/x-m4a")


class MediaRejected(Exception):
    """The upload is not something we are willing to store."""


# ── Type sniffing ───────────────────────────────────────────────────────────
# The client's Content-Type is a claim, not evidence. Everything below decides
# from the bytes.

_IMAGE_MAGIC = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)


def sniff_image(blob: bytes) -> str:
    """The real image type, or raise.

    HEIC is deliberately absent: Pillow cannot decode it without a plugin, and
    the client converts to JPEG before upload rather than us carrying an image
    codec we would then have to keep patched.
    """
    for magic, mime in _IMAGE_MAGIC:
        if blob.startswith(magic):
            return mime
    if blob[4:12] in (b"ftypavif", b"ftypavis"):
        return "image/avif"
    raise MediaRejected("Not an image we can read. Send a JPEG or PNG.")


def sniff_audio(blob: bytes) -> str:
    """Confirm an MPEG-4 audio container.

    The client records AAC in an MP4 container, which is what both platforms
    produce natively. Anything else is refused rather than transcoded — a
    server-side transcode would mean carrying ffmpeg, which is a much larger
    thing to own than a format restriction.
    """
    if len(blob) >= 12 and blob[4:8] == b"ftyp":
        brand = blob[8:12]
        if brand in (b"M4A ", b"mp42", b"isom", b"iso2", b"mp41"):
            return "audio/mp4"
    raise MediaRejected("Not an audio file we can read.")


# ── Images ──────────────────────────────────────────────────────────────────


def process_image(blob: bytes) -> tuple[bytes, bytes, int, int]:
    """Normalise an upload into (jpeg, thumbnail, width, height).

    Returns a stripped, downscaled JPEG and a thumbnail for the bubble. Both
    are re-encoded from decoded pixels, so neither carries anything the sender's
    camera attached.
    """
    if len(blob) > MAX_IMAGE_BYTES:
        raise MediaRejected("That photo is too large. The limit is 8 MB.")

    sniff_image(blob)

    try:
        opened = Image.open(io.BytesIO(blob))
        # Cameras store landscape pixels plus an orientation tag. Applying it
        # now means the tag can be dropped without the photo arriving sideways.
        image = ImageOps.exif_transpose(opened) or opened
        image = image.convert("RGB")
    except MediaRejected:
        raise
    except Exception as exc:
        raise MediaRejected("That photo could not be read.") from exc

    image.thumbnail((IMAGE_MAX_EDGE, IMAGE_MAX_EDGE), Image.Resampling.LANCZOS)
    width, height = image.size

    full = io.BytesIO()
    # `exif` is not passed through and Pillow writes none by default; this is
    # the strip. Nothing downstream needs to filter tags because none survive.
    image.save(full, format="JPEG", quality=IMAGE_QUALITY, optimize=True)

    thumb_image = image.copy()
    thumb_image.thumbnail((THUMB_MAX_EDGE, THUMB_MAX_EDGE), Image.Resampling.LANCZOS)
    thumb = io.BytesIO()
    thumb_image.save(thumb, format="JPEG", quality=THUMB_QUALITY, optimize=True)

    return full.getvalue(), thumb.getvalue(), width, height


def has_metadata(blob: bytes) -> bool:
    """Whether a JPEG still carries EXIF. Used by the tests to prove the strip."""
    try:
        image = Image.open(io.BytesIO(blob))
    except Exception:
        return False
    return bool(image.getexif())


# ── Voice ───────────────────────────────────────────────────────────────────


def process_voice(blob: bytes, duration_ms: int) -> tuple[bytes, str]:
    """Validate a voice note. Returns it unchanged, with its real mime type.

    Unlike images there is nothing to strip or resize — the client already
    encoded to the shape we want, and re-containerising audio server-side would
    buy nothing.
    """
    if len(blob) > MAX_VOICE_BYTES:
        raise MediaRejected("That voice note is too long.")
    if duration_ms <= 0:
        raise MediaRejected("A voice note needs a duration.")
    if duration_ms > MAX_VOICE_MS:
        raise MediaRejected("Voice notes are limited to two minutes.")
    return blob, sniff_audio(blob)


def normalise_waveform(raw) -> list[int]:
    """Clamp a client-supplied waveform into ``WAVEFORM_BUCKETS`` ints 0..100.

    Cosmetic data, so a malformed one degrades to a flat bar rather than a 400 —
    but it is still user input reaching a JSON column, so its size and range are
    bounded here rather than trusted.
    """
    if not isinstance(raw, (list, tuple)):
        return []
    values = []
    for item in raw[:WAVEFORM_BUCKETS]:
        try:
            values.append(max(0, min(100, int(item))))
        except (TypeError, ValueError):
            values.append(0)
    return values
