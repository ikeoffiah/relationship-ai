"""The outcome loop.

The property worth holding: a couple who keep dismissing a kind of help stop
being offered it, and a couple who have said nothing keep today's behaviour
exactly.
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.chat.models import AssistNudge
from apps.personalization import outcomes
from apps.personalization.models import CouplePolicy
from apps.relationships.models import Relationship

User = get_user_model()


class BucketTests(TestCase):
    def test_the_hour_becomes_a_window(self):
        self.assertEqual(outcomes.bucket("nudge_night", {"hour": 23}), "nudge_night@night")
        self.assertEqual(outcomes.bucket("nudge_night", {"hour": 9}), "nudge_night@morning")
        self.assertEqual(outcomes.bucket("nudge_night", {"hour": 14}), "nudge_night@afternoon")
        self.assertEqual(outcomes.bucket("nudge_night", {"hour": 20}), "nudge_night@evening")

    def test_no_hour_means_the_kind_alone(self):
        self.assertEqual(outcomes.bucket("rephrase", None), "rephrase")
        self.assertEqual(outcomes.bucket("rephrase", {}), "rephrase")

    def test_windows_are_coarse_on_purpose(self):
        # 23:04 on a Tuesday is a coincidence with a long name. Every extra
        # dimension divides evidence there is not much of.
        self.assertEqual(
            outcomes.bucket("nudge_night", {"hour": 23}),
            outcomes.bucket("nudge_night", {"hour": 2}),
        )


class PolicyTests(TestCase):
    def setUp(self):
        self.alex = User.objects.create_user(email="a@test.local", password="pw12345!")
        self.sam = User.objects.create_user(email="s@test.local", password="pw12345!")
        self.relationship = Relationship.objects.create(
            partner_a=self.alex, partner_b=self.sam, status="active"
        )

    def decline(self, times, kind="nudge_night", hour=23):
        for _ in range(times):
            outcomes.record(self.relationship, kind, {"hour": hour}, "declined")

    def test_a_couple_who_have_said_nothing_get_the_defaults(self):
        self.assertEqual(outcomes.score_for(self.relationship.id, "nudge_night"), 0.0)
        self.assertFalse(outcomes.suppressed(self.relationship.id, "nudge_night"))

    def test_one_dismissal_is_not_a_pattern(self):
        self.decline(1)

        # Below the evidence threshold, so it still reads as unknown.
        self.assertEqual(
            outcomes.score_for(self.relationship.id, "nudge_night", {"hour": 23}), 0.0
        )
        self.assertFalse(
            outcomes.suppressed(self.relationship.id, "nudge_night", {"hour": 23})
        )

    def test_repeated_dismissals_suppress_it(self):
        self.decline(4)

        self.assertTrue(
            outcomes.suppressed(self.relationship.id, "nudge_night", {"hour": 23})
        )

    def test_suppression_is_scoped_to_the_window(self):
        self.decline(6, hour=23)

        # They do not want it at night. That says nothing about the morning.
        self.assertTrue(
            outcomes.suppressed(self.relationship.id, "nudge_night", {"hour": 23})
        )
        self.assertFalse(
            outcomes.suppressed(self.relationship.id, "nudge_night", {"hour": 9})
        )

    def test_suppression_is_scoped_to_the_kind(self):
        self.decline(6, kind="nudge_night")

        self.assertFalse(
            outcomes.suppressed(self.relationship.id, "nudge_repair", {"hour": 23})
        )

    def test_acceptances_pull_it_back(self):
        self.decline(4)
        self.assertTrue(
            outcomes.suppressed(self.relationship.id, "nudge_night", {"hour": 23})
        )

        for _ in range(6):
            outcomes.record(self.relationship, "nudge_night", {"hour": 23}, "accepted")

        self.assertFalse(
            outcomes.suppressed(self.relationship.id, "nudge_night", {"hour": 23})
        )

    def test_a_dismissal_costs_more_than_an_acceptance_gains(self):
        # An unwanted nudge teaches someone to ignore the assist; a wanted one
        # is merely useful. The asymmetry is the point.
        self.assertGreater(abs(outcomes.WEIGHTS["declined"]), outcomes.WEIGHTS["accepted"])

    def test_it_decays_so_a_hard_fortnight_does_not_define_them(self):
        self.decline(6)
        policy = CouplePolicy.objects.get(relationship=self.relationship)
        stale = timezone.now() - timedelta(days=90)
        policy.weights["nudge_night@night"]["updated_at"] = stale.isoformat()
        policy.save()

        self.assertFalse(
            outcomes.suppressed(self.relationship.id, "nudge_night", {"hour": 23})
        )

    def test_an_unknown_response_is_ignored(self):
        outcomes.record(self.relationship, "nudge_night", {"hour": 23}, "shrugged")

        self.assertFalse(CouplePolicy.objects.filter(relationship=self.relationship).exists())

    def test_recording_never_raises(self):
        with patch(
            "apps.personalization.models.CouplePolicy.objects.get_or_create",
            side_effect=RuntimeError("db down"),
        ):
            # Bookkeeping about help already given must not break anything.
            outcomes.record(self.relationship, "nudge_night", {"hour": 23}, "declined")

    def test_scoring_never_raises(self):
        with patch(
            "apps.personalization.models.CouplePolicy.objects.filter",
            side_effect=RuntimeError("db down"),
        ):
            self.assertEqual(outcomes.score_for(self.relationship.id, "nudge_night"), 0.0)

    def test_nothing_here_makes_the_system_more_insistent(self):
        for _ in range(20):
            outcomes.record(self.relationship, "nudge_night", {"hour": 23}, "accepted")

        # A high score means "keep offering it", never "offer it harder". There
        # is no path in this module that increases frequency.
        self.assertFalse(
            outcomes.suppressed(self.relationship.id, "nudge_night", {"hour": 23})
        )


class LoopIntegrationTests(TestCase):
    """Feedback goes in one end and changes what comes out of the other."""

    def setUp(self):
        self.alex = User.objects.create_user(email="a@test.local", password="pw12345!")
        self.sam = User.objects.create_user(email="s@test.local", password="pw12345!")
        self.relationship = Relationship.objects.create(
            partner_a=self.alex, partner_b=self.sam, status="active"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.alex)

    def dismiss_a_nudge(self, kind=AssistNudge.KIND_NIGHT):
        nudge = AssistNudge.objects.create(
            relationship=self.relationship,
            user=self.alex,
            kind=kind,
            suggestion="say goodnight",
        )
        AssistNudge.objects.filter(id=nudge.id).update(
            created_at=timezone.now().replace(hour=23, minute=0)
        )
        return self.client.post(
            reverse("chat-assist-feedback", args=[nudge.id]),
            {"action": "dismissed"},
            format="json",
        )

    def test_dismissing_writes_the_lesson(self):
        response = self.dismiss_a_nudge()

        self.assertEqual(response.status_code, 200)
        policy = CouplePolicy.objects.get(relationship=self.relationship)
        self.assertTrue(policy.weights)

    def test_four_dismissals_stop_the_nudge_being_offered(self):
        for _ in range(4):
            self.dismiss_a_nudge()

        offered = AssistNudge(
            relationship=self.relationship,
            user=self.alex,
            kind=AssistNudge.KIND_NIGHT,
            suggestion="say goodnight",
        )
        from apps.chat import assist

        with patch("apps.chat.assist._nudge_for", return_value=offered):
            result = assist.nudge_for(self.relationship, self.alex, local_hour=23)

        # They have told us four times. Asking again is how the assist becomes
        # something people swipe past without reading.
        self.assertIsNone(result)

    def test_a_couple_who_have_not_dismissed_still_get_it(self):
        offered = AssistNudge(
            relationship=self.relationship,
            user=self.alex,
            kind=AssistNudge.KIND_NIGHT,
            suggestion="say goodnight",
        )
        from apps.chat import assist

        with patch("apps.chat.assist._nudge_for", return_value=offered):
            result = assist.nudge_for(self.relationship, self.alex, local_hour=23)

        self.assertIs(result, offered)

    def test_acting_on_one_is_recorded_as_acceptance(self):
        nudge = AssistNudge.objects.create(
            relationship=self.relationship,
            user=self.alex,
            kind=AssistNudge.KIND_REPAIR,
            suggestion="reach out",
        )
        self.client.post(
            reverse("chat-assist-feedback", args=[nudge.id]),
            {"action": "acted"},
            format="json",
        )

        policy = CouplePolicy.objects.get(relationship=self.relationship)
        entry = next(iter(policy.weights.values()))
        self.assertGreater(entry["score"], 0)

    def test_a_policy_failure_does_not_break_the_feedback_endpoint(self):
        nudge = AssistNudge.objects.create(
            relationship=self.relationship,
            user=self.alex,
            kind=AssistNudge.KIND_NIGHT,
            suggestion="say goodnight",
        )

        with patch(
            "apps.personalization.outcomes.record", side_effect=RuntimeError("boom")
        ):
            with self.assertRaises(RuntimeError):
                # Documented rather than swallowed: `record` itself is the thing
                # that must never raise, and it is tested above. If it somehow
                # does, we would rather know than silently lose the signal.
                self.client.post(
                    reverse("chat-assist-feedback", args=[nudge.id]),
                    {"action": "dismissed"},
                    format="json",
                )
