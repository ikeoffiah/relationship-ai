from django.urls import reverse
from rest_framework.test import APITestCase
from django.core.cache import cache
from django.contrib.auth import get_user_model

User = get_user_model()


class RateLimitingTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.register_url = reverse("register")

    def test_auth_attempt_rate_limit(self):
        email = "rate@example.com"
        # Attempt registration 20 times - should be ok (new limit is 20/hour)
        for i in range(20):
            response = self.client.post(
                self.register_url, {"email": email, "password": "password123"}
            )
            # First one is 201, rest are 400 (duplicate email)
            # Both should increment the throttle
            if i == 0:
                self.assertEqual(response.status_code, 201)
            else:
                self.assertEqual(response.status_code, 400)

        # 21st attempt should be rate limited
        response = self.client.post(
            self.register_url, {"email": email, "password": "password123"}
        )
        self.assertEqual(response.status_code, 429)
