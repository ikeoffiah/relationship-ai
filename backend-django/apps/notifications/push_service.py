import base64
import json
import logging
import os
from dataclasses import dataclass

log = logging.getLogger(__name__)


def _parse_service_account(value: str) -> dict:
    """Parse the service-account credential from the env var, accepting either
    raw JSON or a base64-encoded JSON blob (easier to store as a single-line
    secret on most hosts)."""
    try:
        return json.loads(value)
    except (json.JSONDecodeError, ValueError):
        return json.loads(base64.b64decode(value).decode())


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
            log.warning("FIREBASE_SERVICE_ACCOUNT_JSON not set — push logged only: %s",
                        notification.title)
            print(f"[PUSH DRY-RUN] {notification.title}: {notification.body}")
            return True  # Dry run in dev/test

        try:
            import firebase_admin
            from firebase_admin import credentials, messaging

            if not firebase_admin._apps:
                cred = credentials.Certificate(_parse_service_account(account_json))
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
            log.error("push_send_failed for %s: %s", notification.title, str(e))
            return False


push_service = PushNotificationService()
