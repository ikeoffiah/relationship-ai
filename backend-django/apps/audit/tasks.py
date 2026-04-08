from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)


@shared_task(name="audit.tasks.verify_audit_chain")
def verify_audit_chain():
    """
    Task to verify the integrity of the audit event hash chain.
    """
    logger.info("Starting audit chain verification")
    try:
        call_command("verify_audit_chain")
    except Exception as e:
        logger.error(f"Audit chain verification failed: {e}")
        raise
