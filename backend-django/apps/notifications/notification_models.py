"""
In-app notification Django model.

Notifications are stored in the database and surfaced through the
notification center UI.  Push and email delivery happen separately —
this model is only for the in-app notification feed.
"""

import uuid
from django.db import models


class NotificationType(models.TextChoices):
    SESSION_REMINDER = "session_reminder", "Session Reminder"
    PARTNER_JOINED = "partner_joined", "Partner Joined Session"
    RELAY_RECEIVED = "relay_received", "Relay Message Received"
    INSIGHT_DETECTED = "insight_detected", "Insight Detected"
    SAFETY_FOLLOWUP = "safety_followup", "Safety Follow-up"
    THERAPIST_CONNECTED = "therapist_connected", "Therapist Connected"
    SYSTEM = "system", "System"


class Notification(models.Model):
    """
    A single in-app notification delivered to a user.

    Notifications are displayed in the notification center and carry
    an optional ``data`` payload that the Flutter client can use to
    deep-link into the relevant screen.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
    )
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    data = models.JSONField(blank=True, default=dict)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user_id", "-created_at"],
                name="idx_notif_user_created",
            ),
            models.Index(
                fields=["user_id", "read"],
                name="idx_notif_user_read",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.type}] {self.title} → {self.user_id}"
