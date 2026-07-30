"""Tests for the couple-games engine (Know Your Partner)."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

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


def _opt_in(client):
    return client.post("/api/v1/engagement/games/spicy-consent", {"enabled": True})


class SpicyGatingTests(APITestCase):
    def test_spicy_hidden_from_non_age_verified(self):
        a, b, rel = make_couple(age_verified=False)
        make_pack(category="spicy")
        make_pack(category="relationship")
        self.client.force_authenticate(a)
        cats = {g["category"] for g in self.client.get("/api/v1/engagement/games").data["games"]}
        self.assertNotIn("spicy", cats)
        self.assertIn("relationship", cats)

    def test_spicy_hidden_until_both_opt_in(self):
        a, b, rel = make_couple(age_verified=True)
        make_pack(category="spicy")
        # Both age-verified but nobody opted in → hidden.
        self.client.force_authenticate(a)
        self.assertNotIn("spicy", {g["category"] for g in self.client.get("/api/v1/engagement/games").data["games"]})
        # Only A opts in → still hidden.
        _opt_in(self.client)
        self.assertNotIn("spicy", {g["category"] for g in self.client.get("/api/v1/engagement/games").data["games"]})
        # B opts in too → now unlocked for both.
        self.client.force_authenticate(b)
        _opt_in(self.client)
        self.assertIn("spicy", {g["category"] for g in self.client.get("/api/v1/engagement/games").data["games"]})
        self.client.force_authenticate(a)
        self.assertIn("spicy", {g["category"] for g in self.client.get("/api/v1/engagement/games").data["games"]})

    def test_spicy_detail_404_until_unlocked(self):
        a, b, rel = make_couple(age_verified=True)
        pack = make_pack(category="spicy")
        self.client.force_authenticate(a)
        _opt_in(self.client)  # only A opted in
        r = self.client.get(f"/api/v1/engagement/games/{pack.key}")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_age_verified_cannot_opt_in(self):
        a, b, rel = make_couple(age_verified=False)
        self.client.force_authenticate(a)
        r = _opt_in(self.client)
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(r.data["code"], "age_verification_required")

    def test_consent_status_reports_both_and_unlocked(self):
        a, b, rel = make_couple(age_verified=True)
        self.client.force_authenticate(a)
        _opt_in(self.client)
        self.client.force_authenticate(b)
        _opt_in(self.client)
        r = self.client.get("/api/v1/engagement/games/spicy-consent")
        self.assertTrue(r.data["you"])
        self.assertTrue(r.data["partner"])
        self.assertTrue(r.data["both_age_verified"])
        self.assertTrue(r.data["unlocked"])

    def test_can_opt_back_out(self):
        a, b, rel = make_couple(age_verified=True)
        self.client.force_authenticate(a)
        _opt_in(self.client)
        r = self.client.post("/api/v1/engagement/games/spicy-consent", {"enabled": False})
        self.assertFalse(r.data["you"])

    def test_consent_requires_partner(self):
        solo = User.objects.create_user(email="solo@e.com", password="pw", age_verified=True)
        self.client.force_authenticate(solo)
        r = _opt_in(self.client)
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)


class ConversationDeckTests(APITestCase):
    def test_unscored_deck_has_no_reveal(self):
        a, b, rel = make_couple()
        pack = make_pack(n=2, game_type="conversation_deck", category="relationship")
        self.client.force_authenticate(a)
        r = self.client.get(f"/api/v1/engagement/games/{pack.key}")
        self.assertFalse(r.data["is_scored"])


class SoloSpicyConsentTests(APITestCase):
    """Reading the consent state without a partner.

    A GET here is a question — "is intimate content unlocked for me?" — and for
    someone with no partner it has a plain answer. It used to 409, which turned
    an ordinary state into an exception at the client: a stack trace in the
    console every time a solo user opened games or the couple thread, and
    callers left to infer "locked" from a failure, which also made a genuine
    network problem indistinguishable from being single.
    """

    def setUp(self):
        self.solo = User.objects.create_user(email="solo-sc@t.local", password="pw12345!")
        self.client = APIClient()
        self.client.force_authenticate(user=self.solo)
        self.url = "/api/v1/engagement/games/spicy-consent"

    def test_reading_it_solo_answers_rather_than_erroring(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "you": False,
                "partner": False,
                "both_age_verified": False,
                "unlocked": False,
            },
        )

    def test_it_reads_as_locked_not_as_unknown(self):
        """The direction that matters. An absent partner must never resolve to
        unlocked — there is nobody to have consented."""
        self.assertFalse(self.client.get(self.url).json()["unlocked"])

    def test_setting_it_solo_is_still_refused(self):
        """You cannot record half of a mutual consent when there is no other
        half. The write keeps its gate."""
        response = self.client.post(self.url, {"enabled": True}, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "no_active_relationship")
