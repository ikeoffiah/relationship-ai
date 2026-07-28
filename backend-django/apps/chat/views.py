"""HTTP surface for the couple thread.

Every endpoint resolves the relationship through :func:`_thread_or_404`, which
is the single access check: a user may only touch a thread they are a partner
in. It returns 404 rather than 403 on purpose — a stranger probing ids should
not be able to learn which relationships exist.
"""

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.relationships.models import Relationship

from . import assist, realtime
from .models import AssistNudge, CoupleMessage, MessageReaction, ReadReceipt
from .serializers import (
    CoupleMessageSerializer,
    ReactionSerializer,
    SendMessageSerializer,
)

# History page size. Generous enough that opening the thread rarely needs a
# second round trip, small enough to stay comfortably inside a mobile payload.
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


def _thread_or_404(user, relationship_id) -> Relationship:
    """Return the relationship only if `user` is one of its partners."""
    relationship = get_object_or_404(Relationship, id=relationship_id)
    if user.id not in (relationship.partner_a_id, relationship.partner_b_id):
        # Deliberately 404, not 403 — see module docstring.
        from django.http import Http404

        raise Http404
    return relationship


def _with_relations(queryset):
    return queryset.select_related("sender", "reply_to", "reply_to__sender").prefetch_related(
        "reactions"
    )


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
            "results": CoupleMessageSerializer(page, many=True).data,
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
                CoupleMessageSerializer(existing).data, status=status.HTTP_200_OK
            )

    message = CoupleMessage(
        relationship=relationship,
        sender=request.user,
        kind=data.get("kind", CoupleMessage.KIND_TEXT),
        sticker=(data.get("sticker") or "").strip(),
        reply_to=reply_to,
        client_id=client_id,
    )
    message.body = (data.get("body") or "").strip()

    try:
        with transaction.atomic():
            message.save()
    except IntegrityError:
        # Two retries raced; the winner is already stored.
        existing = CoupleMessage.objects.filter(
            relationship=relationship, client_id=client_id
        ).first()
        if existing is not None:
            return Response(
                CoupleMessageSerializer(existing).data, status=status.HTTP_200_OK
            )
        raise

    payload = CoupleMessageSerializer(message).data
    realtime.publish(
        relationship.id,
        {"type": "couple_message", "message": payload},
        exclude_user_id=request.user.id,
    )
    _maybe_refresh_summary(relationship)
    return Response(payload, status=status.HTTP_201_CREATED)


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
        message.save(update_fields=["deleted_at", "ciphertext", "sticker"])
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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_read(request, relationship_id):
    """Advance this user's read high-water mark. Never moves backwards."""
    relationship = _thread_or_404(request.user, relationship_id)
    now = timezone.now()

    receipt, created = ReadReceipt.objects.get_or_create(
        relationship=relationship, user=request.user, defaults={"last_read_at": now}
    )
    if not created and receipt.last_read_at < now:
        receipt.last_read_at = now
        receipt.save(update_fields=["last_read_at"])

    realtime.publish(
        relationship.id,
        {
            "type": "couple_read",
            "user_id": str(request.user.id),
            "last_read_at": receipt.last_read_at.isoformat(),
        },
        exclude_user_id=request.user.id,
    )
    return Response({"last_read_at": receipt.last_read_at.isoformat()})


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
