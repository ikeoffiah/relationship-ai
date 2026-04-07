from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class UserModelTest(TestCase):
    def test_user_str(self):
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="password123"
        )
        self.assertEqual(str(user), f"test@example.com ({user.id})")
