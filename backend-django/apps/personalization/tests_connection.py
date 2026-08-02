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
from apps.chat import assist
from apps.personalization.models import ConnectionScore, RuptureAssessment
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

    def test_repair_is_not_scored_when_there_was_nothing_to_repair(self):
        """It used to be: any repair tendency at all scored the full component,
        whether or not the couple had had a row. That scored a calm fortnight
        and a mended one identically, and marked down a calm couple who simply
        never needed to repair anything. Now the question is not asked."""
        self.mutual()
        parts, _ = connection._components(
            self.relationship, timezone.now() - timedelta(days=connection.WINDOW_DAYS)
        )
        self.assertNotIn("repair", parts)

        before = connection.compute(self.relationship)
        for _ in range(behaviour.MIN_OBSERVATIONS + 2):
            behaviour.observe(self.alex, behaviour.REPAIRS)
        self.assertEqual(connection.compute(self.relationship), before)

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
    def a_day_passes(self):
        """Age the stored reading. ``updated_at`` is auto_now, so this has to
        go through the queryset rather than through save()."""
        ConnectionScore.objects.filter(relationship=self.relationship).update(
            updated_at=timezone.now() - timedelta(days=1)
        )

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

        # A day later. The smoothing is proportional to elapsed time, so a
        # second reading taken in the same instant is correctly no reading at
        # all — the number moves with the week, not with the job.
        self.a_day_passes()
        raised = connection.update(self.relationship)

        self.assertGreater(raised, low)

    def test_it_moves_less_than_the_raw_reading(self):
        self.busy_but_one_sided()
        connection.update(self.relationship)
        self.mutual()

        raw = connection.compute(self.relationship)
        self.a_day_passes()
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
        self.a_day_passes()
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


class SmoothingIsPerDayTests(ConnectionTestCase):
    """The score's inertia is a property of time, not of how often a job ran.

    SMOOTHING is what turns a jittery measurement into something worth putting
    on a home screen, and that only holds if the steps are days. Folded in
    twice in an afternoon the old form moved the number twice as far, so it
    depended on scheduler behaviour rather than on the relationship.
    """

    def age(self, days):
        ConnectionScore.objects.filter(relationship=self.relationship).update(
            updated_at=timezone.now() - timedelta(days=days)
        )

    def stored(self):
        return ConnectionScore.objects.get(relationship=self.relationship).value

    def test_a_second_run_in_the_same_instant_changes_nothing(self):
        self.mutual()
        connection.update(self.relationship)
        first = self.stored()

        for _ in range(5):
            connection.update(self.relationship)

        self.assertEqual(self.stored(), first)

    def test_a_run_the_next_day_does_move_it(self):
        self.mutual()
        self.gratitude(self.alex, 10)
        connection.update(self.relationship)
        first = self.stored()

        # One partner goes quiet, so the reading genuinely falls — but there is
        # still plenty of evidence, so the score is a number rather than None.
        self.message(self.alex, 60)
        self.age(1)
        connection.update(self.relationship)

        self.assertLess(self.stored(), first)

    def test_a_missed_day_catches_up_rather_than_pretending_it_did_not_happen(self):
        """Four days of drift should not leave the number where one day would.

        The old form could not tell the difference: it applied one step per
        call, so a job that missed three nights quietly under-corrected for
        ever after.
        """
        self.mutual()
        self.gratitude(self.alex, 10)
        connection.update(self.relationship)
        start = self.stored()

        self.message(self.alex, 60)

        self.age(1)
        connection.update(self.relationship)
        after_one_day = self.stored()

        ConnectionScore.objects.filter(relationship=self.relationship).update(value=start)
        self.age(4)
        connection.update(self.relationship)
        after_four_days = self.stored()

        self.assertLess(after_four_days, after_one_day)

    def test_the_first_ever_reading_is_not_blocked(self):
        """A couple with no stored value takes the raw number, elapsed or not."""
        self.mutual()
        self.assertIsNotNone(connection.update(self.relationship))


