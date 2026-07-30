# Voice notes and photos in the couple thread

A spec for sending images and voice messages in the partner-to-partner thread,
with WhatsApp-level interaction quality and the same encryption posture the
thread's text already has.

Status: proposed. Nothing here is built yet — there is no upload path, storage
backend, or media dependency anywhere in the repo today.

---

## 1. The decision that drives everything else

`apps/chat/models.py` already states the trade: bodies are encrypted at rest
with a key derived from the **relationship id**, and this cannot be an
end-to-end-encrypted product because Bliss reads the thread to coach it
(`assist.py::_thread_context` decrypts recent bodies and feeds them to a model).

So the property the encryption actually buys is: **a leak of the data store
alone yields nothing.** The master secret lives in Django's environment;
whoever owns the app server owns the plaintext, for text and for media alike.

Media must preserve exactly that property and introduce **no new trust
boundary**. That single requirement settles the Cloudinary question:

- **Cloudinary never sees plaintext.** Blobs are encrypted with the same
  AES-GCM + HKDF scheme as message bodies, keyed on the relationship, and
  uploaded as `resource_type: raw`. A Cloudinary breach yields opaque bytes.
- **Clients never talk to Cloudinary.** They cannot — the decryption key is
  derived from the master secret and can never ship to a device. Media is
  proxied through Django, which decrypts on the way out.
- **We therefore lose every Cloudinary transform** (resize, `f_auto`,
  transcode, CDN delivery by URL). Those are replaceable: the client encodes
  and downscales before upload, and Django makes the thumbnail. The trust
  boundary is not replaceable.

The plaintext lifecycle is then identical to text: ciphertext at rest, decrypted
in Django's memory, delivered over TLS. Nothing new to reason about.

**Cost note.** Storing opaque blobs makes Cloudinary a dumb bucket at
media-CDN prices. That is fine to start with — it is what exists — but the
storage adapter (§3) is deliberately a 40-line interface so moving to S3 or B2
is an afternoon, not a migration.

---

## 2. Scope

In: photos (camera + library, with optional caption), voice notes, thumbnails,
upload progress, playback, full-screen image viewer, retry on failure, and
transcription of voice notes so Bliss and the safety layer can see them (§5.1).

Out of v1: video, documents/arbitrary files, GIF search, view-once media,
media forwarding between threads, voice-note auto-advance.

---

## 3. Backend

### 3.1 Byte-level encryption helpers

`utils/encryption.py` today is string-only and base64s its output — wrong shape
for a 500 KB file. Add alongside the existing functions, reusing
`derive_user_key` unchanged so there is one derivation in the codebase:

```python
def encrypt_bytes(data: bytes, scope: str) -> bytes:
    """AES-GCM over raw bytes. Returns nonce(12) || ciphertext."""

def decrypt_bytes(blob: bytes, scope: str) -> bytes:
    """Inverse. Raises on tamper — callers must handle it."""
```

`scope` is `str(relationship_id)`, matching `CoupleMessage.body`. One-shot
AESGCM over an 8 MB ceiling is acceptable memory-wise; do not stream.

Unlike `decrypt()`, which swallows failures and returns `"[ENCRYPTION_ERROR]"`,
`decrypt_bytes` **raises**. A corrupt image must become an "unavailable" bubble,
not a file of garbage bytes handed to a decoder.

### 3.2 Storage adapter

`apps/chat/storage.py` — the whole vendor surface, so it can be swapped:

```python
def put(key: str, blob: bytes) -> None      # upload ciphertext
def get(key: str) -> bytes                  # fetch ciphertext
def delete(key: str) -> None                # hard delete, idempotent
```

Cloudinary implementation: signed upload (`api_secret` server-side only, never
near a client), `resource_type="raw"`, `type="authenticated"`,
`public_id = f"chat/{relationship_id}/{uuid4()}"`. Authenticated delivery is
defence in depth — nothing should be able to fetch a blob by guessing a
`public_id` even though the blob is useless without the key.

