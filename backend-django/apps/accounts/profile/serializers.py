from rest_framework import serializers
from django.conf import settings
from .models import UserProfile, NotificationPreference

class UserProfileSerializer(serializers.ModelSerializer):
    # email lives on the User, not the profile, but the client reads it from
    # this response; expose it read-only.
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = UserProfile
        fields = ["full_name", "email", "phone_number", "date_of_birth"]

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "session_reminders",
            "partner_joined_session",
            "relay_message_received",
            "insight_detected",
        ]

class ChangeEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if settings.AUTH_USER_MODEL.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already in use.")
        return value
