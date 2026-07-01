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
    """User's notification preferences (email, push, weekly summary)."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_pref')
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    weekly_summary = models.BooleanField(default=False)

    class Meta:
        db_table = 'notification_preferences'

    def __str__(self):
        return f"Notification prefs for {self.user.email}"
