from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import TherapistConnection, TherapistStrategyNote
from .serializers import TherapistLoginSerializer, TherapistConnectionSerializer, TherapistStrategyNoteSerializer
from apps.accounts.auth import generate_jwt

User = get_user_model()

class TherapistPermission(permissions.BasePermission):
    """Allow access only to authenticated therapist users."""
    def has_permission(self, request, view):
        return bool(request.user and hasattr(request.user, "therapist_profile"))

class TherapistLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = TherapistLoginSerializer

    def post(self, request):
        serializer = TherapistLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = generate_jwt(user, ["therapist:read", "therapist:write"])
        return Response({"access_token": token, "token_type": "Bearer"})

def _resolve_client(client_id):
    """Resolve a client id to a real user, 400 rather than a database error."""
    if not client_id:
        raise ValidationError({"client": "This field is required."})
    try:
        return User.objects.get(pk=client_id)
    except (User.DoesNotExist, ValueError, DjangoValidationError):
        raise ValidationError({"client": "No such user."})


class TherapistConnectionViewSet(viewsets.ModelViewSet):
    queryset = TherapistConnection.objects.all()
    serializer_class = TherapistConnectionSerializer
    permission_classes = [permissions.IsAuthenticated, TherapistPermission]

    def get_queryset(self):
        return TherapistConnection.objects.filter(therapist=self.request.user.therapist_profile)

    def perform_create(self, serializer):
        # A therapist may propose a connection, but only the client can grant
        # consent_client (read-only on the serializer), so a connection created
        # here is never active on its own.
        client = _resolve_client(self.request.data.get("client"))
        serializer.save(therapist=self.request.user.therapist_profile, client=client)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        consent = request.data.get("consent_therapist")
        if consent is not None:
            instance.consent_therapist = consent
            instance.save(update_fields=["consent_therapist"])
            return Response(self.get_serializer(instance).data)
        return super().partial_update(request, *args, **kwargs)

class TherapistStrategyNoteViewSet(viewsets.ModelViewSet):
    queryset = TherapistStrategyNote.objects.all()
    serializer_class = TherapistStrategyNoteSerializer
    permission_classes = [permissions.IsAuthenticated, TherapistPermission]

    def get_queryset(self):
        return TherapistStrategyNote.objects.filter(therapist=self.request.user.therapist_profile)

    def perform_create(self, serializer):
        therapist = self.request.user.therapist_profile
        client = _resolve_client(self.request.data.get("client"))
        connection = TherapistConnection.objects.filter(
            therapist=therapist, client=client
        ).first()
        # Notes are clinical records about a person; writing them requires a
        # connection both parties have consented to, not merely a user id.
        if connection is None or not connection.is_active:
            raise PermissionDenied(
                "A mutually consented connection with this client is required."
            )
        serializer.save(therapist=therapist, client=client)
