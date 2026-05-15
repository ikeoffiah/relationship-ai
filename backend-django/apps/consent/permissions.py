from rest_framework.permissions import BasePermission

class IsConsentOwner(BasePermission):
    """Ensures user can only read/write their own consent. No staff override."""
    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id