class RuptureAndRepairTests(ConnectionTestCase):
    """The one component that can fall for a reason other than absence.

    A score that can only rise or hold during deterioration is reassurance
    rather than a reading. This is the part that lets it say things are going
    badly — and the part most able to say it wrongly, so the conjunction that
    guards it is what these tests are really about.
    """

    def sharp(self, sender, when=None, text="you're pathetic and I don't know why I bother"):
        """An argument, not a line.

        A whole day is the unit judged now, and a day is only worth judging if
        there was a conversation in it — so a fixture that writes one message
        and calls it a fight was describing something the product would not
        look at. Three lines is the floor, and it is also what an argument
        actually looks like.
        """
        last = None
        for offset, body in enumerate((text, "forget it", "this is typical you")):
            last = CoupleMessage.objects.create(
                relationship=self.relationship,
                sender=sender if offset % 2 == 0 else self.other_partner(sender),
                body=body,
            )
            if when is not None:
                CoupleMessage.objects.filter(id=last.id).update(
                    created_at=when + timedelta(minutes=offset)
                )
        if when is not None:
            last.refresh_from_db()
        return last

    def other_partner(self, sender):
        return self.sam if sender == self.alex else self.alex

    def calm(self, sender, when=None, text="what time are you back"):
        """One ordinary message. Emphatically not `sharp()` with nicer words —
        that helper writes a three-line argument whatever text it is given, so
        delegating to it made every "calm" message part of a fight."""
        message = CoupleMessage.objects.create(
            relationship=self.relationship, sender=sender, body=text
        )
        if when is not None:
            CoupleMessage.objects.filter(id=message.id).update(created_at=when)
            message.refresh_from_db()
        return message

    def assess(self, is_rupture=True, confidence=0.9):
        """Record a verdict for every candidate exchange, without a model call.

        The score reads *stored* assessments now — an exchange nobody has
        judged is not a rupture, which is the fail-safe direction. These tests
        are about the repair balance rather than about the classifier, so they
        supply the verdict directly; `assess_rupture` has its own tests.
        """
        from apps.chat.models import CoupleMessage
        from apps.personalization.models import RuptureAssessment

        rows = list(
            CoupleMessage.objects.filter(
                relationship=self.relationship, deleted_at__isnull=True
            )
            .select_related("media")
            .order_by("created_at")
        )
        # Stands in for the classifier, agreeing with the lexicon. Marking
        # *every* window a rupture would make the calm days ruptures too, which
        # is neither what the model would say nor what these tests are about.
        from apps.chat.assist import is_rupture as lexicon_says

        for start, end, lines in connection.conversation_windows(self.relationship, rows):
            verdict = is_rupture and lexicon_says(
                [line.split(": ", 1)[-1] for line in lines]
            )
            RuptureAssessment.objects.update_or_create(
                relationship=self.relationship,
                started_at=start,
                defaults={
                    "ended_at": end,
                    "is_rupture": bool(verdict),
                    "confidence": confidence,
                },
            )

    def parts(self):
        self.assess()
        parts, _ = connection._components(
            self.relationship, timezone.now() - timedelta(days=connection.WINDOW_DAYS)
        )
        return parts

    # ── the confidence guard ────────────────────────────────────────────

    def test_one_detected_rupture_does_nothing_at_all(self):
        """The detector is eight keyword phrases. A single false positive must
        not be able to move anybody's score."""
        self.mutual()
        self.sharp(self.alex)
        self.assertNotIn("repair", self.parts())

    def test_two_unrepaired_ruptures_do_move_it(self):
        # No ordinary conversation afterwards on purpose. `mutual()` writes its
        # messages at "now", which fall inside the last rupture's repair window
        # and legitimately mend it — the first version of this test was wrong
        # about its own fixture rather than about the code.
        now = timezone.now()
        self.sharp(self.alex, now - timedelta(days=9))
        self.sharp(self.alex, now - timedelta(days=5))
        self.assertEqual(self.parts()["repair"], 0.0)

    # ── what counts as mended ───────────────────────────────────────────

    def test_coming_back_and_talking_normally_counts_as_repair(self):
        """Most couples repair by talking again, not by sending a ceremony."""
        self.mutual()
        now = timezone.now()
        for offset in (6, 2):
            self.sharp(self.alex, now - timedelta(days=offset))
            self.calm(self.alex, now - timedelta(days=offset, hours=-2))
            self.calm(self.sam, now - timedelta(days=offset, hours=-3))

        self.assertEqual(self.parts()["repair"], 1.0)

    def test_a_repair_sticker_counts_even_with_no_conversation_after(self):
        self.mutual()
        now = timezone.now()
        for offset in (6, 2):
            self.sharp(self.alex, now - timedelta(days=offset))
            sticker = CoupleMessage.objects.create(
                relationship=self.relationship,
                sender=self.alex,
                kind=CoupleMessage.KIND_STICKER,
                sticker="repair.sorry",
            )
            CoupleMessage.objects.filter(id=sticker.id).update(
                created_at=now - timedelta(days=offset, hours=-1)
            )

        self.assertEqual(self.parts()["repair"], 1.0)

    def test_only_one_partner_coming_back_is_not_repair(self):
        """One person talking into silence is the thing that needed repairing."""
        now = timezone.now()
        for offset in (9, 5):
            self.sharp(self.alex, now - timedelta(days=offset))
            self.calm(self.alex, now - timedelta(days=offset, hours=-2))

        self.assertEqual(self.parts()["repair"], 0.0)

    def test_a_partly_mended_fortnight_scores_in_between(self):
        now = timezone.now()
        self.sharp(self.alex, now - timedelta(days=11))
        self.calm(self.alex, now - timedelta(days=10))
        self.calm(self.sam, now - timedelta(days=10, minutes=-30))
        self.sharp(self.alex, now - timedelta(days=5))

        self.assertEqual(self.parts()["repair"], 0.5)

    def test_a_long_argument_is_one_rupture_not_nine(self):
        """Otherwise saying 'forget it' twice in an evening reads as two
        failures rather than one bad night."""
        self.mutual()
        now = timezone.now()
        for minutes in range(0, 50, 10):
            self.sharp(self.alex, now - timedelta(days=3, minutes=minutes))

        self.assertNotIn("repair", self.parts())

    # ── conflict is not connection ──────────────────────────────────────

    def test_an_argument_does_not_count_toward_reciprocity(self):
        """A fight is a burst of messages from both partners, which is exactly
        the shape reciprocity rewards. It used to produce a couple's highest
        reading of the month during their worst week."""
        self.mutual()
        calm_mutuality = self.parts()["mutuality"]

        now = timezone.now()
        self.sharp(self.alex, now - timedelta(hours=3))
        for minutes in range(1, 40, 4):
            self.calm(
                self.alex if minutes % 8 else self.sam,
                now - timedelta(hours=3, minutes=-minutes),
                text="and another thing",
            )

        self.assertLessEqual(self.parts()["mutuality"], calm_mutuality)

    def test_a_fight_still_counts_as_evidence(self):
        """Dropping it from `events` too would let a couple who did nothing but
        argue fall under MIN_EVENTS and be shown nothing — hiding the one
        reading that mattered."""
        now = timezone.now()
        self.sharp(self.alex, now - timedelta(days=6))
        self.sharp(self.sam, now - timedelta(days=2))
        for minutes in range(10):
            self.calm(self.alex, now - timedelta(days=2, minutes=-minutes))

        _, events = connection._components(
            self.relationship, now - timedelta(days=connection.WINDOW_DAYS)
        )
        self.assertGreaterEqual(events, connection.MIN_EVENTS)
        self.assertIsNotNone(connection.compute(self.relationship))


