from django.apps import AppConfig


class ConsentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.consent"

    def ready(self):
        from django.db.models.signals import post_save
        from django.contrib.auth import get_user_model
        from apps.consent.signals import create_user_consent

        User = get_user_model()
        post_save.connect(create_user_consent, sender=User)
