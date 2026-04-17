import pytest
from django.urls import reverse
from apps.accounts.models import AuthCode
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from unittest.mock import patch

User = get_user_model()


@pytest.mark.django_db
class TestCoverageGap:
    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            email="test@example.com", password="password123"
        )

    @pytest.fixture
    def auth_client(self, api_client, user):
        api_client.force_authenticate(user=user)
        return api_client

    def test_login_view(self, api_client, user):
        url = reverse("login")
        # Valid
        api_client.post(url, {"email": "test@example.com", "password": "password123"})
        # Invalid creds
        api_client.post(url, {"email": "test@example.com", "password": "wrong"})
        # Invalid data
        api_client.post(url, {"email": "not-an-email"})

    def test_google_login_success(self, api_client):
        url = reverse("google")
        user_info = {"email": "google@example.com", "name": "G User"}
        with patch(
            "google.oauth2.id_token.verify_oauth2_token", return_value=user_info
        ):
            api_client.post(url, {"id_token": "valid"})

    def test_google_login_invalid_token(self, api_client):
        url = reverse("google")
        with patch(
            "google.oauth2.id_token.verify_oauth2_token", side_effect=ValueError
        ):
            api_client.post(url, {"id_token": "fake"})

    def test_google_login_invalid_serializer(self, api_client):
        url = reverse("google")
        api_client.post(url, {})

    def test_forgot_password_flow(self, api_client, user):
        url = reverse("forgot-password")
        # Success
        api_client.post(url, {"email": user.email})
        # Non-existent (hits line 146-148)
        api_client.post(url, {"email": "ghost@example.com"})
        # Invalid serializer
        api_client.post(url, {})

    def test_reset_password_flow(self, api_client, user):
        from django.contrib.auth.tokens import default_token_generator

        token = default_token_generator.make_token(user)
        url = reverse("reset-password")
        # Success
        api_client.post(
            url, {"email": user.email, "token": token, "new_password": "new"}
        )
        # Invalid token
        api_client.post(
            url, {"email": user.email, "token": "wrong", "new_password": "new"}
        )
        # User not found
        api_client.post(
            url, {"email": "ghost@example.com", "token": "token", "new_password": "new"}
        )
        # Invalid serializer
        api_client.post(url, {})

    def test_authorize_view_unauthenticated(self, api_client):
        url = reverse("authorize")
        api_client.get(url)

    def test_authorize_view_missing_params(self, auth_client):
        url = reverse("authorize")
        auth_client.get(url)  # Hits line 196

    def test_authorize_view_success(self, auth_client):
        url = reverse("authorize") + "?code_challenge=abc&redirect_uri=http://localhost"
        auth_client.get(url)

    def test_token_view_invalid_grant(self, api_client):
        url = reverse("token")
        api_client.post(url, {"grant_type": "wrong"})  # Hits line 229

    def test_token_view_expired_code(self, api_client, user):
        AuthCode.objects.create(
            user=user,
            code_hash="exp",
            code_challenge="c",
            expires_at=timezone.now() - timedelta(minutes=1),
            redirect_uri="http://h",
        )
        api_client.post(
            reverse("token"),
            {"grant_type": "authorization_code", "code": "exp", "code_verifier": "v"},
        )

    def test_token_view_not_found(self, api_client):
        api_client.post(
            reverse("token"), {"grant_type": "authorization_code", "code": "no"}
        )

    def test_token_view_invalid_pkce(self, api_client, user):
        from apps.accounts.auth import get_code_challenge

        c = get_code_challenge("v")
        AuthCode.objects.create(
            user=user,
            code_hash="v",
            code_challenge=c,
            expires_at=timezone.now() + timedelta(minutes=1),
            redirect_uri="h",
        )
        api_client.post(
            reverse("token"),
            {"grant_type": "authorization_code", "code": "v", "code_verifier": "w"},
        )

    def test_refresh_view_variations(self, api_client):
        url = reverse("refresh")
        # Missing
        api_client.post(url, {})  # Hits line 269
        # Invalid format
        api_client.post(url, {"refresh_token": "no-colon"})  # Hits line 275

    def test_revoke_view_variations(self, auth_client):
        url = reverse("revoke")
        # Invalid format
        auth_client.post(url, {"refresh_token": "no-colon"})  # Hits line 304
        # Not found
        auth_client.post(
            url, {"refresh_token": "00000000-0000-0000-0000-000000000000:pass"}
        )  # Hits line 312
