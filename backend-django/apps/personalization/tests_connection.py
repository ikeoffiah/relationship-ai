"""The connection score.

The property that matters most is the first group: the number is built from
behaviour both partners witnessed, and cannot be run backwards into either
person's private check-in. Everything else is about it being a number people
can live with on a home screen.
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.chat.models import CoupleMessage
from apps.engagement.models import (
    GratitudeMoment,
    MicroActionLog,
    MicroActionTemplate,
    RelationshipCheckIn,
)
from apps.personalization import behaviour, connection
from apps.personalization.models import ConnectionScore
from apps.relationships.models import Relationship

User = get_user_model()


class ConnectionTestCase(TestCase):
    def setUp(self):
        self.alex = User.objects.create_user(email="a@test.local", password="pw12345!")
        self.sam = User.objects.create_user(email="s@test.local", password="pw12345!")
        self.relationship = Relationship.objects.create(
            partner_a=self.alex, partner_b=self.sam, status="active"
        )

    def message(self, sender, n=1):
        for i in range(n):
            m = CoupleMessage(relationship=self.relationship, sender=sender)
            m.body = f"hello {i}"
            m.save()

    def check_in(self, user, days_ago=0, score=3):
        day = timezone.now() - timedelta(days=days_ago)
        # One per user per day is a database constraint; get_or_create keeps
        # the helper usable from tests that overlap windows.
        row, _ = RelationshipCheckIn.objects.get_or_create(
            user=user,
            date_key=day.strftime("%Y-%m-%d"),
            defaults={
                "relationship": self.relationship,
                "connection_score": score,
            },
        )
        return row

    def action(self, completed, n=1, offset=0):
        template, _ = MicroActionTemplate.objects.get_or_create(
            text="say something kind", defaults={}
        )
        for i in range(n):
            MicroActionLog.objects.create(
                relationship=self.relationship,
                user=self.alex,
                template=template,
                date_key=f"2026-07-{i + offset + 1:02d}",
                completed=completed,
            )

    def gratitude(self, user, n=1):
        for i in range(n):
            GratitudeMoment.objects.create(
                relationship=self.relationship, user=user, text=f"thank you {i}"
            )

    def busy_but_one_sided(self):
        self.message(self.alex, 30)
        self.check_in(self.alex)
        self.gratitude(self.alex, 5)

    def mutual(self):
        self.message(self.alex, 15)
        self.message(self.sam, 15)
        for i in range(5):
            self.check_in(self.alex, days_ago=i)
            self.check_in(self.sam, days_ago=i)
        self.gratitude(self.alex, 3)
        self.gratitude(self.sam, 3)


class PrivacyTests(ConnectionTestCase):
    """The number must not be reversible into anyone's private answer."""

    def test_the_check_in_value_does_not_move_the_score(self):
        self.mutual()
        RelationshipCheckIn.objects.all().delete()
        for i in range(5):
            self.check_in(self.alex, days_ago=i, score=1)
            self.check_in(self.sam, days_ago=i, score=1)
        miserable = connection.compute(self.relationship)

        RelationshipCheckIn.objects.all().update(connection_score=5)
        delighted = connection.compute(self.relationship)

        # Identical behaviour, opposite private feelings, same number. If these
        # ever diverge, the score has become a way to read your partner's
        # answer by subtracting your own.
        self.assertEqual(miserable, delighted)

    def test_no_component_reads_a_private_note(self):
        self.mutual()
        RelationshipCheckIn.objects.all().update(note="ENC:something private")

        # Nothing raises, nothing changes: the note is not an input.
        self.assertIsNotNone(connection.compute(self.relationship))


class ComponentTests(ConnectionTestCase):
    def test_one_partner_doing_everything_does_not_score_well(self):
        self.busy_but_one_sided()
        one_sided = connection.compute(self.relationship)

        self.mutual()
        both = connection.compute(self.relationship)

        # The imbalance is the finding, not something to paper over with a high
        # number for the partner who is working hard.
        self.assertLess(one_sided, both)

    def test_reciprocity_carries_the_most_weight(self):
        self.assertEqual(
            max(connection.WEIGHTS, key=connection.WEIGHTS.get), "mutuality"
        )

    def test_repair_counts_for_more_than_activity(self):
        # Gottman's strongest single predictor is not whether couples fight.
        self.assertGreater(connection.WEIGHTS["repair"], connection.WEIGHTS["effort"])

    def test_an_uncompleted_action_is_not_effort(self):
        self.mutual()
        before = connection.compute(self.relationship)
        self.action(completed=False, n=7)

        # Being assigned something is not doing it.
        self.assertEqual(connection.compute(self.relationship), before)

    def test_completing_actions_raises_it(self):
        self.mutual()
        before = connection.compute(self.relationship)
        self.action(completed=True, n=7)

        self.assertGreater(connection.compute(self.relationship), before)

    def test_repair_lifts_it(self):
        self.mutual()
        before = connection.compute(self.relationship)
        for _ in range(behaviour.MIN_OBSERVATIONS + 2):
            behaviour.observe(self.alex, behaviour.REPAIRS)

        self.assertGreater(connection.compute(self.relationship), before)

    def test_old_activity_falls_out_of_the_window(self):
        self.mutual()
        stale = timezone.now() - timedelta(days=connection.WINDOW_DAYS + 5)
        CoupleMessage.objects.all().update(created_at=stale)
        GratitudeMoment.objects.all().update(created_at=stale)
        RelationshipCheckIn.objects.all().update(created_at=stale)

        # A good fortnight in March is not this fortnight.
        self.assertIsNone(connection.compute(self.relationship))

    def test_a_compute_failure_says_nothing_rather_than_zero(self):
        self.mutual()
        with patch(
            "apps.personalization.connection._components",
            side_effect=RuntimeError("boom"),
        ):
            self.assertIsNone(connection.compute(self.relationship))


