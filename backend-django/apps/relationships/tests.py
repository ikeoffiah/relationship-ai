import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from apps.relationships.models import Relationship, RelationshipInvite
from apps.relationships.serializers import RelationshipSerializer

User = get_user_model()

class RelationshipPairingTests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            email="partner_a@example.com", 
            password="password123",
            full_name="Partner A"
        )
        self.user_b = User.objects.create_user(
            email="partner_b@example.com", 
            password="password123",
            full_name="Partner B"
        )
        self.client.force_authenticate(user=self.user_a)

    def test_invite_partner(self):
        """Test sending an invite to a partner."""
        response = self.client.post('/api/v1/relationships/invite', {
            'invitee_email': 'partner_b@example.com'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Relationship.objects.count(), 1)
        self.assertEqual(RelationshipInvite.objects.count(), 1)
        
        rel = Relationship.objects.first()
        self.assertEqual(rel.status, 'pending')
        self.assertEqual(rel.partner_a_id, self.user_a.id)

    def test_accept_invite(self):
        """Test accepting an invite."""
        # First send invite
        self.client.post('/api/v1/relationships/invite', {
            'invitee_email': 'partner_b@example.com'
        })
        invite = RelationshipInvite.objects.first()
        
        # Authenticate as Partner B
        self.client.force_authenticate(user=self.user_b)
        response = self.client.post('/api/v1/relationships/accept', {
            'token': invite.token
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        rel = Relationship.objects.first()
        self.assertEqual(rel.status, 'active')
        self.assertEqual(rel.partner_b_id, self.user_b.id)

    def test_single_active_relationship_constraint(self):
        """Test that a user cannot be in two active relationships."""
        # Make user_a already in an active relationship
        Relationship.objects.create(
            partner_a_id=self.user_a.id,
            partner_b_id=uuid.uuid4(),
            status='active'
        )
        
        response = self.client.post('/api/v1/relationships/invite', {
            'invitee_email': 'someone_else@example.com'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already in an active relationship", response.data['error'])

    def test_dissolve_relationship(self):
        """Test dissolving a relationship."""
        rel = Relationship.objects.create(
            partner_a_id=self.user_a.id,
            partner_b_id=self.user_b.id,
            status='active'
        )
        
        response = self.client.delete(f'/api/v1/relationships/{rel.id}')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        rel.refresh_from_db()
        self.assertEqual(rel.status, 'dissolved')
        self.assertEqual(rel.dissolved_by, self.user_a.id)
        self.assertIsNotNone(rel.dissolved_at)
