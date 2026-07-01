from rest_framework import permissions

class IsAdult(permissions.BasePermission):
    """
    Allows access only to non-minor users.
    Per REL-57: Minor users are completely blocked from joint sessions.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and not request.user.is_minor)
