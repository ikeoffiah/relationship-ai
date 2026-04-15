from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from apps.consent.models import UserConsent


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_consent(sender, instance, created, **kwargs):
    """
    Auto-create most restrictive consent record when a new user is registered.
    Per REL-20: Consent records default to most restrictive values on user creation.
    """
    if created:
        UserConsent.objects.get_or_create(
            user_id=instance.id,
            defaults={
                "updated_by": instance.id,
            },
        )
