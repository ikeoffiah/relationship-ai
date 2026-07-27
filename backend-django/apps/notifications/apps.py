from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"

    def ready(self):
        # Connect the post_save signal that mirrors in-app notifications to push.
        from apps.notifications import signals  # noqa: F401
