from django.urls import reverse
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from apps.accounts.models import RefreshToken
from apps.accounts.auth import create_refresh_token_record

User = get_user_model()


class TokenRotationTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="rotate@example.com", password="password123"
        )
        self.refresh_url = reverse("refresh")

    def test_successful_rotation(self):
        # Create initial token
        rt_record, plaintext = create_refresh_token_record(self.user)
        refresh_token_string = f"{rt_record.jti}:{plaintext}"

        response = self.client.post(
            self.refresh_url, {"refresh_token": refresh_token_string}
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)

        # Verify old token is marked as used
        rt_record.refresh_from_db()
        self.assertIsNotNone(rt_record.used_at)

    def test_reuse_detection_invalidates_family(self):
        # Create initial token
        rt_record, plaintext = create_refresh_token_record(self.user)
        refresh_token_string = f"{rt_record.jti}:{plaintext}"

        # Issue another token in same family just to have more than one
        create_refresh_token_record(self.user, family_id=rt_record.family_id)

        # First use - Success
        self.client.post(self.refresh_url, {"refresh_token": refresh_token_string})

        # Second use (REUSE) - Should fail and revoke family
        response = self.client.post(
            self.refresh_url, {"refresh_token": refresh_token_string}
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn("reuse detected", response.data["error"].lower())

        # Verify all tokens in family are gone
        self.assertEqual(
            RefreshToken.objects.filter(family_id=rt_record.family_id).count(), 0
        )

    def test_invalid_refresh_token(self):
        response = self.client.post(
            self.refresh_url, {"refresh_token": "nonexistent:token"}
        )
        self.assertEqual(response.status_code, 401)
