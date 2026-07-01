from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Therapist, TherapistConnection, TherapistStrategyNote
from .serializers import TherapistLoginSerializer, TherapistConnectionSerializer, TherapistStrategyNoteSerializer
from apps.accounts.auth import generate_jwt

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
        therapist = serializer.validated_data["therapist"]
        token, _ = generate_jwt(user, ["therapist:read", "therapist:write"])
        return Response({"access_token": token, "token_type": "Bearer"})

class TherapistConnectionViewSet(viewsets.ModelViewSet):
    queryset = TherapistConnection.objects.all()
    serializer_class = TherapistConnectionSerializer
    permission_classes = [permissions.IsAuthenticated, TherapistPermission]

    def get_queryset(self):
        return TherapistConnection.objects.filter(therapist=self.request.user.therapist_profile)

    def perform_create(self, serializer):
        client_id = self.request.data.get("client")
        serializer.save(therapist=self.request.user.therapist_profile, client_id=client_id)

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
        client_id = self.request.data.get("client")
        serializer.save(therapist=self.request.user.therapist_profile, client_id=client_id)
