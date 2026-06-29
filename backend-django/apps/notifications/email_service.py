import os
import logging

log = logging.getLogger(__name__)


class EmailService:
    """
    Sends transactional emails via Resend (free tier: 3,000/month).
    Called from Celery notifications queue — non-blocking.
    """
    FROM_ADDRESS = "RelationshipAI <hello@relationshipai.app>"

    def send(self, to: str, subject: str, html: str, text: str = '') -> bool:
        """
        Sends via Resend API.
        In test environments (no RESEND_API_KEY), logs the email instead.
        """
        api_key = os.environ.get('RESEND_API_KEY')
        if not api_key:
            log.warning("RESEND_API_KEY not set — email logged only", to=to, subject=subject)
            print(f"[EMAIL DRY-RUN] To: {to} | Subject: {subject}")
            return True  # Return True in dev/test

        try:
            import resend
            resend.api_key = api_key
            resend.Emails.send({
                "from": self.FROM_ADDRESS,
                "to": to,
                "subject": subject,
                "html": html,
                "text": text or subject,
            })
            return True
        except Exception as e:
            log.error("email_send_failed", to=to, subject=subject, error=str(e))
            return False


email_service = EmailService()
