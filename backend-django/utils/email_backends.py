"""Email over Resend's HTTP API rather than SMTP.

Render's free instances block outbound traffic to SMTP ports 25, 465 and 587
(policy change, September 2025, to curb spam from free accounts). Port 25 stays
blocked on paid instances too. So `django.core.mail.backends.smtp` cannot
deliver from that host at all — it does not fail fast either, it hangs until
EMAIL_TIMEOUT and surfaces as `TimeoutError: timed out` inside a Celery retry,
which looks like a slow mail server rather than a blocked port.

This backend posts to https://api.resend.com/emails over 443, which no host
blocks. Nothing else changes: every existing `send_mail()` call keeps working.

Set EMAIL_BACKEND to this class and provide RESEND_API_KEY. EMAIL_HOST_PASSWORD
is accepted as a fallback because that is where the key already lives on hosts
configured for the SMTP transport.
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

_ENDPOINT = "https://api.resend.com/emails"


class ResendHTTPBackend(BaseEmailBackend):
    """Deliver via Resend's REST API. Same contract as any Django backend."""

    def __init__(self, fail_silently: bool = False, **kwargs) -> None:
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = (
            getattr(settings, "RESEND_API_KEY", "")
            or getattr(settings, "EMAIL_HOST_PASSWORD", "")
        )
        # Deliberately not raising here. A missing key must not stop the
        # process from starting — it should fail on send, where the caller can
        # see which message was lost.
        self.timeout = getattr(settings, "EMAIL_TIMEOUT", 10) or 10

    def send_messages(self, email_messages) -> int:
        if not email_messages:
            return 0
        if not self.api_key:
            logger.error("resend_backend: no API key configured; %d message(s) dropped",
                         len(email_messages))
            if not self.fail_silently:
                raise ValueError("RESEND_API_KEY (or EMAIL_HOST_PASSWORD) is not set")
            return 0

        sent = 0
        for message in email_messages:
            if self._send(message):
                sent += 1
        return sent

    def _send(self, message) -> bool:
        recipients = list(message.to or [])
        if not recipients:
            return False

        payload = {
            "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
            "to": recipients,
            "subject": message.subject,
            "text": message.body,
        }
        if message.cc:
            payload["cc"] = list(message.cc)
        if message.bcc:
            payload["bcc"] = list(message.bcc)
        if message.reply_to:
            payload["reply_to"] = list(message.reply_to)

        # EmailMultiAlternatives carries the HTML part here.
        for content, mimetype in getattr(message, "alternatives", []) or []:
            if mimetype == "text/html":
                payload["html"] = content
                break

        try:
            response = requests.post(
                _ENDPOINT,
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            # No recipient addresses in the log line — this is a counselling
            # product and who was emailed is itself information.
            logger.error("resend_backend: request failed: %s", exc)
            if not self.fail_silently:
                raise
            return False

        if response.status_code >= 400:
            logger.error(
                "resend_backend: %s rejected the message: %s",
                response.status_code,
                response.text[:300],
            )
            if not self.fail_silently:
                raise RuntimeError(
                    f"Resend returned {response.status_code}: {response.text[:300]}"
                )
            return False

        return True
