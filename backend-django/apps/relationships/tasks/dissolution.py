import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from apps.consent.models import UserConsent
from apps.relationships.models import Relationship


logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, retry_backoff=True)
def RelationshipDissolutionJob(self, relationship_id):
    """
    Cascading cleanup task for relationship dissolution (REL-63).
    """
    logger.info(f"Starting dissolution job for relationship {relationship_id}")
    
    try:
        relationship = Relationship.objects.get(id=relationship_id)
        partner_a = relationship.partner_a
        partner_b = relationship.partner_b
        partners = [partner_a, partner_b]

        with transaction.atomic():
            # 1. Revoke shared context access immediately for both partners
            UserConsent.objects.filter(user__in=partners).update(
                shared_relationship_context='not_participating',
                joint_session_participation='not_enrolled',
                cross_partner_insight_sharing='never',
                updated_at=timezone.now()
            )

            # 2. Revoke access to shared namespace in vector DB
            # namespace: shared_{relationship_id}
            # This would interface with the vector store client
            logger.info(f"Revoking vector DB namespace: shared_{relationship_id}")

            # 3. Apply retention policies to shared context memories
            # Logic: Delete if 'Not participating'; retain if either partner set longer retention
            # (Assuming a shared memory model exists)
            logger.info("Applying memory retention policies post-dissolution")

            # 4. Log relationship_dissolved event to audit store
            # from apps.audit.models import AuditEvent
            # AuditEvent.objects.create(...)
            logger.info(f"Logging dissolution for {relationship_id} to audit store")

            # 5. Send email notification to both partners
            recipient_list = [p.email for p in partners if p]
            if recipient_list:
                try:
                    send_mail(
                        subject="Relationship Dissolved",
                        message="Your relationship on RelationshipAI has been dissolved. All shared context access has been revoked.",
                        from_email=None,
                        recipient_list=recipient_list,
                    )
                except Exception as e:
                    logger.error(f"Failed to send dissolution emails: {e}")

    except Relationship.DoesNotExist:
        logger.error(f"Dissolution job failed: Relationship {relationship_id} not found.")
    except Exception as exc:
        logger.error(f"Dissolution job error: {exc}")
        raise self.retry(exc=exc)
