from datetime import date

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User, AgeVerification
from apps.accounts.services.age_verification import (
    verify_user_age,
    handle_minor_guardian_abuse_disclosure
)


def dob_for_age(age):
    """Return an ISO date string for someone who turned `age` yesterday."""
    today = date.today()
    return date(today.year - age, 1, 1).isoformat()


class AgeVerificationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@example.com",
            password="password123"
        )
        self.client.force_authenticate(user=self.user)
        self.verify_url = reverse("verify-age")

    def test_minor_self_report_blocked(self):
        """User under 13 self-reporting is blocked immediately (COPPA)."""
        response = self.client.post(self.verify_url, {"dob": dob_for_age(10)})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"], "minor_blocked")

        verification = AgeVerification.objects.get(user=self.user)
        self.assertEqual(verification.status, "blocked")

    def test_minor_self_report_requires_guardian_consent(self):
        """A 13-17 year old is routed to guardian consent rather than verified."""
        response = self.client.post(self.verify_url, {"dob": dob_for_age(15)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "guardian_consent_required")
        self.assertIs(response.data["is_minor"], True)

        # No verification is granted until a guardian consents.
        self.assertFalse(
            AgeVerification.objects.filter(
                user=self.user, status="verified"
            ).exists()
        )

    def test_adult_self_report_initiates_verification(self):
        """User 18 or over completes verification."""
        response = self.client.post(self.verify_url, {"dob": dob_for_age(25)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "verified")
        self.assertIs(response.data["is_minor"], False)

        verification = AgeVerification.objects.get(user=self.user)
        self.assertEqual(verification.status, "verified")

        self.user.refresh_from_db()
        self.assertTrue(self.user.age_verified)
        self.assertFalse(self.user.is_minor)

    def test_missing_dob_rejected(self):
        """A request without a date of birth is rejected."""
        response = self.client.post(self.verify_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_guardian_abuse_disclosure_suspends_access(self):
        """handle_minor_guardian_abuse_disclosure suspends guardian access."""
        # Setup a minor with parental consent
        verify_user_age(self.user, "parental_consent", {"status": "verified"})
        verification = self.user.age_verification
        self.assertEqual(verification.method, "parental_consent")

        # Trigger disclosure handling
        result = handle_minor_guardian_abuse_disclosure("session_123", str(self.user.id))

        self.assertTrue(result)
        verification.refresh_from_db()
        self.assertEqual(verification.status, "blocked")
        self.assertEqual(verification.blocked_reason, "Guardian abuse disclosure")

    def test_decorator_blocks_unverified_user(self):
        """Endpoints using require_age_verified block pending/unverified users."""
        from apps.accounts.decorators import require_age_verified
        from django.http import HttpResponse
        from unittest.mock import MagicMock

        @require_age_verified
        def dummy_view(request):
            return HttpResponse("Success")

        def make_request():
            # Reload the user each time so the reverse one-to-one cache does
            # not mask changes made by verify_user_age, mirroring how a real
            # request loads the user fresh from the DB.
            request = MagicMock()
            request.user = User.objects.get(pk=self.user.pk)
            return request

        # 1. Not started
        response = dummy_view(make_request())
        self.assertEqual(response.status_code, 403)

        # 2. Pending
        verify_user_age(self.user, "id_verification", {"status": "pending"})
        response = dummy_view(make_request())
        self.assertEqual(response.status_code, 403)

        # 3. Verified
        verify_user_age(self.user, "id_verification", {"status": "verified"})
        response = dummy_view(make_request())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Success")
