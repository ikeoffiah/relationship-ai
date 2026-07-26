"""Tests for Two Truths & a Lie."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.engagement.models import TwoTruthsPlay
from apps.relationships.models import Relationship

User = get_user_model()

BASE = "/api/v1/engagement/two-truths"


def make_couple():
    a = User.objects.create_user(email="a@e.com", password="pw", full_name="Alex")
    b = User.objects.create_user(email="b@e.com", password="pw", full_name="Blake")
    rel = Relationship.objects.create(partner_a=a, partner_b=b, status="active")
    return a, b, rel


class AuthorTests(APITestCase):
    def setUp(self):
        self.a, self.b, self.rel = make_couple()
        self.client.force_authenticate(self.a)

    def test_author_stores_statements(self):
        r = self.client.post(BASE + "/author", {
            "statements": ["I ran a marathon", "I hate coffee", "I speak Japanese"],
            "lie_index": 1,
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data["authored"])
        play = TwoTruthsPlay.objects.get(user=self.a)
        self.assertEqual(play.lie_index, 1)

    def test_author_requires_exactly_three(self):
        r = self.client.post(BASE + "/author", {
            "statements": ["only", "two"], "lie_index": 0,
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_author_rejects_bad_lie_index(self):
        r = self.client.post(BASE + "/author", {
            "statements": ["a", "b", "c"], "lie_index": 5,
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_author_rejects_empty_statement(self):
        r = self.client.post(BASE + "/author", {
            "statements": ["a", "  ", "c"], "lie_index": 0,
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_solo_user_cannot_author(self):
        solo = User.objects.create_user(email="s@e.com", password="pw", full_name="Sol")
        self.client.force_authenticate(solo)
        r = self.client.post(BASE + "/author", {
            "statements": ["a", "b", "c"], "lie_index": 0,
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


class GuessAndRevealTests(APITestCase):
    def setUp(self):
        self.a, self.b, self.rel = make_couple()

    def _author(self, user, lie_index):
        self.client.force_authenticate(user)
        self.client.post(BASE + "/author", {
            "statements": ["s0", "s1", "s2"], "lie_index": lie_index,
        }, format="json")

    def _guess(self, user, guess_index):
        self.client.force_authenticate(user)
        return self.client.post(BASE + "/guess", {"guess_index": guess_index}, format="json")

    def test_cannot_guess_before_partner_authors(self):
        self._author(self.a, 0)
        # A tries to guess B's lie, but B hasn't authored.
        r = self._guess(self.a, 1)
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)

    def test_partner_statements_hidden_lie_until_reveal(self):
        self._author(self.a, 0)
        self._author(self.b, 2)
        # A sees B's statements but NOT which is the lie.
        self.client.force_authenticate(self.a)
        r = self.client.get(BASE)
        self.assertEqual(r.data["partner_statements"], ["s0", "s1", "s2"])
        self.assertNotIn("reveal", r.data)
        self.assertIsNone(r.data.get("partner_lie_index"))

    def test_full_round_reveals_with_scoring(self):
        self._author(self.a, 0)  # A's lie is index 0
        self._author(self.b, 2)  # B's lie is index 2
        self._guess(self.a, 2)   # A guesses B's lie is 2 -> correct
        self._guess(self.b, 1)   # B guesses A's lie is 1 -> wrong (A's lie is 0)

        self.client.force_authenticate(self.a)
        r = self.client.get(BASE)
        self.assertTrue(r.data["revealed"])
        reveal = r.data["reveal"]
        self.assertEqual(reveal["partner_lie_index"], 2)
        self.assertTrue(reveal["i_caught_them"])    # A caught B
        self.assertFalse(reveal["they_caught_me"])  # B missed A

        # Symmetric from B's side.
        self.client.force_authenticate(self.b)
        rb = self.client.get(BASE).data["reveal"]
        self.assertFalse(rb["i_caught_them"])   # B missed A
        self.assertTrue(rb["they_caught_me"])   # A caught B

    def test_reveal_only_after_both_guess(self):
        self._author(self.a, 0)
        self._author(self.b, 2)
        self._guess(self.a, 2)
        # B hasn't guessed yet -> no reveal for anyone.
        self.client.force_authenticate(self.a)
        self.assertFalse(self.client.get(BASE).data["revealed"])

    def test_reset_clears_both_plays(self):
        self._author(self.a, 0)
        self._author(self.b, 1)
        self.client.force_authenticate(self.a)
        r = self.client.post(BASE + "/reset")
        self.assertTrue(r.data["reset"])
        self.assertEqual(TwoTruthsPlay.objects.filter(relationship=self.rel).count(), 0)


class AuthTests(APITestCase):
    def test_auth_required(self):
        for method, path in [
            ("get", BASE),
            ("post", BASE + "/author"),
            ("post", BASE + "/guess"),
        ]:
            resp = getattr(self.client, method)(path)
            self.assertIn(resp.status_code, (401, 403))
