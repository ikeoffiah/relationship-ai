"""HTTP surface for the couple thread.

Every endpoint resolves the relationship through :func:`_thread_or_404`, which
is the single access check: a user may only touch a thread they are a partner
in. It returns 404 rather than 403 on purpose — a stranger probing ids should
not be able to learn which relationships exist.
"""

import logging
from datetime import UTC, datetime

from django.db import IntegrityError, transaction
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.constants import AuditEventType
from apps.audit.logger import AuditLogger
from apps.personalization import outcomes
from apps.relationships.models import Relationship
from utils.encryption import DecryptionError, decrypt_bytes, encrypt_bytes

from . import assist, media as media_processing, moderation, realtime, storage, transcription
from .models import (
    AssistNudge,
    CoupleMessage,
    MessageMedia,
    MessageReaction,
    ReadReceipt,
)
from .serializers import (
    CoupleMessageSerializer,
    MessageMediaSerializer,
    ReactionSerializer,
    SendMessageSerializer,
    UploadMediaSerializer,
)

log = logging.getLogger(__name__)

# History page size. Generous enough that opening the thread rarely needs a
# second round trip, small enough to stay comfortably inside a mobile payload.
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

# A sentinel for "delivered, never opened". ``last_read_at`` is non-null in the
# schema, and widening it to accept null would mean revisiting every existing
# comparison against it; a floor no message can precede does the same job.
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _thread_or_404(user, relationship_id) -> Relationship:
    """Return the relationship only if `user` is one of its partners."""
    relationship = get_object_or_404(Relationship, id=relationship_id)
    if user.id not in (relationship.partner_a_id, relationship.partner_b_id):
        # Deliberately 404, not 403 — see module docstring.
        from django.http import Http404

        raise Http404
    return relationship


def _with_relations(queryset):
    return queryset.select_related(
        "sender", "reply_to", "reply_to__sender", "media", "reply_to__media"
    ).prefetch_related("reactions")


def _partner_id(relationship, user):
    """The other person, or None in a solo relationship."""
    if relationship.partner_a_id == user.id:
        return relationship.partner_b_id
    return relationship.partner_a_id


