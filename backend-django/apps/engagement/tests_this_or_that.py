"""Tests for the This-or-That game (agreement reveal)."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.engagement.models import GamePack, GameQuestion
from apps.relationships.models import Relationship

User = get_user_model()


def make_couple():
    a = User.objects.create_user(email="a@e.com", password="pw", full_name="Alex")
    b = User.objects.create_user(email="b@e.com", password="pw", full_name="Blake")
    rel = Relationship.objects.create(partner_a=a, partner_b=b, status="active")
    return a, b, rel


def make_tot_pack(n=3):
    pack = GamePack.objects.create(
        key="tot-test", title="This or That", game_type="this_or_that", category="fun",
    )
    for i in range(n):
        GameQuestion.objects.create(pack=pack, prompt=f"A or B #{i}?", options=["A", "B"], order=i)
    return pack


def answer_all(client, pack, choice):
    """Submit `choice` (an option index) as self_answer for every question."""
    for q in pack.questions.all():
        client.post(
            f"/api/v1/engagement/games/{pack.key}/answer",
            {"question_id": str(q.id), "self_answer": choice},
        )


class ThisOrThatTests(APITestCase):
    def setUp(self):
        self.a, self.b, self.rel = make_couple()
        self.pack = make_tot_pack(n=3)

    def test_no_guess_required(self):
        # This-or-That only needs self_answer; omitting guess is fine.
        self.client.force_authenticate(self.a)
        q = self.pack.questions.first()
        r = self.client.post(
            f"/api/v1/engagement/games/{self.pack.key}/answer",
            {"question_id": str(q.id), "self_answer": 0},
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_reveal_requires_both_and_uses_agreement_mode(self):
        self.client.force_authenticate(self.a)
        answer_all(self.client, self.pack, 0)  # A on all
        r = self.client.get(f"/api/v1/engagement/games/{self.pack.key}")
        self.assertNotIn("reveal", r.data)  # partner hasn't played

        self.client.force_authenticate(self.b)
        answer_all(self.client, self.pack, 0)  # B also picks A on all -> full agreement
        r = self.client.get(f"/api/v1/engagement/games/{self.pack.key}")
        reveal = r.data["reveal"]
        self.assertEqual(reveal["mode"], "agreement")
        self.assertEqual(reveal["agree_count"], 3)
        self.assertEqual(reveal["out_of"], 3)
        self.assertTrue(all(item["matched"] for item in reveal["questions"]))

    def test_partial_agreement_is_counted(self):
        self.client.force_authenticate(self.a)
        answer_all(self.client, self.pack, 0)  # A picks option 0 everywhere
        self.client.force_authenticate(self.b)
        # B picks 0 on the first, 1 on the rest -> 1 match of 3.
        questions = list(self.pack.questions.all())
        self.client.post(
            f"/api/v1/engagement/games/{self.pack.key}/answer",
            {"question_id": str(questions[0].id), "self_answer": 0},
        )
        for q in questions[1:]:
            self.client.post(
                f"/api/v1/engagement/games/{self.pack.key}/answer",
                {"question_id": str(q.id), "self_answer": 1},
            )
        r = self.client.get(f"/api/v1/engagement/games/{self.pack.key}")
        self.assertEqual(r.data["reveal"]["agree_count"], 1)

    def test_reveal_answer_on_completion(self):
        # The completing partner gets the reveal inline in the answer response.
        self.client.force_authenticate(self.a)
        answer_all(self.client, self.pack, 1)
        self.client.force_authenticate(self.b)
        questions = list(self.pack.questions.all())
        for q in questions[:-1]:
            self.client.post(
                f"/api/v1/engagement/games/{self.pack.key}/answer",
                {"question_id": str(q.id), "self_answer": 1},
            )
        r = self.client.post(
            f"/api/v1/engagement/games/{self.pack.key}/answer",
            {"question_id": str(questions[-1].id), "self_answer": 1},
        )
        self.assertTrue(r.data["just_completed"])
        self.assertEqual(r.data["reveal"]["mode"], "agreement")
        self.assertEqual(r.data["reveal"]["agree_count"], 3)


class SeededThisOrThatTests(APITestCase):
    def test_seeded_pack_is_listed_and_playable(self):
        a, b, rel = make_couple()
        self.client.force_authenticate(a)
        r = self.client.get("/api/v1/engagement/games")
        keys = {g["key"] for g in r.data["games"]}
        self.assertIn("tot-us", keys)
        detail = self.client.get("/api/v1/engagement/games/tot-us")
        self.assertEqual(detail.data["game_type"], "this_or_that")
        self.assertGreaterEqual(len(detail.data["questions"]), 10)
