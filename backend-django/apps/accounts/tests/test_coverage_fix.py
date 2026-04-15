import pytest
import jwt
import uuid
import secrets
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.accounts.auth import (
    validate_pkce,
    decode_jwt,
    rotate_refresh_token,
    revoke_family,
    generate_jwt,
    create_refresh_token_record,
)
from apps.accounts.models import RefreshToken

User = get_user_model()


@pytest.mark.django_db
class TestAccountsCoverageGaps:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="gap@example.com", password="password")

    # --- auth.py tests ---

    def test_validate_pkce_invalid_method(self):
        # Line 32 gap
        assert validate_pkce("verifier", "challenge", method="plain") is False

    def test_decode_jwt_expired(self, monkeypatch):
        # Line 54 gap
        # Manually create an expired token
        payload = {
            "sub": str(self.user.id),
            "exp": (timezone.now() - timedelta(minutes=1)).timestamp(),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        
        with pytest.raises(ValueError, match="Token expired"):
            decode_jwt(token)

    def test_rotate_refresh_token_verify_error(self):
        # Lines 83-86 gap: ph.verify fails
        rt_record, _ = create_refresh_token_record(self.user)
        with pytest.raises(ValueError, match="Invalid refresh token"):
            rotate_refresh_token(rt_record, "wrong_plaintext")

    def test_rotate_refresh_token_expired(self, monkeypatch):
        # Line 96 gap
        rt_record, plaintext = create_refresh_token_record(self.user)
        # Mock the expiry check
        rt_record.expires_at = timezone.now() - timedelta(minutes=1)
        rt_record.save()
        
        with pytest.raises(ValueError, match="Refresh token expired"):
            rotate_refresh_token(rt_record, plaintext)

    def test_revoke_family_direct(self):
        # Line 109 gap
        family_id = uuid.uuid4()
        rt1, _ = create_refresh_token_record(self.user, family_id=family_id)
        rt2, _ = create_refresh_token_record(self.user, family_id=family_id)
        
        assert RefreshToken.objects.filter(family_id=family_id).count() == 2
        revoke_family(family_id)
        assert RefreshToken.objects.filter(family_id=family_id).count() == 0

    # --- middleware.py tests ---

    def test_middleware_user_not_found(self):
        # Lines 36-37 gap
        non_existent_id = uuid.uuid4()
        payload = {
            "sub": str(non_existent_id),
            "iat": timezone.now().timestamp(),
            "exp": (timezone.now() + timedelta(minutes=15)).timestamp(),
            "jti": str(uuid.uuid4()),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get("/api/v1/auth/me/")
        assert response.status_code == 401
        assert response.json()["error"] == "User not found"

    def test_middleware_generic_exception(self, monkeypatch):
        # Lines 41-42 gap
        # Force decode_jwt to raise a generic exception
        def mock_decode(token):
            raise Exception("Unexpected error")
        
        import apps.accounts.middleware
        monkeypatch.setattr("apps.accounts.middleware.decode_jwt", mock_decode)
        
        self.client.credentials(HTTP_AUTHORIZATION="Bearer valid_looking_token")
        response = self.client.get("/api/v1/auth/me/")
        assert response.status_code == 401
        assert response.json()["error"] == "Invalid token structure"

    # --- models.py tests ---

    def test_create_user_no_email(self):
        # Line 13 gap
        with pytest.raises(ValueError, match="The Email field must be set"):
            User.objects.create_user(email=None, password="password")

    def test_create_superuser_logic(self):
        # Lines 22-25 gap
        admin = User.objects.create_superuser(email="admin@example.com", password="password")
        assert admin.is_staff is True
        assert admin.is_superuser is True
        assert admin.is_verified is True

    # --- views.py tests ---

    def test_revoke_view_success(self):
        # Lines 376-377 gap in RevokeView
        rt_record, plaintext = create_refresh_token_record(self.user)
        composite_token = f"{rt_record.jti}:{plaintext}"
        
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/v1/auth/revoke/", {"refresh_token": composite_token})
        
        assert response.status_code == 200
        assert response.json()["status"] == "revoked"
        # Verify family is actually gone
        assert RefreshToken.objects.filter(family_id=rt_record.family_id).count() == 0
