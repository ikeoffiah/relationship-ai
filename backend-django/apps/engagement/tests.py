"""
Tests for the daily-engagement API.

Covers the behaviours that make the features work as designed: the two-sided
reveal, once-per-day guards, points/streak accrual, the gratitude→repair mirror
into shared context, and the relationship-scoping that keeps one couple out of
another's data.
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.engagement import services
from apps.engagement.models import (
    DailyQuestion,
    EngagementStreak,
    GratitudeMoment,
    MicroActionTemplate,
    PointsLedger,
    SharedGoal,
    today_key,
)
from apps.notifications.notification_models import Notification
from apps.relationships.models import Relationship, SharedRelationshipContext

User = get_user_model()


def make_couple():
    a = User.objects.create_user(email="a@example.com", password="pw", full_name="Alex")
    b = User.objects.create_user(email="b@example.com", password="pw", full_name="Blake")
    rel = Relationship.objects.create(partner_a=a, partner_b=b, status="active")
    return a, b, rel


class SoloModeTests(APITestCase):
    """A user with no partner gets full daily value — the invite is an upgrade,
    not a gate."""

    def setUp(self):
        self.solo = User.objects.create_user(email="solo@example.com", password="pw", full_name="Sam")
        DailyQuestion.objects.create(prompt_text="What went well today?")
        self.client.force_authenticate(self.solo)

    def test_solo_check_in_awards_points_and_streak(self):
        r = self.client.post("/api/v1/engagement/check-in", {"connection_score": 4})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["points_awarded"], services.POINTS["check_in"])
        self.assertEqual(r.data["current_streak"], 1)

    def test_solo_check_in_history_and_once_per_day(self):
        self.client.post("/api/v1/engagement/check-in", {"connection_score": 3})
        again = self.client.post("/api/v1/engagement/check-in", {"connection_score": 5})
        self.assertEqual(again.status_code, status.HTTP_409_CONFLICT)
        hist = self.client.get("/api/v1/engagement/check-in/history")
        self.assertEqual(len(hist.data["check_ins"]), 1)

    def test_solo_can_create_and_progress_a_goal(self):
        created = self.client.post(
            "/api/v1/engagement/goals",
            {"title": "Read 12 books", "category": "learning", "target_value": 12, "unit": "books"},
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        goal_id = created.data["id"]
        # The solo goal is listed for its owner…
        listed = self.client.get("/api/v1/engagement/goals")
        self.assertEqual(len(listed.data["goals"]), 1)
        # …and progress logs succeed and award points.
        prog = self.client.post(f"/api/v1/engagement/goals/{goal_id}/progress", {"value": 3})
        self.assertEqual(prog.data["goal"]["current_value"], 3)
        self.assertEqual(prog.data["points_awarded"], services.POINTS["goal_progress"])

    def test_one_solo_goal_is_hidden_from_another_solo_user(self):
        created = self.client.post(
            "/api/v1/engagement/goals", {"title": "Private", "category": "custom"}
        )
        other = User.objects.create_user(email="other@example.com", password="pw")
        self.client.force_authenticate(other)
        listed = self.client.get("/api/v1/engagement/goals")
        self.assertEqual(len(listed.data["goals"]), 0)
        blocked = self.client.post(
            f"/api/v1/engagement/goals/{created.data['id']}/progress", {"value": 1}
        )
        self.assertEqual(blocked.status_code, status.HTTP_404_NOT_FOUND)

    def test_solo_gratitude_does_not_touch_shared_context(self):
        r = self.client.post(
            "/api/v1/engagement/gratitude", {"kind": "repair", "text": "made peace with myself"}
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SharedRelationshipContext.objects.count(), 0)

    def test_solo_summary_has_no_partner(self):
        self.client.post("/api/v1/engagement/check-in", {"connection_score": 4})
        r = self.client.get("/api/v1/engagement/summary")
        self.assertFalse(r.data["has_partner"])
        self.assertTrue(r.data["today"]["check_in"])
        self.assertEqual(r.data["current_streak"], 1)


class DailyQuestionTests(APITestCase):
    def setUp(self):
        self.a, self.b, self.rel = make_couple()
        self.q = DailyQuestion.objects.create(prompt_text="What made you smile today?")

    def test_reveal_requires_both_answers(self):
        # A answers first — nothing revealed yet.
        self.client.force_authenticate(self.a)
        r = self.client.post("/api/v1/engagement/daily-question/answer", {"response_text": "The dog."})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertFalse(r.data["revealed"])

        # A viewing before B answers cannot see anything but their own answer.
        r = self.client.get("/api/v1/engagement/daily-question")
        self.assertTrue(r.data["i_answered"])
        self.assertFalse(r.data["partner_answered"])
        self.assertFalse(r.data["revealed"])
        self.assertIsNone(r.data["partner_answer"])

        # B answers — now the reveal flips for both.
        self.client.force_authenticate(self.b)
        r = self.client.post("/api/v1/engagement/daily-question/answer", {"response_text": "Coffee."})
        self.assertTrue(r.data["revealed"])

        r = self.client.get("/api/v1/engagement/daily-question")
        self.assertTrue(r.data["revealed"])
        self.assertEqual(r.data["partner_answer"], "The dog.")

    def test_second_answer_notifies_first_partner(self):
        self.client.force_authenticate(self.a)
        self.client.post("/api/v1/engagement/daily-question/answer", {"response_text": "x"})
        self.client.force_authenticate(self.b)
        self.client.post("/api/v1/engagement/daily-question/answer", {"response_text": "y"})
        # The first answerer (A) is told the answers are ready.
        self.assertTrue(
            Notification.objects.filter(user_id=self.a.id, type="daily_question_ready").exists()
        )

    def test_cannot_answer_twice_in_a_day(self):
        self.client.force_authenticate(self.a)
        self.client.post("/api/v1/engagement/daily-question/answer", {"response_text": "first"})
        r = self.client.post("/api/v1/engagement/daily-question/answer", {"response_text": "second"})
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)

    def test_solo_user_can_answer_as_reflection(self):
        # A user with no partner can still answer (private reflection); nothing
        # is revealed, and the answer is visible to them on the next GET.
        solo = User.objects.create_user(email="solo@example.com", password="pw")
        self.client.force_authenticate(solo)
        r = self.client.post("/api/v1/engagement/daily-question/answer", {"response_text": "just me"})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertFalse(r.data["revealed"])

        r = self.client.get("/api/v1/engagement/daily-question")
        self.assertFalse(r.data["has_partner"])
        self.assertTrue(r.data["i_answered"])
        self.assertFalse(r.data["revealed"])
        self.assertEqual(r.data["my_answer"], "just me")

    def test_response_is_encrypted_at_rest(self):
        self.client.force_authenticate(self.a)
        self.client.post("/api/v1/engagement/daily-question/answer", {"response_text": "secret words"})
        from apps.engagement.models import DailyQuestionResponse

        row = DailyQuestionResponse.objects.get(user=self.a)
        self.assertTrue(row.response_text.startswith("ENC:"))
        self.assertEqual(row.decrypted_response, "secret words")

    def test_requires_auth(self):
        # Auth is enforced by JWT middleware, which rejects anonymous callers
        # with 403 (no DRF WWW-Authenticate challenge is issued).
        r = self.client.get("/api/v1/engagement/daily-question")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)


class CheckInTests(APITestCase):
    def setUp(self):
        self.a, self.b, self.rel = make_couple()
        self.client.force_authenticate(self.a)

    def test_check_in_awards_points_and_streak(self):
        r = self.client.post("/api/v1/engagement/check-in", {"connection_score": 4, "mood": "good"})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["points_awarded"], services.POINTS["check_in"])
        self.assertEqual(r.data["current_streak"], 1)

    def test_score_out_of_range_rejected(self):
        r = self.client.post("/api/v1/engagement/check-in", {"connection_score": 9})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_one_check_in_per_day(self):
        self.client.post("/api/v1/engagement/check-in", {"connection_score": 3})
        r = self.client.post("/api/v1/engagement/check-in", {"connection_score": 5})
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)

    def test_history_returns_only_own_check_ins(self):
        self.client.post("/api/v1/engagement/check-in", {"connection_score": 3})
        self.client.force_authenticate(self.b)
        self.client.post("/api/v1/engagement/check-in", {"connection_score": 5})
        r = self.client.get("/api/v1/engagement/check-in/history")
        self.assertEqual(len(r.data["check_ins"]), 1)
        self.assertEqual(r.data["check_ins"][0]["connection_score"], 5)


class SharedGoalTests(APITestCase):
    def setUp(self):
        self.a, self.b, self.rel = make_couple()
        self.client.force_authenticate(self.a)

    def test_create_and_list_goal(self):
        r = self.client.post(
            "/api/v1/engagement/goals",
            {"title": "Save for Japan", "category": "financial", "target_value": 5000, "unit": "USD"},
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        r = self.client.get("/api/v1/engagement/goals")
        self.assertEqual(len(r.data["goals"]), 1)
        self.assertEqual(r.data["goals"][0]["title"], "Save for Japan")

    def test_progress_accumulates_and_completes(self):
        goal = SharedGoal.objects.create(
            relationship=self.rel, created_by=self.a, title="Run 100mi",
            category="health", target_value=100, unit="miles",
        )
        r = self.client.post(f"/api/v1/engagement/goals/{goal.id}/progress", {"value": 60})
        self.assertEqual(r.data["goal"]["current_value"], 60)
        self.assertEqual(r.data["goal"]["status"], "active")
        r = self.client.post(f"/api/v1/engagement/goals/{goal.id}/progress", {"value": 45})
        self.assertEqual(r.data["goal"]["status"], "completed")

    def test_partner_notified_on_progress(self):
        goal = SharedGoal.objects.create(
            relationship=self.rel, created_by=self.a, title="Cook weekly", category="home"
        )
        self.client.post(f"/api/v1/engagement/goals/{goal.id}/progress", {"value": 1})
        self.assertTrue(Notification.objects.filter(user_id=self.b.id, type="goal_progress").exists())

    def test_cannot_touch_another_couples_goal(self):
        c = User.objects.create_user(email="c@example.com", password="pw")
        d = User.objects.create_user(email="d@example.com", password="pw")
        other = Relationship.objects.create(partner_a=c, partner_b=d, status="active")
        their_goal = SharedGoal.objects.create(
            relationship=other, created_by=c, title="Private", category="custom"
        )
        r = self.client.post(f"/api/v1/engagement/goals/{their_goal.id}/progress", {"value": 1})
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)


class GratitudeTests(APITestCase):
    def setUp(self):
        self.a, self.b, self.rel = make_couple()
        self.client.force_authenticate(self.a)

    def test_gratitude_encrypted_and_awards_points(self):
        r = self.client.post("/api/v1/engagement/gratitude", {"kind": "gratitude", "text": "thank you"})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["points_awarded"], services.POINTS["gratitude"])
        row = GratitudeMoment.objects.get(user=self.a)
        self.assertTrue(row.text.startswith("ENC:"))

    def test_repair_mirrors_into_shared_context(self):
        r = self.client.post(
            "/api/v1/engagement/gratitude", {"kind": "repair", "text": "we made up after the argument"}
        )
        self.assertEqual(r.data["points_awarded"], services.POINTS["repair"])
        ctx = SharedRelationshipContext.objects.get(relationship=self.rel)
        self.assertEqual(len(ctx.repair_history), 1)
        self.assertEqual(ctx.repair_history[0]["by"], str(self.a.id))
        # Only a short preview is mirrored, and it is not the ciphertext.
        self.assertIn("we made up", ctx.repair_history[0]["note_preview"])


class MicroActionTests(APITestCase):
    def setUp(self):
        self.a, self.b, self.rel = make_couple()
        MicroActionTemplate.objects.create(text="Send a thinking-of-you text")
        self.client.force_authenticate(self.a)

    def test_get_and_complete(self):
        r = self.client.get("/api/v1/engagement/micro-action")
        self.assertIsNotNone(r.data["action"])
        self.assertFalse(r.data["completed"])
        r = self.client.post("/api/v1/engagement/micro-action/complete")
        self.assertTrue(r.data["completed"])
        self.assertEqual(r.data["points_awarded"], services.POINTS["micro_action"])
        # Idempotent within the day.
        r = self.client.post("/api/v1/engagement/micro-action/complete")
        self.assertTrue(r.data["completed"])
        self.assertEqual(PointsLedger.objects.filter(user=self.a, reason="micro_action").count(), 1)


class StreakServiceTests(APITestCase):
    def setUp(self):
        self.a, self.b, self.rel = make_couple()

    def test_consecutive_days_increment_then_reset(self):
        d0 = date(2026, 7, 1)
        services.touch_streak(self.a, day_key=d0.isoformat())
        services.touch_streak(self.a, day_key=(d0 + timedelta(days=1)).isoformat())
        s = EngagementStreak.objects.get(user=self.a)
        self.assertEqual(s.current_streak, 2)
        self.assertEqual(s.longest_streak, 2)

        # Skip a day → streak resets to 1 but longest is remembered.
        services.touch_streak(self.a, day_key=(d0 + timedelta(days=3)).isoformat())
        s.refresh_from_db()
        self.assertEqual(s.current_streak, 1)
        self.assertEqual(s.longest_streak, 2)

    def test_same_day_is_idempotent(self):
        d = today_key()
        services.touch_streak(self.a, day_key=d)
        services.touch_streak(self.a, day_key=d)
        s = EngagementStreak.objects.get(user=self.a)
        self.assertEqual(s.current_streak, 1)

    def test_each_partner_keeps_their_own_streak(self):
        d = today_key()
        services.touch_streak(self.a, day_key=d)
        self.assertEqual(EngagementStreak.objects.get(user=self.a).current_streak, 1)
        # B has done nothing → no streak row yet.
        self.assertFalse(EngagementStreak.objects.filter(user=self.b).exists())


class SummaryTests(APITestCase):
    def setUp(self):
        self.a, self.b, self.rel = make_couple()
        DailyQuestion.objects.create(prompt_text="Q?")
        self.client.force_authenticate(self.a)

    def test_summary_reflects_todays_activity(self):
        self.client.post("/api/v1/engagement/check-in", {"connection_score": 4})
        self.client.post("/api/v1/engagement/daily-question/answer", {"response_text": "hi"})
        r = self.client.get("/api/v1/engagement/summary")
        self.assertTrue(r.data["today"]["check_in"])
        self.assertTrue(r.data["today"]["daily_question"])
        self.assertGreater(r.data["points_balance"], 0)
        self.assertEqual(r.data["current_streak"], 1)


from django.test import TestCase as DjangoTestCase  # noqa: E402


class RollingConsistencyTests(DjangoTestCase):
    """Consistency over a window, not a chain that resets.

    The property that matters: a missed day must not undo the days that came
    before it. That is the whole point of the change.
    """

    def setUp(self):
        from django.contrib.auth import get_user_model

        self.user = get_user_model().objects.create_user(
            email="rolling@test.local", password="pw12345!"
        )

    def _active_on(self, days_ago):
        from datetime import timedelta

        from django.utils import timezone

        from apps.engagement.models import PointsLedger

        day = (timezone.now() - timedelta(days=days_ago)).date().isoformat()
        PointsLedger.objects.create(
            user=self.user, points=5, reason="check_in", date_key=day
        )

    def test_counts_distinct_days_not_actions(self):
        from apps.engagement import services

        # Three actions on one day is still one day.
        for _ in range(3):
            self._active_on(0)

        self.assertEqual(services.days_active_in_window(self.user), 1)

    def test_a_gap_does_not_reset_the_count(self):
        """The behaviour a streak gets wrong."""
        from apps.engagement import services

        self._active_on(5)
        self._active_on(4)
        # day 3 missed — someone was ill, travelling, having a bad week
        self._active_on(2)
        self._active_on(1)

        # A consecutive streak would read 2 here. This reads 4, because the
        # earlier days genuinely happened.
        self.assertEqual(services.days_active_in_window(self.user), 4)

    def test_days_outside_the_window_drop_off(self):
        from apps.engagement import services

        self._active_on(45)
        self._active_on(2)

        self.assertEqual(services.days_active_in_window(self.user), 1)

    def test_no_activity_is_zero_not_an_error(self):
        from apps.engagement import services

        self.assertEqual(services.days_active_in_window(self.user), 0)

    def test_one_user_never_counts_anothers_days(self):
        from django.contrib.auth import get_user_model

        from apps.engagement import services

        other = get_user_model().objects.create_user(
            email="other@test.local", password="pw12345!"
        )
        self._active_on(1)

        self.assertEqual(services.days_active_in_window(other), 0)
