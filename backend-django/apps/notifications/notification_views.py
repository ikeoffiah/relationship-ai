"""
API views for the in-app notification center.

Endpoints
---------
GET    /api/v1/users/{user_id}/notifications            — paginated list
GET    /api/v1/users/{user_id}/notifications/unread-count — unread badge count
PUT    /api/v1/notifications/{id}/read                   — mark one as read
PUT    /api/v1/users/{user_id}/notifications/read-all    — mark all as read
DELETE /api/v1/notifications/{id}                        — delete one
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications.notification_models import Notification
from apps.notifications.notification_serializers import (
    NotificationSerializer,
    UnreadCountSerializer,
)


# ── Ownership helpers ───────────────────────────────────────────────────
# Every route is addressed by a user_id or notification_id in the URL, so
# authentication alone is not enough: without these checks any logged-in user
# could read, mutate or delete another user's notifications.


def _is_self(request, user_id) -> bool:
    """True when the authenticated caller owns the addressed user_id."""
    return str(request.user.id) == str(user_id)


def _forbidden():
    return Response(
        {"message": "You may only access your own notifications"},
        status=status.HTTP_403_FORBIDDEN,
    )


# ── Paginated list ──────────────────────────────────────────────────────


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_notifications(request, user_id):
    """Return a paginated list of in-app notifications, newest first."""
    if not _is_self(request, user_id):
        return _forbidden()
    page = int(request.query_params.get("page", 1))
    limit = min(int(request.query_params.get("limit", 20)), 50)
    offset = (page - 1) * limit

    qs = Notification.objects.filter(user_id=user_id)
    total = qs.count()
    notifications = qs[offset : offset + limit]

    serializer = NotificationSerializer(notifications, many=True)
    return Response(
        {
            "notifications": serializer.data,
            "total": total,
            "page": page,
            "limit": limit,
            "has_more": offset + limit < total,
        }
    )


# ── Unread count ────────────────────────────────────────────────────────


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def unread_count(request, user_id):
    """Return the number of unread notifications for badge display."""
    if not _is_self(request, user_id):
        return _forbidden()
    count = Notification.objects.filter(user_id=user_id, read=False).count()
    serializer = UnreadCountSerializer({"count": count})
    return Response(serializer.data)


# ── Mark single as read ─────────────────────────────────────────────────


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def mark_read(request, notification_id):
    """Mark a single notification as read."""
    try:
        notification = Notification.objects.get(
            id=notification_id, user_id=request.user.id
        )
    except Notification.DoesNotExist:
        return Response(
            {"message": "Notification not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    notification.read = True
    notification.save(update_fields=["read"])
    return Response(NotificationSerializer(notification).data)


# ── Mark all as read ────────────────────────────────────────────────────


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def mark_all_read(request, user_id):
    """Mark every unread notification for the user as read."""
    if not _is_self(request, user_id):
        return _forbidden()
    updated = Notification.objects.filter(user_id=user_id, read=False).update(
        read=True
    )
    return Response({"marked_read": updated})


# ── Delete single ───────────────────────────────────────────────────────


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_notification(request, notification_id):
    """Delete a single notification (swipe-to-dismiss)."""
    try:
        notification = Notification.objects.get(
            id=notification_id, user_id=request.user.id
        )
    except Notification.DoesNotExist:
        return Response(
            {"message": "Notification not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    notification.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
