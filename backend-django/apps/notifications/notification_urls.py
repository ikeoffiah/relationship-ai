"""URL configuration for the in-app notification API."""

from django.urls import path

from apps.notifications import notification_views as views

urlpatterns = [
    # ── User-scoped ─────────────────────────────────────────────────────
    path(
        "api/v1/users/<uuid:user_id>/notifications",
        views.list_notifications,
        name="notification-list",
    ),
    path(
        "api/v1/users/<uuid:user_id>/notifications/unread-count",
        views.unread_count,
        name="notification-unread-count",
    ),
    path(
        "api/v1/users/<uuid:user_id>/notifications/read-all",
        views.mark_all_read,
        name="notification-read-all",
    ),
    # ── Notification-scoped ─────────────────────────────────────────────
    path(
        "api/v1/notifications/<uuid:notification_id>/read",
        views.mark_read,
        name="notification-mark-read",
    ),
    path(
        "api/v1/notifications/<uuid:notification_id>",
        views.delete_notification,
        name="notification-delete",
    ),
]
