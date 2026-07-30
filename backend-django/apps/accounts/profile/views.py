from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .models import UserProfile, NotificationPreference
from .serializers import UserProfileSerializer, NotificationPreferenceSerializer, ChangeEmailSerializer

User = get_user_model()

class ProfileView(generics.RetrieveUpdateAPIView):
    """Retrieve or update the authenticated user's profile."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.all()

    def get_object(self):
        # Ensure a profile exists for the user
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

class ChangeEmailView(generics.GenericAPIView):
    """Change the email address of the authenticated user."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangeEmailSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.email = serializer.validated_data["email"]
        request.user.save()
        return Response({"detail": "Email updated successfully."}, status=status.HTTP_200_OK)

class NotificationPreferencesView(generics.RetrieveUpdateAPIView):
    """Get or update notification preferences for the authenticated user."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationPreferenceSerializer
    queryset = NotificationPreference.objects.all()

    def get_object(self):
        pref, _ = NotificationPreference.objects.get_or_create(user=self.request.user)
        return pref

class FCMTokenView(generics.GenericAPIView):
    """Store or update the user's FCM token for push notifications."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        token = request.data.get("token")
        if not token:
            return Response({"detail": "Token is required."}, status=status.HTTP_400_BAD_REQUEST)
        # Assuming a simple field on User model or a related model; here we store on profile
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.fcm_token = token  # Add fcm_token field if not present; for now store dynamically
        profile.save(update_fields=["fcm_token"])
        return Response({"detail": "FCM token saved."}, status=status.HTTP_200_OK)

class AccountDeletionView(generics.DestroyAPIView):
    """Deactivate the authenticated user, and destroy their media outright.

    Deactivation is a defensible soft delete for rows in our own database —
    unreachable, and finishable later. It is not defensible for photographs and
    voice notes held by a storage vendor, where "unreachable" means nothing and
    the bytes stay on someone else's disk. So the media is destroyed here,
    synchronously, at the moment the person asks.
    """
    permission_classes = [permissions.IsAuthenticated]
    queryset = User.objects.all()

    def get_object(self):
        return self.request.user

    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        # Account deletion is destructive, so re-authenticate: the client
        # collects the password for exactly this. A social-only account with no
        # usable password cannot be deleted this way and must use a dedicated
        # flow rather than being deletable with any/empty password.
        password = request.data.get("password", "")
        if not user.has_usable_password() or not user.check_password(password):
            return Response(
                {"detail": "Password confirmation is incorrect."},
                status=status.HTTP_403_FORBIDDEN,
            )

        from apps.chat.erasure import erase_media_for_user

        # Before deactivating, not after: a failure here must not leave an
        # account that is already unusable with its photographs still live.
        _destroyed, failed = erase_media_for_user(user)

        user.is_active = False
        user.save(update_fields=["is_active"])

        if failed:
            # Honest rather than tidy. The account is gone and the sweep will
            # finish the rest, but claiming a clean erasure we did not achieve
            # is the one answer that would be wrong.
            return Response(
                {"detail": "Account deactivated. Some media could not be removed yet."},
                status=status.HTTP_200_OK,
            )
        return Response({"detail": "Account deactivated."}, status=status.HTTP_204_NO_CONTENT)
