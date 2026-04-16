import pytest
from uuid import uuid4
from django.urls import reverse
from rest_framework.test import APIClient
from apps.consent.models import UserConsent, ConsentAuditEntry

@pytest.mark.django_db
class TestConsentAPI:
    def setup_method(self):
        self.client = APIClient()

    def test_get_consent_authenticated_owner(self, django_user_model):
        user = django_user_model.objects.create_user(
            email="api_owner@example.com", password="password123"
        )
        self.client.force_authenticate(user=user)
        
        url = reverse("user-consent", kwargs={"user_id": user.id})
        response = self.client.get(url)
        
        assert response.status_code == 200
        assert response.data["user_id"] == str(user.id)
        assert response.data["session_transcript_retention"] == "per_session"

    def test_get_consent_unauthorized_user(self, django_user_model):
        owner = django_user_model.objects.create_user(
            email="owner@example.com", password="password123"
        )
        other_user = django_user_model.objects.create_user(
            email="attacker@example.com", password="password123"
        )
        
        self.client.force_authenticate(user=other_user)
        
        url = reverse("user-consent", kwargs={"user_id": owner.id})
        response = self.client.get(url)
        
        assert response.status_code == 403

    def test_put_consent_updates_field_and_audit_log(self, django_user_model):
        user = django_user_model.objects.create_user(
            email="updater@example.com", password="password123"
        )
        self.client.force_authenticate(user=user)
        
        url = reverse("user-consent", kwargs={"user_id": user.id})
        data = {
            "session_transcript_retention": "30_days",
            "therapist_summary_access": True
        }
        
        # Pass optional session context via headers
        session_id = str(uuid4())
        response = self.client.put(url, data, headers={"X-Session-Context": session_id})
        
        assert response.status_code == 200
        assert response.data["session_transcript_retention"] == "30_days"
        assert response.data["therapist_summary_access"] is True
        
        # Verify audit logs
        audit_logs = ConsentAuditEntry.objects.filter(user_id=user.id)
        assert audit_logs.count() == 2
        
        # Check session context was preserved
        # Note: Depending on the backend model implementation, ensure session_context is correctly cast and stored
        for log in audit_logs:
            assert str(log.session_context) == session_id

    def test_put_consent_ignores_read_only_user_id(self, django_user_model):
        user = django_user_model.objects.create_user(
            email="readonly@example.com", password="password123"
        )
        self.client.force_authenticate(user=user)
        
        new_user_id = str(uuid4())
        url = reverse("user-consent", kwargs={"user_id": user.id})
        data = {
            "user_id": new_user_id,
            "session_transcript_retention": "1_year"
        }
        
        response = self.client.put(url, data)
        assert response.status_code == 200
        assert response.data["user_id"] == str(user.id) # Should NOT have changed
        
        consent = UserConsent.objects.get(user_id=user.id)
        assert str(consent.user_id) == str(user.id)

    def test_unauthenticated_access_denied(self, django_user_model):
        user_id = uuid4()
        url = reverse("user-consent", kwargs={"user_id": user_id})
        
        response = self.client.get(url)
        # DRF returns 403 Forbidden for unauthenticated users when no custom authenticators 
        # are configured that handle the specific protocol (JWT middleware handles auth at Django level).
        assert response.status_code == 403

    def test_handle_django_validation_error(self, django_user_model):
        from unittest.mock import patch
        from django.core.exceptions import ValidationError as DjangoValidationError
        
        user = django_user_model.objects.create_user(
            email="validation@example.com", password="password123"
        )
        self.client.force_authenticate(user=user)
        
        url = reverse("user-consent", kwargs={"user_id": user.id})
        
        with patch('apps.consent.serializers.UserConsentSerializer.save') as mock_save:
            mock_save.side_effect = DjangoValidationError("Direct model validation failure")
            response = self.client.put(url, {"session_transcript_retention": "30_days"})
            
            assert response.status_code == 400
            assert str(response.data[0]) == "Direct model validation failure"
