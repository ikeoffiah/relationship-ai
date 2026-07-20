"""
Model registration for the notifications app.

The Notification model is defined in ``notification_models`` alongside the
app's other ``notification_*`` modules. Django only discovers models via
``<app>/models.py``, so re-exporting here is what actually registers the
model and lets its table be migrated.
"""

from apps.notifications.notification_models import Notification, NotificationType

__all__ = ["Notification", "NotificationType"]
