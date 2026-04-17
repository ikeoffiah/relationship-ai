from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.dispatch import receiver
from apps.audit.logger import AuditLogger
from apps.audit.constants import AuditEventType

audit = AuditLogger.get_instance()


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    audit.log(
        AuditEventType.LOGIN,
        user_id=user.id,
        metadata={"ip": request.META.get("REMOTE_ADDR")},
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user:
        audit.log(AuditEventType.LOGOUT, user_id=user.id)


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    audit.log(
        AuditEventType.FAILED_AUTH,
        metadata={
            "username": credentials.get("username"),
            "ip": request.META.get("REMOTE_ADDR") if request else None,
        },
    )
