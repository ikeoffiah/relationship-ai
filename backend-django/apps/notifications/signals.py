"""
Mirror every in-app notification to a push notification.

When a ``Notification`` row is created (by any feature — daily question, @bliss,
commitments, focus, games…), this sends the same title/body to the recipient's
device via ``PushNotificationService``. It is best-effort and never blocks or
breaks notification creation:

* No device token on the recipient's profile → nothing to push, skip.
* ``FIREBASE_SERVICE_ACCOUNT_JSON`` unset → the push service dry-runs (logs
  only), so this is inert until real Firebase credentials are configured.
* Any error is swallowed — a push failure must not roll back the notification.

Delivery runs on a background thread so it never adds latency to the request
that created the notification, except under ``PUSH_SYNCHRONOUS`` (set in tests)
where it runs inline for deterministic assertions — mirroring the audit logger.
"""

import logging
import os
import threading

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.notifications.notification_models import Notification
from apps.notifications.push_service import PushNotification, push_service

logger = logging.getLogger(__name__)


def _device_token(user_id) -> str | None:
    """The recipient's FCM device token, if they have a profile with one."""
    from apps.accounts.profile.models import UserProfile

    return (
        UserProfile.objects.filter(user_id=user_id)
        .values_list("fcm_token", flat=True)
        .first()
    )


def _deliver(notification: Notification) -> bool:
    """Send one push for a notification. Returns True if a send was attempted."""
    try:
        token = _device_token(notification.user_id)
        if not token:
            return False
        push_service.send_to_user(
            token,
            PushNotification(
                title=notification.title,
                body=notification.body or "",
                data={"type": notification.type, **(notification.data or {})},
            ),
        )
        return True
    except Exception as exc:  # never let a push failure escape
        logger.warning("push mirror failed for notification %s: %s", notification.id, exc)
        return False


@receiver(post_save, sender=Notification)
def push_on_notification_created(sender, instance, created, **kwargs):
    if not created:
        return
    if getattr(settings, "PUSH_SYNCHRONOUS", False):
        # Deterministic inline delivery for tests.
        _deliver(instance)
    elif os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON"):
        # Real credentials present: deliver off the request thread.
        threading.Thread(target=_deliver, args=(instance,), daemon=True).start()
    # Otherwise push is unconfigured — stay completely inert (no thread, no DB
    # query), so it costs nothing until Firebase credentials are set.
