import re
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework import status
from apps.audit.models import AuditEvent
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

    @override_settings(AUDIT_LOG_SYNCHRONOUS=True)
    def test_accept_invite_writes_audit_event(self):
        """Accepting an invite records a relationship_created audit event."""
        self.client.post('/api/v1/relationships/invite', {
            'invitee_email': 'partner_b@example.com'
        })
        token = extract_invite_token(mail.outbox[0])
        self.client.force_authenticate(user=self.user_b)
        response = self.client.post(f'/api/v1/relationships/accept/{token}')

        rel_id = response.data['relationship_id']
        # Match in Python on the id string: the audit logger writes on a
        # background thread via its own connection, so events from other tests
        # can persist outside this test's transaction — scope to THIS
        # relationship, and compare as strings to stay backend-agnostic.
        event = next(
            (e for e in AuditEvent.objects.filter(event_type='relationship_created')
             if str(e.relationship_id) == rel_id),
            None,
        )
        self.assertIsNotNone(event, "expected a relationship_created audit event")
        self.assertEqual(str(event.user_id), str(self.user_b.id))

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
        # Dissolution is unilateral, so it must record who performed it.
        self.assertEqual(rel.dissolved_by, self.user_a)


class RelationshipMeStateTests(APITestCase):
    """`GET /relationships/me` answers rather than erroring.

    "Do I have a partner?" has three ordinary answers and "no" is the commonest
    one on a new account. It used to 404 for that case, so the Journey Together
    screen — which you open *because* you have no partner — threw on every
    visit and rendered the exception text at the user.
    """

    def setUp(self):
        self.user = User.objects.create_user(email="me-state@t.local", password="pw12345!")
        self.client.force_authenticate(user=self.user)
        self.url = "/api/v1/relationships/me"

    def test_no_relationship_reads_as_not_connected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], "not_connected")

    def test_the_status_value_is_the_one_the_client_branches_on(self):
        """The client has always compared against 'not_connected'. The server
        never sent it — the two contracts were written independently and never
        met, which is why the screen worked only by falling through to an error
        handler."""
        self.assertEqual(self.client.get(self.url).json()["status"], "not_connected")

    def test_an_outstanding_invite_reads_as_pending(self):
        """Unreachable before this. The client has a `pending` branch and a
        "Waiting for … to accept" screen behind it, and the state it needed was
        never sent because the query only looked at active relationships."""
        from datetime import timedelta

        from django.utils import timezone

        RelationshipInvite.objects.create(
            inviter=self.user,
            invitee_email="them@t.local",
            token_hash="x" * 64,
            expires_at=timezone.now() + timedelta(hours=72),
        )
        body = self.client.get(self.url).json()
        self.assertEqual(body["status"], "pending")
        self.assertEqual(body["invitee_email"], "them@t.local")

    def test_an_expired_invite_is_not_pending(self):
        from datetime import timedelta

        from django.utils import timezone

        RelationshipInvite.objects.create(
            inviter=self.user,
            invitee_email="them@t.local",
            token_hash="y" * 64,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        self.assertEqual(self.client.get(self.url).json()["status"], "not_connected")

    def test_an_invite_sent_to_me_does_not_show_as_my_pending(self):
        """Only invites this user sent. One addressed to them is theirs to
        accept from the link, and surfacing it here would tell someone they had
        been invited before they chose to open it."""
        from datetime import timedelta

        from django.utils import timezone

        other = User.objects.create_user(email="sender@t.local", password="pw12345!")
        RelationshipInvite.objects.create(
            inviter=other,
            invitee_email=self.user.email,
            token_hash="z" * 64,
            expires_at=timezone.now() + timedelta(hours=72),
        )
        self.assertEqual(self.client.get(self.url).json()["status"], "not_connected")

    def test_an_active_relationship_still_returns_the_partner(self):
        partner = User.objects.create_user(email="partner@t.local", password="pw12345!")
        rel = Relationship.objects.create(
            partner_a=self.user, partner_b=partner, status="active"
        )
        body = self.client.get(self.url).json()
        self.assertEqual(body["status"], "active")
        self.assertEqual(body["id"], str(rel.id))
        self.assertEqual(body["partner"]["email"], "partner@t.local")

    def test_a_solo_relationship_returns_a_null_partner_rather_than_raising(self):
        """Solo is a supported state. The old code read partner.id
        unconditionally, so an active relationship with no partner_b would have
        raised a 500 here."""
        Relationship.objects.create(partner_a=self.user, status="active")
        body = self.client.get(self.url).json()
        self.assertEqual(body["status"], "active")
        self.assertIsNone(body["partner"])

    def test_it_still_requires_authentication(self):
        self.client.force_authenticate(user=None)
        self.assertIn(self.client.get(self.url).status_code, (401, 403))
