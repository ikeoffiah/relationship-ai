import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.accounts.models import User, AgeVerification
from apps.relationships.models import Relationship
from apps.consent.models import UserConsent
from apps.sessions.models import JointSession

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def setup_users():
    user_a = User.objects.create_user(email="partner_a@example.com", password="password123")
    user_b = User.objects.create_user(email="partner_b@example.com", password="password123")
    
    relationship = Relationship.objects.create(partner_a_id=user_a.id, partner_b_id=user_b.id, status='active')
    
    # Setup restrictive consent defaults (ensuring records exist with correct user mapping)
    consent_a, _ = UserConsent.objects.get_or_create(user=user_a)
    consent_b, _ = UserConsent.objects.get_or_create(user=user_b)
    
    # Setup age verification
    AgeVerification.objects.create(user=user_a, status='verified', method='card_check')
    AgeVerification.objects.create(user=user_b, status='verified', method='card_check')
    
    return user_a, user_b, relationship, consent_a, consent_b

@pytest.mark.django_db
class TestJointSessionConsentGate:
    def test_initiate_partner_not_enrolled(self, api_client, setup_users):
        user_a, user_b, relationship, consent_a, consent_b = setup_users
        api_client.force_authenticate(user=user_a)
        
        # consent_b.joint_session_participation is 'not_enrolled' by default
        response = api_client.post(reverse("joint_session_initiate"))
        assert response.status_code == 400
        assert response.data["error"] == "partner_not_enrolled"

    def test_full_confirmation_flow(self, api_client, setup_users):
        user_a, user_b, relationship, consent_a, consent_b = setup_users
        
        # Enroll both
        consent_a.joint_session_participation = 'enrolled'
        consent_a.save()
        consent_b.joint_session_participation = 'enrolled'
        consent_b.save()
        
        # Initiate
        api_client.force_authenticate(user=user_a)
        response = api_client.post(reverse("joint_session_initiate"))
        assert response.status_code == 201
        session_id = response.data["joint_session_id"]
        
        # Partner A confirms
        response = api_client.post(reverse("joint_session_confirm", kwargs={"session_id": session_id}))
        assert response.data["state"] == "PENDING_B"
        
        # Partner B confirms
        api_client.force_authenticate(user=user_b)
        response = api_client.post(reverse("joint_session_confirm", kwargs={"session_id": session_id}))
        assert response.data["state"] == "ACTIVE"
        assert response.data["both_confirmed"] is True

    def test_exit_at_any_time(self, api_client, setup_users):
        user_a, user_b, relationship, consent_a, consent_b = setup_users
        consent_a.joint_session_participation = 'enrolled'
        consent_a.save()
        consent_b.joint_session_participation = 'enrolled'
        consent_b.save()
        
        # Start session
        api_client.force_authenticate(user=user_a)
        res = api_client.post(reverse("joint_session_initiate"))
        session_id = res.data["joint_session_id"]
        
        # Exit even before activation
        response = api_client.post(reverse("joint_session_exit", kwargs={"session_id": session_id}))
        assert response.status_code == 200
        
        session = JointSession.objects.get(id=session_id)
        assert session.state == "EXITED"

    def test_consent_validation_failure_terminates_session(self, api_client, setup_users):
        user_a, user_b, relationship, consent_a, consent_b = setup_users
        consent_a.joint_session_participation = 'enrolled'
        consent_a.save()
        consent_b.joint_session_participation = 'enrolled'
        consent_b.save()
        
        # Un-verify user B's age
        av_b = AgeVerification.objects.get(user=user_b)
        av_b.status = 'pending'
        av_b.save()
        
        # Initiate and A confirms
        api_client.force_authenticate(user=user_a)
        res = api_client.post(reverse("joint_session_initiate"))
        session_id = res.data["joint_session_id"]
        api_client.post(reverse("joint_session_confirm", kwargs={"session_id": session_id}))
        
        # Partner B confirms -> should terminate due to failed validation
        api_client.force_authenticate(user=user_b)
        response = api_client.post(reverse("joint_session_confirm", kwargs={"session_id": session_id}))
        assert response.data["state"] == "TERMINATED"
