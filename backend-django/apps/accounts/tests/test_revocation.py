from django.urls import reverse
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from apps.accounts.auth import generate_jwt
from django.core.cache import cache

User = get_user_model()


class RevocationTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="revoke@example.com", password="password123"
        )
        self.logout_url = reverse("logout")
        self.me_url = reverse("me")

    def test_token_revocation_on_logout(self):
        # 1. Get a token
        token, claims = generate_jwt(self.user, ["session:read"])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # 2. Logout - should blacklist the JTI
        logout_response = self.client.post(self.logout_url)
        self.assertEqual(logout_response.status_code, 200)

        # 3. Try to use it again - should fail middleware check
        me_response = self.client.get(self.me_url)
        self.assertEqual(me_response.status_code, 401)
        self.assertEqual(me_response.json()["error"], "Token revoked")