class GoingQuietTests(ConnectionTestCase):
    """A couple who stop are not a couple who are doing well."""

    def test_the_number_is_withdrawn_rather_than_frozen(self):
        """It used to return early and leave the stored value alone, so a
        couple who stopped using the product kept their best reading for ever.
        Measured before this changed: an active fortnight scored 68, and ten
        days of total silence still showed 68."""
        self.mutual()
        self.assertIsNotNone(connection.update(self.relationship))
        self.assertIsNotNone(connection.presentation(self.relationship.id)["score"])

        stale = timezone.now() - timedelta(days=connection.WINDOW_DAYS + 5)
        CoupleMessage.objects.all().update(created_at=stale)
        GratitudeMoment.objects.all().update(created_at=stale)
        RelationshipCheckIn.objects.all().update(created_at=stale)

        self.assertIsNone(connection.update(self.relationship))
        shown = connection.presentation(self.relationship.id)
        self.assertIsNone(shown["score"])
        self.assertEqual(shown["emphasis"], "hidden")

    def test_their_history_is_kept_on_the_row(self):
        """Hiding the number is not forgetting the couple.

        `presentation` still reports an empty series while hidden — showing a
        trend line under no current number would be a graph of a relationship
        the product has just said it cannot read. What matters is that the
        history survives on the row, so it is still there if they come back.
        """
        self.mutual()
        connection.update(self.relationship)
        CoupleMessage.objects.all().update(
            created_at=timezone.now() - timedelta(days=connection.WINDOW_DAYS + 5)
        )
        RelationshipCheckIn.objects.all().update(
            created_at=timezone.now() - timedelta(days=connection.WINDOW_DAYS + 5)
        )
        GratitudeMoment.objects.all().update(
            created_at=timezone.now() - timedelta(days=connection.WINDOW_DAYS + 5)
        )
        connection.update(self.relationship)

        row = ConnectionScore.objects.get(relationship=self.relationship)
        self.assertIsNone(row.value)
        self.assertTrue(row.series)


