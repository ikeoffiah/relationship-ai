from rest_framework import serializers
from django.conf import settings
from .models import UserProfile, NotificationPreference

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ["full_name", "phone_number", "date_of_birth"]
        read_only_fields = []

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ["email_notifications", "push_notifications", "weekly_summary"]

class ChangeEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if settings.AUTH_USER_MODEL.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already in use.")
        return value