class ColdStartTests(ConnectionTestCase):
    def test_a_new_couple_has_no_score(self):
        # Not 0, not 18/100 — nothing. They joined on Tuesday.
        self.assertIsNone(connection.compute(self.relationship))
        self.assertIsNone(connection.update(self.relationship))

    def test_a_little_activity_is_still_not_enough(self):
        self.message(self.alex, 2)
        self.assertIsNone(connection.compute(self.relationship))

    def test_presentation_hides_rather_than_showing_a_placeholder(self):
        shown = connection.presentation(self.relationship.id)

        # "—/100" reads as a zero to anyone already anxious about it.
        self.assertIsNone(shown["score"])
        self.assertEqual(shown["emphasis"], "hidden")


class SmoothingTests(ConnectionTestCase):
    def test_the_first_reading_is_taken_as_is(self):
        self.mutual()
        self.assertEqual(connection.update(self.relationship), connection.compute(self.relationship))

    def test_a_small_change_does_not_move_the_number(self):
        self.mutual()
        first = connection.update(self.relationship)
        self.gratitude(self.alex, 1)

        # One extra thank-you on a Tuesday is not news.
        self.assertEqual(connection.update(self.relationship), first)

    def test_a_real_change_does_move_it(self):
        self.busy_but_one_sided()
        low = connection.update(self.relationship)
        self.mutual()
        self.gratitude(self.sam, 10)
        for i in range(10):
            self.check_in(self.sam, days_ago=i + 5)

        raised = connection.update(self.relationship)

        self.assertGreater(raised, low)

    def test_it_moves_less_than_the_raw_reading(self):
        self.busy_but_one_sided()
        connection.update(self.relationship)
        self.mutual()

        raw = connection.compute(self.relationship)
        smoothed = connection.update(self.relationship)

        # Smoothing is what makes a /100 number honest: the underlying
        # measurement has nothing like 100 distinguishable states.
        self.assertLess(smoothed, raw)

    def test_the_trend_series_is_bounded(self):
        self.mutual()
        row = ConnectionScore.objects.create(
            relationship=self.relationship,
            value=50.0,
            series=[{"week": f"2026-W{i:02d}", "value": 50} for i in range(30)],
        )
        connection.update(self.relationship)
        row.refresh_from_db()

        # A trend line, not a dated record of when they struggled.
        self.assertLessEqual(len(row.series), connection.SERIES_LENGTH)

    def test_an_update_failure_is_survivable(self):
        self.mutual()
        with patch(
            "apps.personalization.models.ConnectionScore.objects.get_or_create",
            side_effect=RuntimeError("db down"),
        ):
            self.assertIsNone(connection.update(self.relationship))


class PresentationTests(ConnectionTestCase):
    def test_a_healthy_score_is_featured(self):
        ConnectionScore.objects.create(relationship=self.relationship, value=78.0)

        self.assertEqual(connection.presentation(self.relationship.id)["emphasis"], "feature")

    def test_a_low_score_goes_quiet_rather_than_leading(self):
        ConnectionScore.objects.create(relationship=self.relationship, value=20.0)

        # The morning after a fight, someone opening the app for help should be
        # met with something useful, not a number telling them they are failing.
        self.assertEqual(connection.presentation(self.relationship.id)["emphasis"], "quiet")

    def test_direction_is_weekly_and_needs_two_points(self):
        ConnectionScore.objects.create(
            relationship=self.relationship,
            value=60.0,
            series=[{"week": "2026-W20", "value": 50}],
        )
        self.assertIsNone(connection.presentation(self.relationship.id)["direction"])

    def test_direction_reports_movement(self):
        ConnectionScore.objects.create(
            relationship=self.relationship,
            value=60.0,
            series=[
                {"week": "2026-W20", "value": 50},
                {"week": "2026-W21", "value": 60},
            ],
        )
        self.assertEqual(connection.presentation(self.relationship.id)["direction"], "up")

    def test_a_flat_week_reads_as_steady_not_as_a_fall(self):
        ConnectionScore.objects.create(
            relationship=self.relationship,
            value=60.0,
            series=[
                {"week": "2026-W20", "value": 60},
                {"week": "2026-W21", "value": 61},
            ],
        )
        self.assertEqual(connection.presentation(self.relationship.id)["direction"], "steady")

    def test_a_fall_is_reported_honestly(self):
        ConnectionScore.objects.create(
            relationship=self.relationship,
            value=40.0,
            series=[
                {"week": "2026-W20", "value": 60},
                {"week": "2026-W21", "value": 40},
            ],
        )
        shown = connection.presentation(self.relationship.id)
        # Quiet, but not hidden and not sugared. The direction is true.
        self.assertEqual(shown["direction"], "down")
        self.assertEqual(shown["emphasis"], "quiet")