Uses the existing `requests` dependency; the `cloudinary` SDK is optional.
New Python deps: `Pillow` only.

### 3.3 Model

Upload and send are **two steps** (§3.4), so media must exist before any message
references it. A separate model, not nullable columns on `CoupleMessage`:

```python
class MessageMedia(models.Model):
    KIND_IMAGE, KIND_VOICE = "image", "voice"

    id            = UUIDField(pk, default=uuid4)
    relationship  = FK(Relationship)          # authorization + key scope
    uploader      = FK(AUTH_USER_MODEL)
    kind          = CharField(choices=[image, voice])

    storage_key   = CharField(max_length=255)
    thumb_key     = CharField(max_length=255, blank=True)   # images only
    mime          = CharField(max_length=64)
    byte_size     = PositiveIntegerField()
    sha256        = CharField(max_length=64)                # integrity + dedupe

    duration_ms   = PositiveIntegerField(null=True)         # voice
    waveform      = JSONField(default=list)                 # voice: ~48 ints 0..100
    width         = PositiveIntegerField(null=True)         # image
    height        = PositiveIntegerField(null=True)

    # Voice transcript (§5). Encrypted like a message body, same relationship
    # scope, exposed through a `transcript` property — never read the column.
    transcript_ciphertext = TextField(blank=True, default="")
    transcript_status     = CharField(  # pending | ok | failed | skipped
        max_length=16, default="skipped"
    )

    created_at    = DateTimeField(auto_now_add=True)
    attached_at   = DateTimeField(null=True)   # set when a message references it
    deleted_at    = DateTimeField(null=True)
```

And on `CoupleMessage`:

```python
KIND_IMAGE = "image"
KIND_VOICE = "voice"
media = FK(MessageMedia, null=True, blank=True, on_delete=models.SET_NULL)
```

`storage_key` is a random opaque id and reveals nothing, so it is stored in the
clear — encrypting it would only break the enumeration that erasure and orphan
sweeps depend on.

An image message with a non-empty `body` **is** a captioned photo. Captions cost
zero schema work.

Extend `_with_relations` (`views.py:51`) with `"media"` and `"reply_to__media"`.

### 3.4 Endpoints

**`POST /api/v1/chat/<relationship_id>/media`** — multipart.

Fields: `file`, `kind`, and for voice `duration_ms` + `waveform`.

1. `_thread_or_404` for membership (reuse — the 404-not-403 convention matters).
2. Enforce ceilings *before* reading the body into memory (§3.6).
3. Sniff the real type from magic bytes; never trust `Content-Type`.
4. **Images:** decode with Pillow, re-encode JPEG q82, long edge ≤ 1600px,
   **all metadata dropped**. This is the EXIF strip — phone photos carry GPS,
   and a shared album quietly becoming a location history is the most likely
   real-world harm in this feature. Also produce a 320px q70 thumbnail.
   **Voice:** accept `audio/mp4`/`aac` only, no server-side transcode (no
   ffmpeg in the image); the client is responsible for encoding.
5. `encrypt_bytes` each artefact, `storage.put` each.
6. Row saved with `attached_at=None`.
7. Queue moderation (§5).

Returns the media descriptor including **our own** URLs, never Cloudinary's.

**`GET /api/v1/chat/media/<media_id>`** and **`…/thumb`** — membership-checked,
fetch, decrypt, stream out. `Cache-Control: private, no-store` so no proxy or
CDN ever holds plaintext; the app manages its own cache (§4.4). No Range
support in v1 — files are ≤ 8 MB and the client plays from a local copy.

**`POST …/messages/send`** — `SendMessageSerializer` gains `media` (UUID) and
the two new kinds. Validation: media must exist, belong to this relationship,
be unattached, and match the declared kind. On success set `attached_at`. The
existing `client_id` idempotency covers retries unchanged.

