"""DRF serializers for the in-app notification model."""

from rest_framework import serializers

from apps.notifications.notification_models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Read-only serializer for notification list / detail responses."""

    class Meta:
        model = Notification
        fields = [
            "id",
            "user_id",
            "type",
            "title",
            "body",
            "data",
            "read",
            "created_at",
        ]
        read_only_fields = fields


class UnreadCountSerializer(serializers.Serializer):
    """Simple wrapper for the unread-count endpoint."""

    count = serializers.IntegerField()
