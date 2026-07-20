import re
from django.contrib.auth import get_user_model
from django.core import mail
from rest_framework.test import APITestCase
from rest_framework import status
from apps.relationships.models import Relationship, RelationshipInvite

User = get_user_model()


def extract_invite_token(email_message):
    """
    The plaintext invite token is never persisted (only its SHA-256 hash is,
    via RelationshipInvite.token_hash). The only place it appears is the
    invite email, so tests recover it the same way a real invitee would.
    """
    match = re.search(r"accept-invite\?token=([\w\-]+)", email_message.body)
    assert match, f"No invite token found in email body: {email_message.body!r}"
    return match.group(1)


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

        # The relationship itself is only created once the invite is accepted.
        self.assertEqual(Relationship.objects.count(), 0)
        self.assertEqual(RelationshipInvite.objects.count(), 1)

        invite = RelationshipInvite.objects.first()
        self.assertEqual(invite.status, 'pending')
        self.assertEqual(invite.inviter_id, self.user_a.id)
        self.assertEqual(invite.invitee_email, 'partner_b@example.com')
        self.assertEqual(response.data['invite_id'], str(invite.id))

        # Plaintext token is emailed, never stored.
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(invite.token_hash)
        self.assertNotIn(invite.token_hash, mail.outbox[0].body)

    def test_accept_invite(self):
        """Test accepting an invite."""
        # First send invite
        self.client.post('/api/v1/relationships/invite', {
            'invitee_email': 'partner_b@example.com'
        })
        invite = RelationshipInvite.objects.first()
        token = extract_invite_token(mail.outbox[0])

        # Authenticate as Partner B
        self.client.force_authenticate(user=self.user_b)
        response = self.client.post(f'/api/v1/relationships/accept/{token}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        invite.refresh_from_db()
        self.assertEqual(invite.status, 'accepted')

        rel = Relationship.objects.get(id=response.data['relationship_id'])
        self.assertEqual(rel.status, 'active')
        self.assertEqual(rel.partner_a_id, self.user_a.id)
        self.assertEqual(rel.partner_b_id, self.user_b.id)

    def test_single_active_relationship_constraint(self):
        """Test that a user cannot be in two active relationships."""
        # Make user_a already in an active relationship with a real third user
        existing_partner = User.objects.create_user(
            email="existing_partner@example.com",
            password="password123",
        )
        Relationship.objects.create(
            partner_a=self.user_a,
            partner_b=existing_partner,
            status='active'
        )

        response = self.client.post('/api/v1/relationships/invite', {
            'invitee_email': 'someone_else@example.com'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already in an active relationship", response.data['error'])
        self.assertEqual(RelationshipInvite.objects.count(), 0)

    def test_dissolve_relationship(self):
        """Test dissolving a relationship."""
        rel = Relationship.objects.create(
            partner_a=self.user_a,
            partner_b=self.user_b,
            status='active'
        )

        response = self.client.delete(f'/api/v1/relationships/{rel.id}')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        rel.refresh_from_db()
        self.assertEqual(rel.status, 'dissolved')
        self.assertIsNotNone(rel.dissolved_at)