### 3.5 Wire format

`CoupleMessageSerializer` gains a nested `media` object (id, kind, mime,
byte_size, duration_ms, waveform, width, height, url, thumb_url, transcript,
transcript_status).

`ReplyPreviewSerializer.get_body` returns `""` for media kinds; the client
renders "📷 Photo" / "🎤 Voice message" from `kind`. The server stays dumb about
presentation, as it already is.

Realtime needs no new event type — media rides inside the existing
`couple_message` payload published in `send_message`.

### 3.6 Ceilings

| | limit |
|---|---|
| Image upload | 8 MB, ≤ 1600px stored |
| Voice | 120 s, 2 MB, mono AAC ~32 kbps |
| Rate | 60 uploads/hour/user |
| Orphan TTL | 24 h |

### 3.7 Lifecycle

- **Orphan sweep** — Celery beat task (`config/celery.py:19` already has a
  schedule) hard-deletes `attached_at IS NULL` rows older than 24 h, blobs
  first. Covers "uploaded, then abandoned the send".
- **Message delete** — `delete_message` currently soft-deletes so replies still
  render. Correct for text; for media the tombstone stays but the **bytes are
  destroyed immediately**. A soft-deleted photo still sitting in a bucket is not
  deleted in any sense a user would recognise.
- **Account deletion is currently a gap.** `apps/accounts/profile/views.py:57`
  deactivates the user; it removes nothing. With media that becomes an erasure
  problem no encryption fixes. A hard-delete path must enumerate
  `MessageMedia` by relationship and destroy every blob. **This must ship with
  the feature, not after it.**
- **Missing blob** — a 404 from storage renders "unavailable", mirroring how a
  body that will not decrypt returns `""` rather than taking down the thread.

---

## 4. Mobile

### 4.1 New packages

`record` (capture + live amplitude stream), `just_audio` (playback + position
stream), `flutter_image_compress` (downscale and strip EXIF on-device),
`path_provider` (cache dir). `image_picker` and `permission_handler` are
already in `pubspec.yaml`.

### 4.2 Send path

`CoupleMessage.pendingMedia(...)` carries a **local file path**, so the bubble
renders from disk the instant the user picks or releases — before a byte is
uploaded. Then: compress → `POST /media` with a Dio progress callback → `send`
with the returned media id → `_replaceByClientId`, exactly as text does today.

Failure keeps the bubble and marks it failed, per the existing rule that a
message vanishing on a flaky connection is worse than one you can see and
retry. `retry()` (`couple_chat_viewmodel.dart:302`) gains a media branch that
reuses an already-uploaded media id rather than re-uploading.

### 4.3 UI

**Composer** (`couple_chat_screen.dart:903`) becomes:
`[sticker] [attach] [TextField] [mic ⇄ send]`.

The trailing button swaps mic → send the moment the field stops being empty,
`AnimatedSwitcher` at 150 ms. This is the WhatsApp gesture vocabulary and it is
why the feature feels like one thing rather than three buttons.

**Hold to record.** Press and hold the mic: the composer collapses into a
recording bar — pulsing red dot, elapsed timer, live waveform driven by
`record`'s amplitude stream, "‹ slide to cancel". Release to send. Drag left
past a threshold cancels with haptic feedback. Drag up locks hands-free
recording and swaps to a stop button. Nothing about this is decorative; each
affordance is the escape hatch for a mis-press, and a voice feature without
them feels hostile.

**Attach** opens a bottom sheet styled like `sticker_picker_sheet.dart`, with
Camera and Photo library. Two options, no file browser.

**Image bubble.** Thumbnail at `AppRadii.lg`, caption below in the same bubble
if present. While uploading: the thumbnail blurred behind a determinate
progress ring with a cancel X. Tap opens a full-screen viewer — Hero
transition, pinch zoom, swipe-down to dismiss, share and save actions.