def _viewer_context(request, relationship) -> dict:
    """Everything the serializer needs to put ticks on the reader's messages.

    One extra query per response, not per message — the partner's cursor is a
    single row that answers the delivery question for the entire page.
    """
    partner_id = _partner_id(relationship, request.user)
    cursor = (
        ReadReceipt.objects.filter(relationship=relationship, user_id=partner_id).first()
        if partner_id
        else None
    )
    return {"viewer_id": request.user.id, "partner_cursor": cursor}


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def messages(request, relationship_id):
    """Newest-first page of the thread.

    Paginates on ``before`` (an ISO timestamp) rather than an offset: the thread
    grows from the bottom while you are reading it, and an offset would silently
    skip or repeat messages as it shifts.
    """
    relationship = _thread_or_404(request.user, relationship_id)

    try:
        limit = int(request.query_params.get("limit", DEFAULT_PAGE_SIZE))
    except (TypeError, ValueError):
        limit = DEFAULT_PAGE_SIZE
    limit = max(1, min(limit, MAX_PAGE_SIZE))

    qs = CoupleMessage.objects.filter(relationship=relationship)
    before = request.query_params.get("before")
    if before:
        parsed = timezone.datetime.fromisoformat(before.replace("Z", "+00:00")) if before else None
        if parsed is not None:
            qs = qs.filter(created_at__lt=parsed)

    page = list(_with_relations(qs).order_by("-created_at", "-id")[: limit + 1])
    has_more = len(page) > limit
    page = page[:limit]

    return Response(
        {
            "results": CoupleMessageSerializer(
                page, many=True, context=_viewer_context(request, relationship)
            ).data,
            "has_more": has_more,
            # Feed straight back as `before` to get the next page.
            "next_before": page[-1].created_at.isoformat() if page and has_more else None,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_message(request, relationship_id):
    relationship = _thread_or_404(request.user, relationship_id)
    serializer = SendMessageSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    reply_to = None
    if data.get("reply_to"):
        # A reply may only quote a message from this same thread; without this
        # check a crafted reply_to would leak one line of another couple's
        # conversation through the quote preview.
        reply_to = CoupleMessage.objects.filter(
            id=data["reply_to"], relationship=relationship
        ).first()
        if reply_to is None:
            return Response(
                {"error": "reply_to must be a message in this conversation."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    client_id = (data.get("client_id") or "").strip()
    if client_id:
        # A retry after a dropped response must not double-post.
        existing = CoupleMessage.objects.filter(
            relationship=relationship, client_id=client_id
        ).first()
        if existing is not None:
            return Response(
                CoupleMessageSerializer(
                    existing, context=_viewer_context(request, relationship)
                ).data,
                status=status.HTTP_200_OK,
            )

    kind = data.get("kind", CoupleMessage.KIND_TEXT)
    media = None
    if kind in CoupleMessage.MEDIA_KINDS:
        # Scoped to this relationship, so a stolen media id from another
        # couple's thread cannot be attached here — the same reasoning as the
        # reply_to check above, and the same 400 rather than a leaky 404.
        media = MessageMedia.objects.filter(
            id=data["media"], relationship=relationship, deleted_at__isnull=True
        ).first()
        if media is None:
            return Response(
                {"error": "That upload is not available."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if media.kind != kind:
            return Response(
                {"error": f"That upload is a {media.kind}, not a {kind}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if media.is_attached:
            # One upload, one message. Without this the same photo could be
            # re-sent by id forever, and deleting either copy would strand the
            # other pointing at destroyed bytes.
            return Response(
                {"error": "That upload has already been sent."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    message = CoupleMessage(
        relationship=relationship,
        sender=request.user,
        kind=kind,
        sticker=(data.get("sticker") or "").strip(),
        media=media,
        reply_to=reply_to,
        client_id=client_id,
    )
    message.body = (data.get("body") or "").strip()

    try:
        with transaction.atomic():
            message.save()
            if media is not None:
                media.attached_at = timezone.now()
                media.save(update_fields=["attached_at"])
    except IntegrityError:
        # Two retries raced; the winner is already stored.
        existing = CoupleMessage.objects.filter(
            relationship=relationship, client_id=client_id
        ).first()
        if existing is not None:
            return Response(
                CoupleMessageSerializer(
                    existing, context=_viewer_context(request, relationship)
                ).data,
                status=status.HTTP_200_OK,
            )
        raise

    # Two renderings on purpose. The socket payload carries no viewer context,
    # so `status` is null on the copy the partner receives — ticks belong to
    # whoever sent the message, and shipping the sender's tick state to the
    # recipient would only invite the client to render it on the wrong side.
    realtime.publish(
        relationship.id,
        {"type": "couple_message", "message": CoupleMessageSerializer(message).data},
        exclude_user_id=request.user.id,
    )
    # Learn from the send. Costs one indexed query and no model call, and is
    # guarded inside so it can never be why a message fails.
    assist.note_send_pattern(relationship, request.user, message)
    _maybe_refresh_summary(relationship)
    return Response(
        CoupleMessageSerializer(
            message, context=_viewer_context(request, relationship)
        ).data,
        status=status.HTTP_201_CREATED,
    )


def _maybe_refresh_summary(relationship) -> None:
    """Queue a summary refresh if the thread has drifted far enough.

    Enqueue only — the summarisation itself is a whole extra model round-trip
    and must never happen while someone is waiting on a send. A broker that is
    unreachable is not worth failing a message over.
    """
    try:
        from .tasks import refresh_thread_summary, summary_is_stale

        if summary_is_stale(relationship):
            refresh_thread_summary.delay(str(relationship.id))
    except Exception as exc:
        import logging

        logging.getLogger(__name__).info("summary_refresh_not_queued: %s", exc)


# ── Media ───────────────────────────────────────────────────────────────────
# Upload and send are two steps on purpose. The client uploads first, gets an
# id, then sends a message referencing it — which is what lets a photo appear
# in the thread with a progress ring rather than after the round trip. The cost
# is that a row can exist with no message attached; tasks.sweep_orphan_media
# collects those.


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_media(request, relationship_id):
    """Accept a photo or voice note, normalise it, encrypt it, store it."""
    relationship = _thread_or_404(request.user, relationship_id)

    serializer = UploadMediaSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    upload = request.FILES.get("file")
    if upload is None:
        return Response(
            {"error": "No file was uploaded."}, status=status.HTTP_400_BAD_REQUEST
        )

    # Check the declared size before reading the body into memory. Django has
    # already spooled it, but this is what keeps an 80 MB upload from becoming
    # an 80 MB Pillow decode.
    ceiling = (
        media_processing.MAX_IMAGE_BYTES
        if data["kind"] == MessageMedia.KIND_IMAGE
        else media_processing.MAX_VOICE_BYTES
    )
    if upload.size > ceiling:
        return Response(
            {"error": "That file is too large."}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        )

    blob = upload.read()
    scope = str(relationship.id)

    try:
        if data["kind"] == MessageMedia.KIND_IMAGE:
            full, thumb, width, height = media_processing.process_image(blob)
            mime, duration_ms, waveform = media_processing.IMAGE_MIME, None, []
        else:
            full, mime = media_processing.process_voice(blob, data.get("duration_ms", 0))
            thumb, width, height = b"", None, None
            duration_ms = data["duration_ms"]
            waveform = media_processing.normalise_waveform(data.get("waveform"))
    except media_processing.MediaRejected as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    storage_key = storage.key_for(relationship.id)
    thumb_key = storage.key_for(relationship.id, suffix="-thumb") if thumb else ""

    try:
        storage.put(storage_key, encrypt_bytes(full, scope))
        if thumb:
            storage.put(thumb_key, encrypt_bytes(thumb, scope))
    except storage.StorageError:
        log.exception("media_upload_failed relationship=%s", relationship.id)
        # Best effort tidy-up so a half-written pair does not linger unreferenced.
        for key in (storage_key, thumb_key):
            if key:
                try:
                    storage.delete(key)
                except storage.StorageError:
                    pass
        return Response(
            {"error": "Could not store that file. Try again."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    record = MessageMedia.objects.create(
        relationship=relationship,
        uploader=request.user,
        kind=data["kind"],
        storage_key=storage_key,
        thumb_key=thumb_key,
        mime=mime,
        byte_size=len(full),
        sha256=storage.checksum(full),
        duration_ms=duration_ms,
        waveform=waveform,
        width=width,
        height=height,
        transcript_status=(
            MessageMedia.TRANSCRIPT_PENDING
            if data["kind"] == MessageMedia.KIND_VOICE
            and transcription.should_transcribe(relationship)
            else MessageMedia.TRANSCRIPT_SKIPPED
        ),
    )

    # Both queued rather than run inline: the upload is on the request path and
    # a model call is not, and neither of these may be why a photo fails to
    # send. `_queue` swallows a broker that is down for the same reason.
    if record.transcript_status == MessageMedia.TRANSCRIPT_PENDING:
        _queue(transcription.transcribe_voice_note, record.id)
    if record.kind == MessageMedia.KIND_IMAGE:
        _queue(moderation.moderate_image, record.id)

    AuditLogger.get_instance().log(
        AuditEventType.MEDIA_UPLOADED,
        user_id=request.user.id,
        metadata={"media_id": str(record.id), "kind": record.kind},
    )
    return Response(MessageMediaSerializer(record).data, status=status.HTTP_201_CREATED)


def _queue(task, *args) -> None:
    """Fire a background task without letting the broker break the request."""
    try:
        task.delay(*args)
    except Exception:
        log.exception("chat_media_task_not_queued task=%s args=%s", task.name, args)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def media_meta(request, media_id):
    """The media row as JSON, without its bytes.

    Exists because transcription and moderation finish after the upload
    response has gone. The client polls this to reveal a transcript, and to run
    the pre-send caution check on a voice note before it is sent.
    """
    record = _media_or_404(request.user, media_id)
    return Response(MessageMediaSerializer(record).data)


def _media_or_404(user, media_id) -> MessageMedia:
    """A media row the caller is entitled to, or 404.

    Same 404-not-403 convention as the thread: someone probing ids should not
    learn that a photo exists, only that this one is not theirs to see.
    """
    record = get_object_or_404(MessageMedia, id=media_id, deleted_at__isnull=True)
    _thread_or_404(user, record.relationship_id)
    return record


def _serve_blob(record: MessageMedia, key: str, content_type: str) -> HttpResponse:
    """Fetch, decrypt and hand back one blob.

    ``no-store`` because this response is plaintext: no proxy, CDN or browser
    cache should hold a decrypted photo. The app keeps its own cache under file
    protection instead — see docs/chat-media.md §4.4.
    """
    try:
        blob = decrypt_bytes(storage.get(key), str(record.relationship_id))
    except storage.MissingBlob:
        # The row outlived its bytes. A missing photo is an unavailable bubble,
        # not a 500 — the same posture as a body that will not decrypt.
        log.warning("media_blob_missing media=%s key=%s", record.id, key)
        raise Http404 from None
    except (storage.StorageError, DecryptionError):
        log.exception("media_unreadable media=%s key=%s", record.id, key)
        raise Http404 from None

    response = HttpResponse(blob, content_type=content_type)
    response["Cache-Control"] = "private, no-store"
    response["Content-Length"] = str(len(blob))
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def media_blob(request, media_id):
    record = _media_or_404(request.user, media_id)
    return _serve_blob(record, record.storage_key, record.mime)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def media_thumb(request, media_id):
    record = _media_or_404(request.user, media_id)
    if not record.thumb_key:
        raise Http404
    return _serve_blob(record, record.thumb_key, media_processing.IMAGE_MIME)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_message(request, message_id):
    """Soft-delete. Only the author can delete, and only their own message."""
    message = get_object_or_404(CoupleMessage, id=message_id)
    _thread_or_404(request.user, message.relationship_id)

    if message.sender_id != request.user.id:
        return Response(
            {"error": "You can only delete your own messages."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if message.deleted_at is None:
        message.deleted_at = timezone.now()
        # Drop the ciphertext outright: a deleted message should not remain
        # readable in the database just because the row survives for replies.
        message.ciphertext = ""
        message.sticker = ""
        attached_media = message.media
        # The tombstone survives so replies still render, but the bytes do not.
        # A photo that is still sitting in a bucket has not been deleted in any
        # sense the person who deleted it would recognise.
        message.media = None
        message.save(update_fields=["deleted_at", "ciphertext", "sticker", "media"])
        if attached_media is not None:
            try:
                attached_media.destroy()
            except storage.StorageError:
                # Storage is down. The message is already a tombstone, so
                # failing the request now would tell the user their delete did
                # not work when the part they can see plainly did. The row is
                # left unreferenced, which is precisely what the orphan sweep
                # looks for, so the bytes still go — just later.
                log.exception(
                    "media_destroy_deferred message=%s media=%s",
                    message.id,
                    attached_media.id,
                )
        realtime.publish(
            message.relationship_id,
            {"type": "couple_message_deleted", "message_id": str(message.id)},
        )

    return Response(CoupleMessageSerializer(message).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def toggle_reaction(request, message_id):
    """Add the reaction, or remove it if it is already there (tap to toggle)."""
    message = get_object_or_404(CoupleMessage, id=message_id)
    _thread_or_404(request.user, message.relationship_id)

    if message.deleted_at is not None:
        return Response(
            {"error": "Cannot react to a deleted message."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = ReactionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    emoji = serializer.validated_data["emoji"]

    existing = MessageReaction.objects.filter(
        message=message, user=request.user, emoji=emoji
    ).first()
    if existing is not None:
        existing.delete()
        action = "removed"
    else:
        try:
            MessageReaction.objects.create(
                message=message, user=request.user, emoji=emoji
            )
        except IntegrityError:
            # Double-tap raced; the reaction is present either way.
            pass
        action = "added"

    message.refresh_from_db()
    payload = CoupleMessageSerializer(message).data
    realtime.publish(
        message.relationship_id,
        {
            "type": "couple_message_reaction",
            "message_id": str(message.id),
            "action": action,
            "emoji": emoji,
            "user_id": str(request.user.id),
            "reactions": payload["reactions"],
        },
        exclude_user_id=request.user.id,
    )
    return Response(payload)


def _advance_cursor(request, relationship, *, read: bool):
    """Move this user's cursor to now and tell the partner, so their ticks move.

    Delivery and read share one code path because they share one row and one
    invariant (delivery never trails read). The event is published to the
    partner only — a cursor is news to the person waiting on ticks, never to
    the person whose own app just moved it.
    """
    now = timezone.now()
    receipt, created = ReadReceipt.objects.get_or_create(
        relationship=relationship,
        user=request.user,
        defaults={
            "last_read_at": now if read else _EPOCH,
            "last_delivered_at": now,
        },
    )
    if not created:
        moved = receipt.advance(
            read_at=now if read else None, delivered_at=None if read else now
        )
        if moved:
            receipt.save(update_fields=["last_read_at", "last_delivered_at"])

    realtime.publish(
        relationship.id,
        {
            "type": "couple_receipt",
            "user_id": str(request.user.id),
            "last_read_at": receipt.last_read_at.isoformat()
            if receipt.last_read_at > _EPOCH
            else None,
            "last_delivered_at": receipt.last_delivered_at.isoformat()
            if receipt.last_delivered_at
            else None,
        },
        exclude_user_id=request.user.id,
    )
    return receipt



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_read(request, relationship_id):
    """Advance this user's read high-water mark. Never moves backwards."""
    relationship = _thread_or_404(request.user, relationship_id)
    receipt = _advance_cursor(request, relationship, read=True)
    return Response({"last_read_at": receipt.last_read_at.isoformat()})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_delivered(request, relationship_id):
    """This device now holds the thread up to now — but nobody has opened it.

    Called when the app has the messages in hand and *not* when they are on
    screen: on connecting the socket, on fetching history in the background, on
    a push arriving. That separation is the whole point of having two cursors.
    """
    relationship = _thread_or_404(request.user, relationship_id)
    receipt = _advance_cursor(request, relationship, read=False)
    return Response(
        {
            "last_delivered_at": receipt.last_delivered_at.isoformat()
            if receipt.last_delivered_at
            else None
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def unread_count(request, relationship_id):
    """How many of the partner's messages arrived after this user last read."""
    relationship = _thread_or_404(request.user, relationship_id)
    receipt = ReadReceipt.objects.filter(
        relationship=relationship, user=request.user
    ).first()

    qs = CoupleMessage.objects.filter(relationship=relationship, deleted_at__isnull=True).exclude(
        sender=request.user
    )
    if receipt is not None:
        qs = qs.filter(created_at__gt=receipt.last_read_at)

    return Response({"unread": qs.count()})


# ── Bliss in the thread ─────────────────────────────────────────────────────


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def assist_rephrase(request, relationship_id):
    """"Help me say this." Explicitly asked for, so it may take a moment."""
    relationship = _thread_or_404(request.user, relationship_id)
    draft = (request.data.get("draft") or "").strip()
    if not draft:
        return Response({"error": "draft required"}, status=status.HTTP_400_BAD_REQUEST)
    return Response(assist.rephrase(relationship, request.user, draft))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def assist_check(request, relationship_id):
    """Called as the user hits send.

    Always 200 with a verdict, even when the model is unavailable — the client
    treats "ok" as "send it", so a failure here must never strand a message.
    """
    relationship = _thread_or_404(request.user, relationship_id)
    draft = (request.data.get("draft") or "").strip()
    return Response(assist.check_before_send(relationship, request.user, draft))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def assist_nudge(request, relationship_id):
    """The one suggestion worth offering right now, if any.

    ``local_hour`` comes from the device rather than a stored timezone, so
    "end of the day" means their evening, not the server's.
    """
    relationship = _thread_or_404(request.user, relationship_id)
    raw_hour = request.query_params.get("local_hour")
    try:
        local_hour = int(raw_hour) if raw_hour is not None else None
        if local_hour is not None and not 0 <= local_hour <= 23:
            local_hour = None
    except (TypeError, ValueError):
        local_hour = None

    nudge = assist.nudge_for(relationship, request.user, local_hour=local_hour)
    if nudge is None:
        return Response({"nudge": None})
    return Response(
        {
            "nudge": {
                "id": str(nudge.id),
                "kind": nudge.kind,
                "suggestion": nudge.suggestion,
            }
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def assist_nudge_feedback(request, nudge_id):
    """Record whether a suggestion was used or waved away.

    An unacted nudge is the signal that it should probably not have fired.
    """
    nudge = get_object_or_404(AssistNudge, id=nudge_id, user=request.user)
    action = (request.data.get("action") or "").strip()
    now = timezone.now()
    if action == "acted":
        nudge.acted_at = now
    elif action == "dismissed":
        nudge.dismissed_at = now
    else:
        return Response(
            {"error": "action must be 'acted' or 'dismissed'"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    nudge.save(update_fields=["acted_at", "dismissed_at"])

    # The other half of the loop. Until now an unacted nudge was recorded and
    # never read; this is what makes it change anything.
    outcomes.record(
        nudge.relationship,
        f"nudge_{nudge.kind}",
        {"hour": timezone.localtime(nudge.created_at).hour},
        "accepted" if action == "acted" else "declined",
    )
    return Response({"ok": True})


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def assist_settings(request, relationship_id):
    """Read or change how much Bliss participates. Shared by both partners."""
    relationship = _thread_or_404(request.user, relationship_id)
    config = assist.settings_for(relationship)

    if request.method == "PATCH":
        for field in ("assist_enabled", "interception_enabled", "night_nudge_enabled"):
            if field in request.data:
                setattr(config, field, bool(request.data[field]))
        config.save()

    return Response(
        {
            "assist_enabled": config.assist_enabled,
            "interception_enabled": config.interception_enabled,
            "night_nudge_enabled": config.night_nudge_enabled,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def assist_read_coach(request, relationship_id):
    """Private guidance for the partner who just received a hard message.

    Only the receiver sees this. It is never shown to, or recorded against, the
    person who sent the message.
    """
    relationship = _thread_or_404(request.user, relationship_id)
    incoming = (request.data.get("message") or "").strip()
    return Response(assist.coach_response(relationship, request.user, incoming))
