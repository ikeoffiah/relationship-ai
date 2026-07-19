from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import AgeVerification

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "phone_number",
            "is_verified",
            "created_at",
            "data_encryption_key_id",
            "age_verification",
        )

    def get_age_verification(self, obj):
        verification = getattr(obj, "age_verification", None)
        if verification:
            return AgeVerificationSerializer(verification).data
        return None


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("email", "password", "full_name", "phone_number")

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class SocialAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)


class AgeVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgeVerification
        fields = ("status", "method", "verified_at", "blocked_reason")
