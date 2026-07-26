"""Tests for consensual Focus Mode."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.engagement.models import FocusSession
from apps.notifications.notification_models import Notification
from apps.relationships.models import Relationship

User = get_user_model()
BASE = "/api/v1/engagement/focus"


def make_couple():
    a = User.objects.create_user(email="a@e.com", password="pw", full_name="Alex")
    b = User.objects.create_user(email="b@e.com", password="pw", full_name="Blake")
    rel = Relationship.objects.create(partner_a=a, partner_b=b, status="active")
    return a, b, rel


class FocusProposeTests(APITestCase):
    def setUp(self):
        self.a, self.b, self.rel = make_couple()
        self.client.force_authenticate(self.a)

    def test_propose_creates_and_notifies_partner(self):
        r = self.client.post(BASE + "/propose", {"duration_minutes": 25}, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["session"]["status"], "proposed")
        self.assertTrue(r.data["session"]["i_initiated"])
        self.assertTrue(Notification.objects.filter(user_id=self.b.id, type="focus_proposed").exists())

    def test_duration_is_clamped(self):
        r = self.client.post(BASE + "/propose", {"duration_minutes": 9999}, format="json")
        self.assertLessEqual(r.data["session"]["duration_minutes"], 180)

    def test_second_proposal_conflicts(self):
        self.client.post(BASE + "/propose", {"duration_minutes": 20}, format="json")
        r = self.client.post(BASE + "/propose", {"duration_minutes": 20}, format="json")
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(FocusSession.objects.count(), 1)

    def test_solo_cannot_propose(self):
        solo = User.objects.create_user(email="s@e.com", password="pw", full_name="Sol")
        self.client.force_authenticate(solo)
        r = self.client.post(BASE + "/propose", {"duration_minutes": 20}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


class FocusAcceptEndTests(APITestCase):
    def setUp(self):
        self.a, self.b, self.rel = make_couple()

    def _propose(self, minutes=20):
        self.client.force_authenticate(self.a)
        self.client.post(BASE + "/propose", {"duration_minutes": minutes}, format="json")

    def test_partner_accepts_activates_with_timer(self):
        self._propose(minutes=30)
        self.client.force_authenticate(self.b)
        r = self.client.post(BASE + "/accept")
        self.assertEqual(r.data["session"]["status"], "active")
        self.assertIsNotNone(r.data["session"]["ends_at"])
        self.assertGreater(r.data["session"]["remaining_seconds"], 0)
        # Proposer is notified it started.
        self.assertTrue(Notification.objects.filter(user_id=self.a.id, type="focus_started").exists())

    def test_initiator_cannot_accept_own_invite(self):
        self._propose()
        self.client.force_authenticate(self.a)
        r = self.client.post(BASE + "/accept")
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)

    def test_partner_can_decline(self):
        self._propose()
        self.client.force_authenticate(self.b)
        r = self.client.post(BASE + "/decline")
        self.assertIsNone(r.data["session"])
        self.assertEqual(FocusSession.objects.get().status, "declined")

    def test_either_partner_can_end_active_session(self):
        # The core consent guarantee: the NON-initiator can end at any time.
        self._propose()
        self.client.force_authenticate(self.b)
        self.client.post(BASE + "/accept")
        # A (the initiator) ends it.
        self.client.force_authenticate(self.a)
        r = self.client.post(BASE + "/end")
        self.assertIsNone(r.data["session"])
        self.assertEqual(FocusSession.objects.get().status, "ended")

    def test_ending_active_awards_both_partners(self):
        self._propose()
        self.client.force_authenticate(self.b)
        self.client.post(BASE + "/accept")
        self.client.post(BASE + "/end")
        from apps.engagement.models import PointsLedger
        self.assertTrue(PointsLedger.objects.filter(user=self.a, reason="focus_completed").exists())
        self.assertTrue(PointsLedger.objects.filter(user=self.b, reason="focus_completed").exists())

    def test_accept_with_no_invite_is_404(self):
        self.client.force_authenticate(self.b)
        self.assertEqual(self.client.post(BASE + "/accept").status_code, status.HTTP_404_NOT_FOUND)

    def test_current_reflects_state(self):
        self._propose()
        self.client.force_authenticate(self.b)
        r = self.client.get(BASE)
        self.assertEqual(r.data["session"]["status"], "proposed")
        self.assertFalse(r.data["session"]["i_initiated"])


class FocusAuthTests(APITestCase):
    def test_auth_required(self):
        for method, path in [("get", BASE), ("post", BASE + "/propose"), ("post", BASE + "/end")]:
            resp = getattr(self.client, method)(path)
            self.assertIn(resp.status_code, (401, 403))
