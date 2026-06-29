import json
import logging
import os
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass
class PushNotification:
    title: str
    body: str
    data: dict | None = None


class PushNotificationService:
    """
    Sends push notifications via Firebase Cloud Messaging (FCM) HTTP v1 API.
    FCM is completely free with no meaningful limits for MVP scale.
    Credentials: Firebase project service account JSON stored in FIREBASE_SERVICE_ACCOUNT_JSON
    env var (base64-encoded in production).
    """

    def send_to_user(self, device_token: str, notification: PushNotification) -> bool:
        """Send a push notification to a specific device token."""
        account_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')
        if not account_json:
            log.warning("FIREBASE_SERVICE_ACCOUNT_JSON not set — push logged only",
                        title=notification.title)
            print(f"[PUSH DRY-RUN] {notification.title}: {notification.body}")
            return True  # Dry run in dev/test

        try:
            import firebase_admin
            from firebase_admin import credentials, messaging

            if not firebase_admin._apps:
                cred = credentials.Certificate(json.loads(account_json))
                firebase_admin.initialize_app(cred)

            message = messaging.Message(
                notification=messaging.Notification(
                    title=notification.title,
                    body=notification.body,
                ),
                data=notification.data or {},
                token=device_token,
            )
            messaging.send(message)
            return True
        except Exception as e:
            log.error("push_send_failed", title=notification.title, error=str(e))
            return False


push_service = PushNotificationService()