class StoredAssessmentTests(ConnectionTestCase):
    """The score reads verdicts; it does not form them.

    Rupture assessment is retrospective, so it happens once in the nightly job
    and is read back here. That keeps the number deterministic when it is read
    and keeps every model call out of the path that computes it.
    """

    def sharp(self, sender, when=None):
        message = CoupleMessage.objects.create(
            relationship=self.relationship, sender=sender, body="you're pathetic"
        )
        if when is not None:
            CoupleMessage.objects.filter(id=message.id).update(created_at=when)
            message.refresh_from_db()
        return message

    def rows(self):
        return list(
            CoupleMessage.objects.filter(relationship=self.relationship)
            .select_related("media")
            .order_by("created_at")
        )

    def record(self, start, end, is_rupture, confidence=0.9):
        RuptureAssessment.objects.create(
            relationship=self.relationship,
            started_at=start,
            ended_at=end,
            is_rupture=is_rupture,
            confidence=confidence,
        )

    def a_days_conversation(self, when):
        """Enough messages that the day is worth judging at all."""
        for sender, body in (
            (self.sam, "are you even listening to me"),
            (self.alex, "yes"),
            (self.sam, "it does not feel like it"),
        ):
            message = CoupleMessage.objects.create(
                relationship=self.relationship, sender=sender, body=body
            )
            CoupleMessage.objects.filter(id=message.id).update(created_at=when)

    def test_an_unassessed_exchange_is_not_a_rupture(self):
        """The fail-safe direction: a couple whose assessment job has not run
        is not marked down for arguments nobody has confirmed they had."""
        self.a_days_conversation(timezone.now() - timedelta(days=5))
        self.assertEqual(connection._ruptures(self.relationship, self.rows()), [])

    def test_a_day_of_plain_tone_withdrawal_is_still_judged(self):
        """The reason the lexicon cannot be the gate. Not one of these messages
        grades as sharp, and this is the exchange the feature exists for."""
        self.a_days_conversation(timezone.now() - timedelta(days=5))
        windows = connection.conversation_windows(self.relationship, self.rows())

        self.assertEqual(len(windows), 1)
        from apps.chat.assist import is_rupture

        self.assertFalse(is_rupture([m.body for m in self.rows()]))

    def test_a_quiet_day_is_not_worth_asking_about(self):
        message = CoupleMessage.objects.create(
            relationship=self.relationship, sender=self.alex, body="night x"
        )
        CoupleMessage.objects.filter(id=message.id).update(
            created_at=timezone.now() - timedelta(days=5)
        )
        self.assertEqual(
            connection.conversation_windows(self.relationship, self.rows()), []
        )

    def test_an_assessed_one_is(self):
        now = timezone.now()
        self.a_days_conversation(now - timedelta(days=5))
        start, end, _ = connection.conversation_windows(self.relationship, self.rows())[0]
        self.record(start, end, is_rupture=True)

        self.assertEqual(len(connection._ruptures(self.relationship, self.rows())), 1)

    def test_a_verdict_of_no_is_respected(self):
        """The whole point of comprehension: something that read the exchange
        said it was not a fight, and that wins over any keyword in it."""
        now = timezone.now()
        self.a_days_conversation(now - timedelta(days=5))
        self.sharp(self.alex, now - timedelta(days=5))
        start, end, _ = connection.conversation_windows(self.relationship, self.rows())[0]
        self.record(start, end, is_rupture=False)

        self.assertEqual(connection._ruptures(self.relationship, self.rows()), [])

    def test_a_hedged_verdict_does_not_count(self):
        now = timezone.now()
        self.a_days_conversation(now - timedelta(days=5))
        start, end, _ = connection.conversation_windows(self.relationship, self.rows())[0]
        self.record(start, end, is_rupture=True, confidence=0.2)

        self.assertEqual(connection._ruptures(self.relationship, self.rows()), [])

    def test_candidates_carry_the_surrounding_exchange(self):
        """Judging "that's fine." without the hour before it is judging the
        wrong thing."""
        now = timezone.now()
        CoupleMessage.objects.create(
            relationship=self.relationship, sender=self.sam, body="are you even listening"
        ).id
        self.sharp(self.alex)
        CoupleMessage.objects.create(
            relationship=self.relationship, sender=self.sam, body="that's fine."
        )
        _, _, lines = connection.conversation_windows(self.relationship, self.rows())[0]

        self.assertGreater(len(lines), 1)
        self.assertTrue(any("that's fine" in line for line in lines))
        self.assertTrue(all(line.startswith(("A:", "B:")) for line in lines))
        _ = now


