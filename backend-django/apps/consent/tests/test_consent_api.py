import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.relationships.models import Relationship
from apps.consent.models import UserConsent, ConsentChangeLog
from apps.consent.gate import ConsentGate

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def setup_user():
    user = User.objects.create_user(email="test@example.com", password="password123")
    # UserConsent is created by signal or manually if needed, but let's ensure it exists
    consent, _ = UserConsent.objects.get_or_create(user=user)
    return user, consent

@pytest.mark.django_db
class TestConsentAPI:
    def test_get_consent_detail(self, api_client, setup_user):
        user, consent = setup_user
        api_client.force_authenticate(user=user)
        
        url = reverse("consent-detail", kwargs={"user_id": user.id})
        response = api_client.get(url)
        
        assert response.status_code == 200
        assert "plain_language_summary" in response.data["data"]
        assert response.data["data"]["joint_session_participation"] == "not_enrolled"

    def test_put_consent_validation_no_partner(self, api_client, setup_user):
        user, consent = setup_user
        api_client.force_authenticate(user=user)
        
        url = reverse("consent-detail", kwargs={"user_id": user.id})
        response = api_client.put(url, {"joint_session_participation": "enrolled"})
        
        assert response.status_code == 400
        assert "relationship" in response.data

    def test_put_consent_success_with_partner(self, api_client, setup_user):
        user, consent = setup_user
        partner = User.objects.create_user(email="partner@example.com", password="password123")
        Relationship.objects.create(partner_a_id=user.id, partner_b_id=partner.id, status='active')
        
        api_client.force_authenticate(user=user)
        url = reverse("consent-detail", kwargs={"user_id": user.id})
        response = api_client.put(url, {"joint_session_participation": "enrolled"})
        
        assert response.status_code == 200
        assert response.data["data"]["joint_session_participation"] == "enrolled"
        
        # Verify history entry
        assert ConsentChangeLog.objects.filter(user=user, dimension="joint_session_participation").exists()

    def test_model_improvement_acknowledgment_required(self, api_client, setup_user):
        user, consent = setup_user
        api_client.force_authenticate(user=user)
        
        url = reverse("consent-detail", kwargs={"user_id": user.id})
        response = api_client.put(url, {"model_improvement_data": True})
        
        assert response.status_code == 400
        assert "model_improvement_acknowledged" in response.data

    def test_consent_owner_permission(self, api_client, setup_user):
        user, consent = setup_user
        other_user = User.objects.create_user(email="other@example.com", password="password123")
        UserConsent.objects.create(user=other_user)
        
        api_client.force_authenticate(user=user)
        url = reverse("consent-detail", kwargs={"user_id": other_user.id})
        response = api_client.get(url)
        
        assert response.status_code == 404 # get_object_or_404 returns 404 for object doesn't exist, but permission check happens before that? 
        # Actually get_object_or_404 is in the view.

    def test_consent_gate_caching(self, setup_user):
        user, consent = setup_user
        
        # First call - cache miss
        policy1 = ConsentGate.get_access_policy(str(user.id))
        assert policy1.joint_session_participation == "not_enrolled"
        
        # Update DB directly
        consent.joint_session_participation = "enrolled"
        consent.save(update_fields=['joint_session_participation']) 
        # Wait, the save override invalidates the cache.
        
        # So we check that the second call gets the NEW value
        policy2 = ConsentGate.get_access_policy(str(user.id))
        assert policy2.joint_session_participation == "enrolled"
