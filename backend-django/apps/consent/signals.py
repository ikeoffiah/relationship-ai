from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from apps.consent.models import UserConsent

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_consent(sender, instance, created, **kwargs):
    """
    Auto-create most restrictive consent record when a new user is registered.
    Per REL-40: Consent records default to most restrictive values on user creation.
    """
    if created:
        UserConsent.objects.get_or_create(user=instance)