class RuptureClassifierTests(TestCase):
    """Parsing the verdict. What it decides is the model's business; that the
    answer survives the trip is ours."""

    def test_a_clear_yes(self):
        with patch("apps.chat.assist._complete", return_value="RUPTURE: yes\nCONFIDENCE: 0.9"):
            self.assertEqual(assist.assess_rupture(["A: you're pathetic"]), (True, 0.9))

    def test_a_clear_no(self):
        with patch("apps.chat.assist._complete", return_value="RUPTURE: no\nCONFIDENCE: 0.8"):
            self.assertEqual(assist.assess_rupture(["A: you're the worst 😂"]), (False, 0.8))

    def test_a_missing_confidence_is_zero_not_certain(self):
        with patch("apps.chat.assist._complete", return_value="RUPTURE: yes"):
            self.assertEqual(assist.assess_rupture(["A: hey"]), (True, 0.0))

    def test_an_unparseable_reply_is_no_answer_at_all(self):
        """None means "ask again tomorrow", not "this was benign". A failed
        call must not be recorded as a verdict."""
        for raw in ("who can say, really", "", None):
            with patch("apps.chat.assist._complete", return_value=raw):
                self.assertIsNone(assist.assess_rupture(["A: hey"]), raw)

    def test_confidence_is_clamped(self):
        with patch("apps.chat.assist._complete", return_value="RUPTURE: yes\nCONFIDENCE: 7"):
            self.assertEqual(assist.assess_rupture(["A: hey"])[1], 1.0)

    def test_an_empty_exchange_is_never_asked_about(self):
        with patch("apps.chat.assist._complete") as complete:
            self.assertIsNone(assist.assess_rupture(["", None]))
        complete.assert_not_called()
