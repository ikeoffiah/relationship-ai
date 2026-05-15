import uuid
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User, AgeVerification
from apps.accounts.services.age_verification import (
    verify_user_age, 
    handle_minor_guardian_abuse_disclosure
)

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
        """User under 18 self-reporting is blocked immediately."""
        from datetime import date
        today = date.today()
        # 17 years ago
        minor_year = today.year - 17
        
        response = self.client.post(self.verify_url, {
            "dob_month": today.month,
            "dob_year": minor_year
        })
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"], "minor_blocked")
        
        verification = AgeVerification.objects.get(user=self.user)
        self.assertEqual(verification.status, "blocked")

    def test_adult_self_report_initiates_verification(self):
        """User 18 or over initiates verification."""
        from datetime import date
        today = date.today()
        # 25 years ago
        adult_year = today.year - 25
        
        response = self.client.post(self.verify_url, {
            "dob_month": today.month,
            "dob_year": adult_year
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "pending")
        
        verification = AgeVerification.objects.get(user=self.user)
        self.assertEqual(verification.status, "pending")

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
        
        @require_age_verified
        def dummy_view(request):
            return HttpResponse("Success")
        
        # 1. Not started
        from unittest.mock import MagicMock
        request = MagicMock()
        request.user = self.user
        request.user.is_authenticated = True
        
        response = dummy_view(request)
        self.assertEqual(response.status_code, 403)
        
        # 2. Pending
        verify_user_age(self.user, "id_verification", {"status": "pending"})
        response = dummy_view(request)
        self.assertEqual(response.status_code, 403)
        
        # 3. Verified
        verify_user_age(self.user, "id_verification", {"status": "verified"})
        response = dummy_view(request)
        # In this mock setup, we just check if it passed the check
        self.assertNotEqual(response.status_code, 403)
