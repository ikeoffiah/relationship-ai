from django.db import models
from django.conf import settings

class UserProfile(models.Model):
    """Extended profile information for a user."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=255, blank=True)
    fcm_token = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    # Add any additional fields as needed

    class Meta:
        db_table = 'user_profiles'

    def __str__(self):
        return f"Profile for {self.user.email}"

class NotificationPreference(models.Model):
    """
    Per-event notification preferences.

    These mirror the events the mobile app actually surfaces (its settings UI
    is built around exactly these four toggles). The previous generic
    email/push/weekly fields were placeholders that nothing read.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_pref')
    session_reminders = models.BooleanField(default=True)
    partner_joined_session = models.BooleanField(default=True)
    relay_message_received = models.BooleanField(default=True)
    insight_detected = models.BooleanField(default=False)

    class Meta:
        db_table = 'notification_preferences'

    def __str__(self):
        return f"Notification prefs for {self.user.email}"
