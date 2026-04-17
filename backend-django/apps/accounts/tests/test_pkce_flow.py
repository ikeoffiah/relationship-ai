import base64
import hashlib
import secrets
from django.urls import reverse
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class PKCEFlowTest(APITestCase):
    def setUp(self):
        self.password = "SecurePassword123!"
        self.user = User.objects.create_user(
            email="test@example.com", password=self.password, is_verified=True
        )
        self.register_url = reverse("register")
        self.authorize_url = reverse("authorize")
        self.token_url = reverse("token")

    def test_full_pkce_flow(self):
        # 1. Start authorize flow
        # Generate PKCE values
        code_verifier = secrets.token_urlsafe(64)
        sha256_hash = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = (
            base64.urlsafe_b64encode(sha256_hash).decode("ascii").rstrip("=")
        )

        self.client.force_login(self.user)

        redirect_uri = "com.relationshipai://oauth/callback"
        response = self.client.get(
            self.authorize_url,
            {
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "redirect_uri": redirect_uri,
                "state": "random_state",
            },
        )

        self.assertEqual(response.status_code, 302)
        redirect_url = (
            response.url if hasattr(response, "url") else response.get("Location")
        )
        self.assertIsNotNone(
            redirect_url,
            f"Response missing Location header. Status: {response.status_code}, Data: {response.content}",
        )
        self.assertIn("code=", redirect_url)
        self.assertIn("state=random_state", redirect_url)

        # Extract code from redirect URL
        code = redirect_url.split("code=")[1].split("&")[0]

        # 2. Exchange code for token
        self.client.force_authenticate(user=None)  # Token endpoint is public

        token_response = self.client.post(
            self.token_url,
            {
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": code_verifier,
                "redirect_uri": redirect_uri,
            },
        )

        self.assertEqual(token_response.status_code, 200)
        self.assertIn("access_token", token_response.data)
        self.assertIn("refresh_token", token_response.data)
        self.assertEqual(token_response.data["token_type"], "Bearer")

    def test_invalid_pkce_verifier(self):
        # 1. Authorize
        code_verifier = secrets.token_urlsafe(64)
        sha256_hash = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = (
            base64.urlsafe_b64encode(sha256_hash).decode("ascii").rstrip("=")
        )

        self.client.force_login(self.user)
        response = self.client.get(
            self.authorize_url,
            {
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "redirect_uri": "app://callback",
            },
        )
        redirect_url = (
            response.url if hasattr(response, "url") else response.get("Location")
        )
        self.assertIsNotNone(
            redirect_url,
            f"Response missing Location header. Status: {response.status_code}",
        )
        code = redirect_url.split("code=")[1]

        # 2. Exchange with WRONG verifier
        self.client.force_authenticate(user=None)
        token_response = self.client.post(
            self.token_url,
            {
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": "wrong_verifier",
                "redirect_uri": "app://callback",
            },
        )

        self.assertEqual(token_response.status_code, 400)
        self.assertEqual(token_response.data["error"], "Invalid code_verifier")
