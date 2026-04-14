from django.http import JsonResponse
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from .auth import decode_jwt

User = get_user_model()


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware to validate JWT on every authenticated request.
    Extracts Bearer token, validates it, and injects request.user and request.token_claims.
    """

    def process_request(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return

        token = auth_header.split(" ")[1]
        try:
            claims = decode_jwt(token)

            # Check revocation store (Redis)
            jti = claims.get("jti")
            if cache.get(f"revoked_jti:{jti}"):
                return JsonResponse({"error": "Token revoked"}, status=401)

            # Inject claims and user
            user_id = claims.get("sub")
            try:
                user = User.objects.get(id=user_id)
                request.user = user
                request.token_claims = claims
            except User.DoesNotExist:
                return JsonResponse({"error": "User not found"}, status=401)

        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=401)
        except Exception:
            return JsonResponse({"error": "Invalid token structure"}, status=401)