**Voice bubble.** Play/pause, waveform bars from the stored array, elapsed and
total time, and a 1×/1.5×/2× speed chip. The played portion of the waveform is
`warmCoral`, the rest muted, so progress is legible at a glance without a
scrubber thumb. Drag the waveform to seek.

When `transcript_status == ok`, a small "Transcript" affordance expands the
text inline beneath the waveform (WhatsApp's tap-to-expand, not an always-on
wall of text). It arrives after the bubble does — the voice message never waits
on it — and is simply absent while pending, on failure, or when the couple has
assist switched off.

Ticks, reactions, quote-replies and deletion need no changes — a media message
is a message.

### 4.4 Cache

Decrypted media lands in the app cache dir keyed by media id, with
`NSFileProtectionComplete` and excluded from iCloud backup, and is cleared when
the app locks. The app already has biometric/PIN lock in
`security_settings_screen.dart`; a plaintext photo sitting in a cache folder
walks straight around it.

---

## 5. Safety and privacy

Server-held keys are what make any of this possible — true E2E would make it
impossible, which is the strongest argument for the design in §1.

- **Moderation on upload**, async in Celery, using the existing `openai`
  dependency's image moderation. A positive result blocks delivery and opens a
  `SafetyIncident` in `apps/safety`. Images between partners carry an
  NCII/coercion surface, and a CSAM obligation if a minor ever gets on the
  platform; "we could not see it" is not a defence available to us.
- **Audit**: log upload, download, and hard-delete through the existing
  `AuditLogger`, as `change_password` does.

### 5.1 Voice transcription is in scope

An earlier draft of this spec deferred transcription behind an off-by-default
flag. That was wrong, and the reason is safety rather than features.

`assist.py::_thread_context` builds Bliss's entire view of the conversation
from `message.body`, and skips messages whose body is empty. A voice note has
no body — so it is not merely unreadable to Bliss, it is **invisible**. The
same holds for `ThreadSummary`, `note_send_pattern`, and the nudge machinery.

Worse, the contempt vocabulary (`assist.py:275` onward) runs on the *draft*
before it is sent, and voice has no draft. Untranscribed, someone can say the
harshest thing in the relationship out loud and every coaching and safety
mechanism in the product is blind to it — and voice is precisely where the
loaded messages will go, because it is the more intimate medium.

Shipping voice without transcription does not keep the feature small. It builds
a channel that routes around the product.

### 5.2 How it works

- **Where.** A Celery task fired on *upload*, never in the request path. Same
  posture as `_maybe_refresh_summary` and the best-effort rule in
  `realtime.py`: a failed transcript is "no opinion", exactly as `_complete`
  returns `None`.
- **What.** `gpt-4o-mini-transcribe` through the existing singleton client at
  `assist.py:66` — same key, same connection pool, no new vendor and no new DPA
  entry. Decrypted bytes go from memory straight to the API; plaintext audio
  never touches disk. No language hint: couples code-switch.
- **Where it lands.** `MessageMedia.transcript`, not `CoupleMessage.body`.
  Putting machine-heard text into `body` would conflate it with what a person
  typed and break quote and edit semantics. `_thread_context` gains a one-line
  fallback to the transcript, and every existing consumer picks it up unchanged.
- **Cost.** Verified against OpenAI's pricing page, July 2026:
  `gpt-4o-mini-transcribe` $0.003/min, `gpt-4o-transcribe` and `whisper-1`
  $0.006/min. A couple sending twenty 20-second notes a day is ~6.7 min/day —
  2¢/day, ~60¢/month on mini, double that on whisper. Never the constraint, so
  pick on transcription quality, not price.

  Note the `gpt-4o*-transcribe` per-minute figures are OpenAI's *estimates*:
  those models bill by audio input token, so actual spend moves with speech
  density. Only `whisper-1` is billed per minute outright. If predictable
  per-couple cost ever matters more than accuracy, that is the reason to prefer
  whisper despite the price.
