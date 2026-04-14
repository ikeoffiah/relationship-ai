from rest_framework.throttling import SimpleRateThrottle


class AuthAttemptThrottle(SimpleRateThrottle):
    """
    Max 5 per 15 minutes per IP + per email.
    """

    scope = "auth_attempt"

    def get_cache_key(self, request, view):
        email = request.data.get("email") or request.GET.get("email")
        if not email:
            return None  # Fallback to default behavior if email not present

        ident = self.get_ident(request)
        return f"throttle_{self.scope}_{ident}_{email}"
