"""Tests for partner commitments (API + the reminder sweep)."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.engagement.models import Commitment
from apps.engagement.tasks import _deliver_commitments
from apps.notifications.notification_models import Notification
from apps.relationships.models import Relationship

User = get_user_model()

URL = "/api/v1/engagement/commitments"


def make_couple():
    a = User.objects.create_user(email="a@e.com", password="pw", full_name="Alex")
    b = User.objects.create_user(email="b@e.com", password="pw", full_name="Blake")
    rel = Relationship.objects.create(partner_a=a, partner_b=b, status="active")
    return a, b, rel


class CommitmentApiTests(APITestCase):
    def setUp(self):
        self.a, self.b, self.rel = make_couple()
        self.client.force_authenticate(self.a)

    def test_create_for_partner_is_private_no_partner_notification(self):
        r = self.client.post(URL, {"kind": "for_partner", "text": "Bring you coffee in bed"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        # A "for my partner" surprise does NOT notify the partner.
        self.assertFalse(
            Notification.objects.filter(user_id=self.b.id, type="commitment_created").exists()
        )

    def test_create_with_partner_notifies_partner(self):
        r = self.client.post(URL, {"kind": "with_partner", "text": "Cook dinner together Friday"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Notification.objects.filter(user_id=self.b.id, type="commitment_created").exists()
        )

    def test_partner_cannot_see_my_private_for_commitment(self):
        self.client.post(URL, {"kind": "for_partner", "text": "secret surprise"}, format="json")
        # B lists — must NOT see A's private "for" commitment.
        self.client.force_authenticate(self.b)
        r = self.client.get(URL)
        texts = {c["text"] for c in r.data["commitments"]}
        self.assertNotIn("secret surprise", texts)

    def test_both_see_with_commitments(self):
        self.client.post(URL, {"kind": "with_partner", "text": "weekly walk"}, format="json")
        for user in (self.a, self.b):
            self.client.force_authenticate(user)
            r = self.client.get(URL)
            self.assertIn("weekly walk", {c["text"] for c in r.data["commitments"]})

    def test_invalid_kind_rejected(self):
        r = self.client.post(URL, {"kind": "nonsense", "text": "x"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_done_and_cancel_remove_from_active_list(self):
        c = Commitment.objects.create(relationship=self.rel, created_by=self.a,
                                      kind="for_partner", text="water plants")
        r = self.client.post(f"{URL}/{c.id}/done")
        self.assertEqual(r.data["status"], "done")
        self.assertEqual(self.client.get(URL).data["commitments"], [])

    def test_cannot_touch_another_couples_commitment(self):
        c = Commitment.objects.create(relationship=self.rel, created_by=self.a,
                                      kind="for_partner", text="mine")
        outsider = User.objects.create_user(email="c@e.com", password="pw", full_name="Cass")
        self.client.force_authenticate(outsider)
        r = self.client.post(f"{URL}/{c.id}/done")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_solo_user_cannot_create(self):
        solo = User.objects.create_user(email="s@e.com", password="pw", full_name="Sol")
        self.client.force_authenticate(solo)
        r = self.client.post(URL, {"kind": "for_partner", "text": "x"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_auth_required(self):
        self.client.force_authenticate(user=None)
        self.assertIn(self.client.get(URL).status_code, (401, 403))


class CommitmentReminderSweepTests(APITestCase):
    def setUp(self):
        self.a, self.b, self.rel = make_couple()
        self.now = timezone.now()

    def _commitment(self, **kwargs):
        defaults = dict(relationship=self.rel, created_by=self.a, kind="for_partner",
                        text="do the thing", remind_at=self.now - timedelta(minutes=1))
        defaults.update(kwargs)
        return Commitment.objects.create(**defaults)

    def test_for_partner_reminder_goes_only_to_author(self):
        self._commitment(kind="for_partner")
        self.assertEqual(_deliver_commitments(now=self.now), 1)
        self.assertTrue(Notification.objects.filter(user_id=self.a.id, type="commitment_reminder").exists())
        self.assertFalse(Notification.objects.filter(user_id=self.b.id, type="commitment_reminder").exists())

    def test_with_partner_reminder_goes_to_both(self):
        self._commitment(kind="with_partner")
        self.assertEqual(_deliver_commitments(now=self.now), 1)
        self.assertTrue(Notification.objects.filter(user_id=self.a.id, type="commitment_reminder").exists())
        self.assertTrue(Notification.objects.filter(user_id=self.b.id, type="commitment_reminder").exists())

    def test_future_or_undated_do_not_fire(self):
        self._commitment(remind_at=self.now + timedelta(hours=1))
        self._commitment(remind_at=None)
        self.assertEqual(_deliver_commitments(now=self.now), 0)

    def test_sweep_is_idempotent(self):
        self._commitment(kind="for_partner")
        self.assertEqual(_deliver_commitments(now=self.now), 1)
        self.assertEqual(_deliver_commitments(now=self.now + timedelta(minutes=10)), 0)

    def test_done_commitment_does_not_fire(self):
        self._commitment(status="done")
        self.assertEqual(_deliver_commitments(now=self.now), 0)