- **Failure.** `transcript_status` moves pending → ok | failed. A failure is
  silent; the bubble simply has no transcript.

### 5.3 Pre-send interception for voice

Because upload precedes send (§3.4), the transcript can exist *before* the
message does — so the caution flow can run on voice as it does on text, gated
on the `interception_enabled` flag already at `models.py:232`. This is the one
place worth accepting ~1–2s of added latency, and only when interception is on.

### 5.4 Consent and retention

- **Consent is a real gate, not a checkbox.** Recording a voice note is one
  thing; having it converted into durable text that an AI reads and a rolling
  summary retains is another. Transcription must honour
  `ChatAssistSettings.assist_enabled` — the couple's existing off-switch — and
  the `consent` app is where the disclosure belongs. With assist off,
  `transcript_status` is `skipped` and no audio leaves the process.
- **Deletion must reach the transcript.** A deleted voice note whose text
  survives inside `ThreadSummary` is the same lie as a deleted photo still
  sitting in a bucket. Hard-delete drops the blob, the transcript, and
  invalidates the summary that absorbed it.
- **The biometric concern is smaller than it sounds.** Transcription extracts
  content; it does not build a voiceprint or identify a speaker, so BIPA and
  GDPR Art. 9 exposure is low. The real exposure is retention of what was said,
  which is the consent question above rather than a biometrics one. The 120s
  cap still keeps a voice note a message rather than a recording.

---

## 6. Tests

Backend: round-trip `encrypt_bytes`/`decrypt_bytes` including a tamper case;
EXIF/GPS is absent after processing; upload rejects oversize, wrong-magic-bytes,
and non-member callers; download 404s for a non-member; send rejects media from
another relationship, already-attached media, and kind mismatch; orphan sweep
deletes blob before row; message delete destroys bytes but keeps the tombstone;
missing blob degrades to "unavailable".

Transcription: the transcript is stored encrypted and is unreadable under the
wrong relationship scope; `_thread_context` includes a voice note's transcript
and still skips one that has none; a transcription failure leaves the message
sendable and readable; `assist_enabled = False` produces `skipped` and makes no
API call; hard-delete removes transcript and blob together and invalidates the
summary.

Mobile: optimistic media bubble renders before upload; failed upload is
retryable; retry does not re-upload; recorder cancel discards; player position
tracks the waveform.

---

## 7. Sequencing

1. **Backend foundation** — byte helpers, storage adapter, model + migration,
   upload/download, send integration, orphan sweep, tests.
2. **Images on mobile** — picker, compress, progress, bubble, viewer.
3. **Voice, end to end** — hold-to-record, waveform, player, *and* the
   transcription task with its `_thread_context` fallback. These ship together:
   voice without transcription is a channel Bliss and the safety layer cannot
   see (§5.1).
4. **Safety and erasure** — image moderation, hard-delete account path
   including transcripts and summaries, consent disclosure, audit.

Step 4 is not optional polish. Shipping 1–3 without it means holding intimate
media with no erasure story, which is a worse position than not shipping the
feature.

---

## 8. Defaults chosen here, worth a second opinion

- Images get captions (free, given `body` already exists).
- No video in v1 — it needs transcoding, which needs ffmpeg, which is a
  different-sized change.
- Downloads proxy through Django rather than signed direct-from-CDN. Costs
  double egress; it is the price of the vendor never holding a key.
- Voice transcription ships with voice, gated on the couple's existing assist
  switch rather than a new one (§5.1–5.4). The live question is not whether to
  transcribe but how loudly to disclose it: an entry in the consent flow, a
  line in the privacy policy, or a one-time in-thread notice the first time
  someone sends a voice note. That last one is the honest option and the one
  most likely to cost a little adoption.
- Pre-send interception for voice (§5.3) adds latency to a send. Worth it while
  interception is on; revisit if p95 upload-to-send gets uncomfortable.
- Cloudinary now, storage adapter so it is not for ever.
