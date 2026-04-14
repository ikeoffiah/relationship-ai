import secrets
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache
from django.core.exceptions import ValidationError
from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from .models import AuthCode, RefreshToken
from django.conf import settings
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    LoginSerializer,
    SocialAuthSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
)
from .throttles import AuthAttemptThrottle
from .auth import (
    validate_pkce,
    generate_jwt,
    create_refresh_token_record,
    rotate_refresh_token,
    revoke_family,
)

User = get_user_model()


class RegisterView(views.APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthAttemptThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Auto-login: issue tokens for frictionless onboarding
            access_token, _ = generate_jwt(user, ["session:read", "session:write"])
            refresh_token_record, refresh_token_plaintext = create_refresh_token_record(
                user
            )

            return Response(
                {
                    "user": UserSerializer(user).data,
                    "access_token": access_token,
                    "refresh_token": f"{refresh_token_record.jti}:{refresh_token_plaintext}",
                    "token_type": "Bearer",
                    "expires_in": 900,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(views.APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthAttemptThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            password = serializer.validated_data["password"]
            user = authenticate(email=email, password=password)

            if user:
                access_token, _ = generate_jwt(user, ["session:read", "session:write"])
                refresh_token_record, refresh_token_plaintext = (
                    create_refresh_token_record(user)
                )

                return Response(
                    {
                        "user": UserSerializer(user).data,
                        "access_token": access_token,
                        "refresh_token": f"{refresh_token_record.jti}:{refresh_token_plaintext}",
                        "token_type": "Bearer",
                        "expires_in": 900,
                    }
                )
            return Response(
                {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GoogleLoginView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SocialAuthSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data["id_token"]
            try:
                # Verify the ID token using google-auth-library
                idinfo = id_token.verify_oauth2_token(
                    token, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
                )

                # ID token is valid. get user info
                email = idinfo["email"]
                full_name = idinfo.get("name", "")

                user, created = User.objects.get_or_create(
                    email=email, defaults={"full_name": full_name}
                )

                # Issue tokens
                access_token, _ = generate_jwt(user, ["session:read", "session:write"])
                refresh_token_record, refresh_token_plaintext = (
                    create_refresh_token_record(user)
                )

                return Response(
                    {
                        "user": UserSerializer(user).data,
                        "access_token": access_token,
                        "refresh_token": f"{refresh_token_record.jti}:{refresh_token_plaintext}",
                        "token_type": "Bearer",
                        "expires_in": 900,
                    }
                )

            except ValueError:
                return Response(
                    {"error": "Invalid Google token"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            try:
                user = User.objects.get(email=email)
                token = default_token_generator.make_token(user)
                # In a real app, this would be a link to your frontend mobile deep link
                reset_link = (
                    f"relationshipai://reset-password?email={email}&token={token}"
                )

                send_mail(
                    "Password Reset Request",
                    f"Use the following link to reset your password: {reset_link}",
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
            except User.DoesNotExist:
                # Security: Don't reveal if user exists
                pass

            return Response(
                {
                    "detail": "If an account exists with this email, a reset link has been sent."
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = request.data.get("email")  # Expecting email in payload too
            token = serializer.validated_data["token"]
            new_password = serializer.validated_data["new_password"]

            try:
                user = User.objects.get(email=email)
                if default_token_generator.check_token(user, token):
                    user.set_password(new_password)
                    user.save()
                    return Response(
                        {"detail": "Password has been successfully reset."},
                        status=status.HTTP_200_OK,
                    )
                return Response(
                    {"error": "Invalid or expired token"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AuthorizeView(views.APIView):
    permission_classes = [AllowAny]
    """
    GET /api/v1/auth/authorize
    Requires user to be authenticated (e.g. via session for web or pre-existing flow).
    For MVP, we'll assume the user is passed in or we use basic auth / session.
    Returns an auth code via redirect.
    """

    def get(self, request):
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        code_challenge = request.query_params.get("code_challenge")
        code_challenge_method = request.query_params.get(
            "code_challenge_method", "S256"
        )
        redirect_uri = request.query_params.get("redirect_uri")
        state = request.query_params.get("state")

        if not code_challenge or not redirect_uri:
            return Response(
                {"error": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Generate auth code
        code = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(minutes=10)

        AuthCode.objects.create(
            user=request.user,
            code_hash=code,  # In production, hash this
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            expires_at=expires_at,
            redirect_uri=redirect_uri,
        )

        # Redirect back to mobile app
        params = f"?code={code}"
        if state:
            params += f"&state={state}"

        from django.http import HttpResponse

        response = HttpResponse(status=302)
        response["Location"] = f"{redirect_uri}{params}"
        return response


class TokenView(views.APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthAttemptThrottle]

    def post(self, request):
        grant_type = request.data.get("grant_type")
        if grant_type != "authorization_code":
            return Response(
                {"error": "Unsupported grant type"}, status=status.HTTP_400_BAD_REQUEST
            )

        code = request.data.get("code")
        code_verifier = request.data.get("code_verifier")

        try:
            auth_code = AuthCode.objects.get(code_hash=code)
            if timezone.now() > auth_code.expires_at:
                auth_code.delete()
                return Response(
                    {"error": "Code expired"}, status=status.HTTP_400_BAD_REQUEST
                )

            # Validate PKCE
            if not validate_pkce(
                code_verifier, auth_code.code_challenge, auth_code.code_challenge_method
            ):
                auth_code.delete()
                return Response(
                    {"error": "Invalid code_verifier"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user = auth_code.user
            auth_code.delete()

            # Issue tokens
            access_token, payload = generate_jwt(
                user, ["session:read", "session:write"]
            )
            refresh_token_record, refresh_token_plaintext = create_refresh_token_record(
                user
            )

            return Response(
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token_plaintext,
                    "token_type": "Bearer",
                    "expires_in": 900,  # 15 minutes
                }
            )

        except AuthCode.DoesNotExist:
            return Response(
                {"error": "Invalid code"}, status=status.HTTP_400_BAD_REQUEST
            )


class RefreshView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            return Response(
                {"error": "Refresh token required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # We need to find the token record by something other than the plaintext if we had a non-reversible hash.
        # But we are using Argon2 which is slow. We should store a lookup ID (JTI) in the token string or separately.
        # For simplicity, we'll assume the refresh_token is a composite string: "jti:plaintext"
        if ":" not in refresh_token:
            return Response(
                {"error": "Invalid refresh token format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        jti, plaintext = refresh_token.split(":", 1)
        try:
            old_rt = RefreshToken.objects.get(jti=jti)
            new_rt, new_plaintext = rotate_refresh_token(old_rt, plaintext)

            access_token, _ = generate_jwt(
                new_rt.user, ["session:read", "session:write"]
            )

            return Response(
                {
                    "access_token": access_token,
                    "refresh_token": f"{new_rt.jti}:{new_plaintext}",
                    "token_type": "Bearer",
                    "expires_in": 900,
                }
            )

        except (RefreshToken.DoesNotExist, ValidationError):
            return Response(
                {"error": "Invalid refresh token"}, status=status.HTTP_401_UNAUTHORIZED
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_401_UNAUTHORIZED)


class RevokeView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Invalidates refresh token family
        refresh_token = request.data.get("refresh_token")
        if not refresh_token or ":" not in refresh_token:
            return Response(
                {"error": "Invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST
            )

        jti, _ = refresh_token.split(":", 1)
        try:
            rt = RefreshToken.objects.get(jti=jti)
            revoke_family(rt.family_id)
            return Response({"status": "revoked"})
        except (RefreshToken.DoesNotExist, ValidationError):
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)


class LogoutView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Revoke all active sessions for user
        RefreshToken.objects.filter(user=request.user).delete()
        # Also blacklist the current access token's JTI if present
        if hasattr(request, "token_claims") and request.token_claims:
            jti = request.token_claims.get("jti")
            exp = request.token_claims.get("exp")
            now = timezone.now().timestamp()
            ttl = int(exp - now)
            if ttl > 0:
                cache.set(f"revoked_jti:{jti}", True, timeout=ttl)

        return Response({"status": "logged_out"})


class MeView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
