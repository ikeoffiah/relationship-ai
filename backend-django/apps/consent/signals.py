from apps.consent.models import UserConsent


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
