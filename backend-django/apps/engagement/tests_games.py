"""Tests for the couple-games engine (Know Your Partner)."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.engagement.models import GamePack, GameQuestion, GamePlay, PointsLedger
from apps.notifications.notification_models import Notification
from apps.relationships.models import Relationship

User = get_user_model()


def make_couple(age_verified=False):
    a = User.objects.create_user(email="a@e.com", password="pw", full_name="Alex")
    b = User.objects.create_user(email="b@e.com", password="pw", full_name="Blake")
    if age_verified:
        User.objects.filter(pk__in=[a.pk, b.pk]).update(age_verified=True)
        a.refresh_from_db()
        b.refresh_from_db()
    rel = Relationship.objects.create(partner_a=a, partner_b=b, status="active")
    return a, b, rel


def make_pack(n=3, game_type="know_your_partner", category="relationship"):
    pack = GamePack.objects.create(
        key=f"pack-{category}-{game_type}", title="Test Pack",
        game_type=game_type, category=category,
    )
    for i in range(n):
        GameQuestion.objects.create(pack=pack, prompt=f"Q{i}?", options=["A", "B", "C"], order=i)
    return pack


def answers(client, pack, self_idx, guess_idx):
    """Submit self_idx and guess_idx for every question in the pack."""
    for q in pack.questions.all():
        client.post(
            f"/api/v1/engagement/games/{pack.key}/answer",
            {"question_id": str(q.id), "self_answer": self_idx, "guess_answer": guess_idx},
        )


class KnowYourPartnerTests(APITestCase):
    def setUp(self):
        self.a, self.b, self.rel = make_couple()
        self.pack = make_pack(n=3)

    def test_reveal_requires_both_partners(self):
        self.client.force_authenticate(self.a)
        answers(self.client, self.pack, self_idx=0, guess_idx=1)
        # A is done but B hasn't played — no reveal yet.
        r = self.client.get(f"/api/v1/engagement/games/{self.pack.key}")
        self.assertTrue(r.data["progress"]["i_complete"])
        self.assertFalse(r.data["progress"]["revealed"])
        self.assertNotIn("reveal", r.data)

        # B plays — now both complete, reveal unlocks.
        self.client.force_authenticate(self.b)
        answers(self.client, self.pack, self_idx=1, guess_idx=0)
        r = self.client.get(f"/api/v1/engagement/games/{self.pack.key}")
        self.assertTrue(r.data["progress"]["revealed"])
        self.assertIn("reveal", r.data)

    def test_scoring_counts_correct_guesses(self):
        # A always answers 0 about self and guesses 1 for B.
        # B always answers 1 about self and guesses 0 for A.
        # So each guessed the other perfectly → full marks both ways.
        self.client.force_authenticate(self.a)
        answers(self.client, self.pack, self_idx=0, guess_idx=1)
        self.client.force_authenticate(self.b)
        r = None
        for q in self.pack.questions.all():
            r = self.client.post(
                f"/api/v1/engagement/games/{self.pack.key}/answer",
                {"question_id": str(q.id), "self_answer": 1, "guess_answer": 0},
            )
        reveal = r.data["reveal"]
        self.assertEqual(reveal["out_of"], 3)
        self.assertEqual(reveal["my_score"], 3)      # B guessed A right 3x
        self.assertEqual(reveal["partner_score"], 3)  # A guessed B right 3x

    def test_mismatch_is_flagged_as_a_surprise(self):
        # "surprise" is from the caller's perspective: they guessed their
        # partner wrong. B guesses 2, but A actually answered 0 → 3 misses.
        self.client.force_authenticate(self.a)
        answers(self.client, self.pack, self_idx=0, guess_idx=1)
        self.client.force_authenticate(self.b)
        answers(self.client, self.pack, self_idx=1, guess_idx=2)
        r = self.client.get(f"/api/v1/engagement/games/{self.pack.key}")
        surprises = [q for q in r.data["reveal"]["questions"] if q["surprise"]]
        self.assertEqual(len(surprises), 3)

    def test_answer_is_upsert_not_duplicate(self):
        self.client.force_authenticate(self.a)
        q = self.pack.questions.first()
        url = f"/api/v1/engagement/games/{self.pack.key}/answer"
        self.client.post(url, {"question_id": str(q.id), "self_answer": 0, "guess_answer": 1})
        self.client.post(url, {"question_id": str(q.id), "self_answer": 2, "guess_answer": 0})
        plays = GamePlay.objects.filter(user=self.a, question=q)
        self.assertEqual(plays.count(), 1)
        self.assertEqual(plays.first().self_answer, 2)

    def test_completion_awards_points_and_notifies(self):
        self.client.force_authenticate(self.a)
        answers(self.client, self.pack, self_idx=0, guess_idx=1)
        # A earned game_completed points.
        self.assertTrue(PointsLedger.objects.filter(user=self.a, reason="game_completed").exists())
        # B is nudged to play.
        self.assertTrue(Notification.objects.filter(user_id=self.b.id, type="game_ready").exists())

    def test_invalid_option_index_rejected(self):
        self.client.force_authenticate(self.a)
        q = self.pack.questions.first()
        r = self.client.post(
            f"/api/v1/engagement/games/{self.pack.key}/answer",
            {"question_id": str(q.id), "self_answer": 9, "guess_answer": 0},
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_requires_a_partner(self):
        solo = User.objects.create_user(email="solo@e.com", password="pw")
        self.client.force_authenticate(solo)
        q = self.pack.questions.first()
        r = self.client.post(
            f"/api/v1/engagement/games/{self.pack.key}/answer",
            {"question_id": str(q.id), "self_answer": 0, "guess_answer": 0},
        )
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)


class SpicyGatingTests(APITestCase):
    def test_spicy_pack_hidden_from_non_age_verified(self):
        a, b, rel = make_couple(age_verified=False)
        make_pack(category="spicy")
        make_pack(category="relationship")
        self.client.force_authenticate(a)
        r = self.client.get("/api/v1/engagement/games")
        cats = {g["category"] for g in r.data["games"]}
        self.assertNotIn("spicy", cats)
        self.assertIn("relationship", cats)

    def test_spicy_pack_visible_to_age_verified(self):
        a, b, rel = make_couple(age_verified=True)
        make_pack(category="spicy")
        self.client.force_authenticate(a)
        r = self.client.get("/api/v1/engagement/games")
        cats = {g["category"] for g in r.data["games"]}
        self.assertIn("spicy", cats)

    def test_spicy_detail_404s_for_non_age_verified(self):
        a, b, rel = make_couple(age_verified=False)
        pack = make_pack(category="spicy")
        self.client.force_authenticate(a)
        r = self.client.get(f"/api/v1/engagement/games/{pack.key}")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)


class ConversationDeckTests(APITestCase):
    def test_unscored_deck_has_no_reveal(self):
        a, b, rel = make_couple()
        pack = make_pack(n=2, game_type="conversation_deck", category="relationship")
        self.client.force_authenticate(a)
        r = self.client.get(f"/api/v1/engagement/games/{pack.key}")
        self.assertFalse(r.data["is_scored"])
