from rest_framework import generics, permissions, exceptions
from .models import UserConsent
from .serializers import UserConsentSerializer

class IsOwner(permissions.BasePermission):
    """
    Custom permission to only allow users to access their own consent record.
    Matches request.user.id with the user_id field or URL parameter.
    """
    def has_permission(self, request, view):
        user_id_in_url = view.kwargs.get('user_id')
        if not request.user or not request.user.is_authenticated:
            # Let IsAuthenticated handle 401
            return True
            
        return str(request.user.id) == str(user_id_in_url)

    def has_object_permission(self, request, view, obj):
        return str(obj.user_id) == str(request.user.id)

class UserConsentView(generics.RetrieveUpdateAPIView):
    """
    GET /api/v1/users/{user_id}/consent -> Retrieve consent
    PUT /api/v1/users/{user_id}/consent -> Update consent
    """
    serializer_class = UserConsentSerializer
    permission_classes = [IsOwner, permissions.IsAuthenticated]
    lookup_field = "user_id"

    def get_queryset(self):
        # Users can only ever see their own consent
        return UserConsent.objects.filter(user_id=self.request.user.id)

    def perform_update(self, serializer):
        # Per REL-20 and model enforcement: updated_by must be set to user_id
        # We also support optional X-Session-Context for audit logging.
        # Use META.get for maximum compatibility.
        session_context = self.request.META.get('HTTP_X_SESSION_CONTEXT')
        if not session_context:
            session_context = self.request.headers.get('x-session-context')
        
        # Pass extra kwargs to serializer.save() which will be handled by our custom update()
        serializer.save(
            updated_by=self.request.user.id,
            session_context=session_context
        )

    def handle_exception(self, exc):
        # Map specific model validation errors to DRF exceptions
        from django.core.exceptions import ValidationError as DjangoValidationError
        if isinstance(exc, DjangoValidationError):
            # Django's ValidationError can have a message_dict or a list of messages
            detail = getattr(exc, 'message_dict', getattr(exc, 'messages', str(exc)))
            return super().handle_exception(exceptions.ValidationError(detail=detail))
        return super().handle_exception(exc)
