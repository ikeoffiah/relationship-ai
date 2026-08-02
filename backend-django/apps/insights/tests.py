"""What may be read out of an insight, and by whom.

The read path is the whole safety story — an insight is the one place where
something derived from what a partner said privately could reach the other —
and it was once enforced by nothing at all: the consent queryset was written
and never attached to the model.

Two detectors now. ``recurring_theme`` asks a model and so is tested against a
patched ``_complete``; ``perception_gap`` is arithmetic over two columns and so
is tested against exact numbers. See ``docs/relationship-insights.md``.
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.insights import detectors, tasks
from apps.insights.models import RelationshipInsight
from apps.relationships.models import Relationship

User = get_user_model()


class InsightReadPathTests(TestCase):
    def setUp(self):
        self.alex = User.objects.create_user(email="i-a@t.local", password="pw12345!")
        self.sam = User.objects.create_user(email="i-b@t.local", password="pw12345!")
        self.stranger = User.objects.create_user(email="i-x@t.local", password="pw12345!")
        self.relationship = Relationship.objects.create(
            partner_a=self.alex, partner_b=self.sam, status="active"
        )

    def insight(self, **kw):
        return RelationshipInsight.objects.create(
            relationship=self.relationship,
            type="perception_gap",
            theme="the weekend",
            confidence=0.9,
            a_narrative_summary="what Alex said alone",
            b_narrative_summary="what Sam said alone",
            synthesis="they remember it differently",
            **kw,
        )

    def test_the_manager_is_attached(self):
        """It was not. `objects.public(user)` raised AttributeError, so every
        consent filter in managers.py was unreachable."""
        self.assertTrue(hasattr(RelationshipInsight.objects, "public"))

    def test_nothing_is_visible_by_default(self):
        self.insight()
        for user in (self.alex, self.sam):
            self.assertEqual(list(RelationshipInsight.objects.public(user)), [])

    def test_a_partner_sees_it_only_after_their_own_consent(self):
        insight = self.insight(shared_with_a=True)
        self.assertEqual(list(RelationshipInsight.objects.public(self.alex)), [insight])
        self.assertEqual(list(RelationshipInsight.objects.public(self.sam)), [])

    def test_one_partners_consent_does_not_reveal_it_to_the_other(self):
        """The failure this whole design exists to prevent."""
        self.insight(shared_with_a=True)
        self.assertEqual(list(RelationshipInsight.objects.public(self.sam)), [])

    def test_approved_for_joint_alone_reveals_nothing(self):
        """`for_joint_prompt()` used to return these regardless of consent,
        documenting that a joint session is "a shared context" — which
        confuses the session being shared with the evidence being shared."""
        self.insight(approved_for_joint=True)
        for user in (self.alex, self.sam):
            self.assertEqual(list(RelationshipInsight.objects.public(user)), [])

    def test_there_is_no_joint_prompt_reader(self):
        """It comes back when there is a consent flow to derive it from."""
        self.assertFalse(hasattr(RelationshipInsight.objects, "for_joint_prompt"))

    def test_a_stranger_sees_nothing_however_the_flags_are_set(self):
        self.insight(shared_with_a=True, shared_with_b=True, approved_for_joint=True)
        self.assertEqual(list(RelationshipInsight.objects.public(self.stranger)), [])


class ThemeDetectorTests(TestCase):
    """Finding a pattern a couple is too close to see, and mostly not finding
    one — the prompt says most couples do not have a recurring theme, and a
    detector that produces one anyway is worse than no detector."""

    def setUp(self):
        self.alex = User.objects.create_user(email="t-a@t.local", password="pw12345!")
        self.sam = User.objects.create_user(email="t-b@t.local", password="pw12345!")
        self.relationship = Relationship.objects.create(
            partner_a=self.alex, partner_b=self.sam, status="active"
        )

    def rupture(self, days_ago, body="you always do this"):
        from apps.chat.models import CoupleMessage
        from apps.personalization.models import RuptureAssessment

        when = timezone.now() - timedelta(days=days_ago)
        message = CoupleMessage.objects.create(
            relationship=self.relationship, sender=self.alex, body=body
        )
        CoupleMessage.objects.filter(id=message.id).update(created_at=when)
        RuptureAssessment.objects.create(
            relationship=self.relationship,
            started_at=when,
            ended_at=when + timedelta(minutes=5),
            is_rupture=True,
            confidence=0.9,
        )

    def test_a_couple_with_one_argument_has_no_theme(self):
        """Two arguments about different things is a fortnight, not a pattern."""
        self.rupture(10)
        with patch("apps.chat.assist._complete") as complete:
            self.assertIsNone(detectors.recurring_theme(self.relationship))
        complete.assert_not_called()

    def test_three_arguments_are_worth_asking_about(self):
        for days in (20, 12, 4):
            self.rupture(days)
        with patch(
            "apps.chat.assist._complete",
            return_value=(
                "THEME: how evenings get decided\n"
                "ARGUMENTS: 1, 2, 3\n"
                "CONFIDENCE: 0.8"
            ),
        ):
            found = detectors.recurring_theme(self.relationship)

        self.assertEqual(found["theme"], "how evenings get decided")
        self.assertEqual(found["confidence"], 0.8)

    def test_a_theme_it_cannot_point_at_is_not_a_theme(self):
        """The regression that made this check exist.

        Three unrelated arguments — a back door left unlocked, a rude brother,
        an untaxed car — came back live as "responsibility for shared tasks" at
        0.8 confidence, which is true of every couple who has ever argued and
        tells this one nothing. The tell was not the confidence, which was
        0.8 against 0.9 for a real theme and so useless as a threshold. It was
        that when asked *which* arguments the subject appeared in, the model
        could name only two. Confidence is a self-report; a citation is a claim
        that can be checked.
        """
        for days in (20, 12, 4):
            self.rupture(days)
        with patch(
            "apps.chat.assist._complete",
            return_value=(
                "THEME: responsibility for shared tasks\n"
                "ARGUMENTS: 1, 3\n"
                "CONFIDENCE: 0.8"
            ),
        ):
            self.assertIsNone(detectors.recurring_theme(self.relationship))

    def test_a_theme_with_no_citation_at_all_is_not_a_theme(self):
        """Silence on the citation is not consent. A model that ignores the
        field has not shown its working, and the default has to be no."""
        for days in (20, 12, 4):
            self.rupture(days)
        with patch(
            "apps.chat.assist._complete",
            return_value="THEME: money\nCONFIDENCE: 0.95",
        ):
            self.assertIsNone(detectors.recurring_theme(self.relationship))

    def test_no_theme_is_a_normal_answer(self):
        for days in (20, 12, 4):
            self.rupture(days)
        with patch("apps.chat.assist._complete", return_value="THEME: none"):
            self.assertIsNone(detectors.recurring_theme(self.relationship))

    def test_a_hedged_theme_is_not_stored(self):
        """An insight is a claim about somebody's relationship, and a hedged
        claim is worse than silence."""
        for days in (20, 12, 4):
            self.rupture(days)
        with patch(
            "apps.chat.assist._complete",
            return_value=(
                "THEME: something about money\n"
                "ARGUMENTS: 1, 2, 3\n"
                "CONFIDENCE: 0.3"
            ),
        ):
            self.assertIsNone(detectors.recurring_theme(self.relationship))

    def test_it_reads_assessed_ruptures_not_keywords(self):
        """Inherits the comprehension work rather than reintroducing a lexicon
        — an argument nobody assessed is not evidence of a pattern."""
        from apps.chat.models import CoupleMessage

        for _ in range(5):
            CoupleMessage.objects.create(
                relationship=self.relationship,
                sender=self.alex,
                body="you always do this",
            )
        with patch("apps.chat.assist._complete") as complete:
            self.assertIsNone(detectors.recurring_theme(self.relationship))
        complete.assert_not_called()


class SurfacingRulesTests(TestCase):
    """Whether this couple may be shown anything at all today."""

    def setUp(self):
        self.alex = User.objects.create_user(email="s-a@t.local", password="pw12345!")
        self.sam = User.objects.create_user(email="s-b@t.local", password="pw12345!")
        self.relationship = Relationship.objects.create(
            partner_a=self.alex, partner_b=self.sam, status="active"
        )

    def say(self, body, days_ago=1):
        from apps.chat.models import CoupleMessage

        message = CoupleMessage.objects.create(
            relationship=self.relationship, sender=self.alex, body=body
        )
        CoupleMessage.objects.filter(id=message.id).update(
            created_at=timezone.now() - timedelta(days=days_ago)
        )

    def open_rupture(self, days_ago=1):
        from apps.personalization.models import RuptureAssessment

        when = timezone.now() - timedelta(days=days_ago)
        RuptureAssessment.objects.create(
            relationship=self.relationship,
            started_at=when,
            ended_at=when,
            is_rupture=True,
            confidence=0.9,
        )

    def test_an_ordinary_couple_may_be_shown_things(self):
        self.say("what time are you back")
        self.assertTrue(tasks.may_surface(self.relationship))

    def test_not_in_the_middle_of_an_argument(self):
        """Naming a recurring theme the morning after one is a prosecution."""
        self.say("what time are you back")
        self.open_rupture(days_ago=1)
        self.assertFalse(tasks.may_surface(self.relationship))

    def test_but_an_old_argument_does_not_hold_it_back(self):
        self.say("what time are you back")
        self.open_rupture(days_ago=30)
        self.assertTrue(tasks.may_surface(self.relationship))

    def test_an_abuse_signal_holds_everything(self):
        """A perception-gap insight in a coercive relationship is a tool for
        the controlling partner. Nothing crosses."""
        self.say("I went through your phone last night", days_ago=2)
        self.assertFalse(tasks.may_surface(self.relationship))

    def test_it_lifts_after_ninety_days(self):
        """Not for ever. Permanence was out of character for a product where
        everything else decays, and it meant one hit on a keyword list removed
        a feature with no route back."""
        self.say("I went through your phone last night", days_ago=120)
        self.say("what time are you back", days_ago=1)
        self.assertTrue(tasks.may_surface(self.relationship))

    def test_a_new_signal_restarts_the_clock(self):
        self.say("I went through your phone last night", days_ago=120)
        self.say("let me see your phone", days_ago=5)
        self.assertFalse(tasks.may_surface(self.relationship))

    def test_repair_does_not_shorten_it(self):
        """The trap the spec exists to avoid: repair signals are things a
        controlling partner can perform and can pressure the other into
        performing, so "demonstrate repair to restore access" would be
        instructions for looking repaired."""
        from apps.chat.models import CoupleMessage

        self.say("I went through your phone last night", days_ago=5)
        for _ in range(5):
            CoupleMessage.objects.create(
                relationship=self.relationship,
                sender=self.alex,
                kind=CoupleMessage.KIND_STICKER,
                sticker="repair.sorry",
            )
        self.assertFalse(tasks.may_surface(self.relationship))

    def stored_insight(self):
        from apps.insights.models import RelationshipInsight

        return RelationshipInsight.objects.create(
            relationship=self.relationship,
            type="recurring_theme",
            theme="how evenings get decided",
            confidence=0.9,
            shared_with_a=True,
            shared_with_b=True,
            expires_at=timezone.now() + timedelta(days=30),
        )

    def test_a_signal_retracts_what_was_already_shown(self):
        """Gating synthesis was not enough, and this is the gap it left.

        ``may_surface`` ran only in the nightly task, so a signal stopped the
        *next* insight while one written last week went on crossing for the
        rest of its thirty days. A couple can be shown "here is the pattern in
        your arguments" for a month after the thing that should have silenced
        it.
        """
        insight = self.stored_insight()
        self.say("I went through your phone last night", days_ago=2)

        tasks.synthesise_insights()

        insight.refresh_from_db()
        self.assertFalse(insight.shared_with_a)
        self.assertFalse(insight.shared_with_b)
        self.assertFalse(insight.approved_for_joint)

    def test_an_open_argument_does_not_retract_anything(self):
        """The distinction worth keeping: a signal retracts, a rupture only
        waits. A theme they were already shown is not made harmful by this
        week's argument, and yanking it away would be its own message."""
        insight = self.stored_insight()
        self.say("what time are you back")
        self.open_rupture(days_ago=1)

        tasks.synthesise_insights()

        insight.refresh_from_db()
        self.assertTrue(insight.shared_with_a)
        self.assertTrue(insight.shared_with_b)

    def test_the_referral_retracts_immediately(self):
        """A night is a long time to leave it on the screen, so the read-coach
        referral withdraws too rather than waiting for the sweep."""
        from apps.chat import assist

        insight = self.stored_insight()
        result = assist.coach_response(
            self.relationship, self.sam, "I went through your phone last night"
        )

        self.assertTrue(result["defer_to_support"])
        self.assertIsNone(result["guidance"])
        insight.refresh_from_db()
        self.assertFalse(insight.shared_with_a)
        self.assertFalse(insight.shared_with_b)

    def test_a_failed_withdrawal_never_costs_the_referral(self):
        """The referral is the part that matters. If retraction breaks, the
        person still gets routed to support."""
        from apps.chat import assist

        with patch(
            "apps.insights.tasks.withdraw_insights",
            side_effect=RuntimeError("boom"),
        ):
            result = assist.coach_response(
                self.relationship, self.sam, "I went through your phone last night"
            )
        self.assertTrue(result["defer_to_support"])

    def test_a_broken_check_holds_things_back(self):
        """Fails closed, unlike everything else in this codebase — the cost of
        being wrong the other way is handing somebody a tool."""
        with patch(
            "apps.chat.models.CoupleMessage.objects.filter",
            side_effect=RuntimeError("boom"),
        ):
            self.assertFalse(tasks.may_surface(self.relationship))


class InsightEndpointTests(TestCase):
    """The read path, over HTTP."""

    def setUp(self):
        from rest_framework.test import APIClient

        self.alex = User.objects.create_user(email="e-a@t.local", password="pw12345!")
        self.sam = User.objects.create_user(email="e-b@t.local", password="pw12345!")
        self.relationship = Relationship.objects.create(
            partner_a=self.alex, partner_b=self.sam, status="active"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.alex)

    def insight(self, **kw):
        defaults = dict(
            relationship=self.relationship,
            type="recurring_theme",
            theme="how evenings get decided",
            confidence=0.8,
            shared_with_a=True,
            shared_with_b=True,
            expires_at=timezone.now() + timedelta(days=30),
        )
        defaults.update(kw)
        return RelationshipInsight.objects.create(**defaults)

    def get(self):
        return self.client.get("/api/v1/insights/")

    def test_a_shape_only_insight_is_returned(self):
        self.insight()
        body = self.get().json()
        self.assertEqual(len(body["insights"]), 1)
        self.assertEqual(body["insights"][0]["theme"], "how evenings get decided")

    def test_the_narrative_halves_are_not_exposed(self):
        """They are empty today. The day a detector fills them, they must not
        ship to both partners because a serializer field looked relevant."""
        self.insight(
            a_narrative_summary="what Alex said alone",
            b_narrative_summary="what Sam said alone",
            synthesis="they remember it differently",
        )
        raw = self.get().content.decode()
        for private in ("what Alex said alone", "what Sam said alone", "differently"):
            self.assertNotIn(private, raw)

    def test_an_expired_insight_is_not_shown(self):
        """A theme from three months ago is a claim about a couple who may well
        have fixed it."""
        self.insight(expires_at=timezone.now() - timedelta(days=1))
        self.assertEqual(self.get().json()["insights"], [])

    def test_an_unshared_insight_is_not_shown(self):
        self.insight(shared_with_a=False, shared_with_b=False)
        self.assertEqual(self.get().json()["insights"], [])

    def test_a_stranger_sees_nothing(self):
        self.insight()
        stranger = User.objects.create_user(email="e-x@t.local", password="pw12345!")
        self.client.force_authenticate(user=stranger)
        self.assertEqual(self.get().json()["insights"], [])


class PerceptionGapTests(TestCase):
    """The detector that reads both private sides.

    Deterministic, so unlike ``recurring_theme`` these tests assert exact
    numbers rather than mocking a model.
    """

    def setUp(self):
        self.alex = User.objects.create_user(email="g-a@t.local", password="pw12345!")
        self.sam = User.objects.create_user(email="g-b@t.local", password="pw12345!")
        self.relationship = Relationship.objects.create(
            partner_a=self.alex, partner_b=self.sam, status="active"
        )

    def check_ins(self, a_scores, b_scores, start_days_ago=20):
        """One day per score. ``None`` means that partner did not check in."""
        from apps.engagement.models import RelationshipCheckIn

        for offset, (a, b) in enumerate(zip(a_scores, b_scores)):
            when = timezone.now() - timedelta(days=start_days_ago - offset)
            day = when.strftime("%Y-%m-%d")
            for user, score in ((self.alex, a), (self.sam, b)):
                if score is None:
                    continue
                row = RelationshipCheckIn.objects.create(
                    relationship=self.relationship,
                    user=user,
                    connection_score=score,
                    date_key=day,
                )
                # created_at is auto_now_add, so the window filter has to be
                # satisfied through the queryset.
                RelationshipCheckIn.objects.filter(id=row.id).update(created_at=when)

    def test_a_couple_who_agree_have_no_gap(self):
        self.check_ins([4, 4, 5, 4, 4, 5, 4, 4], [4, 5, 4, 4, 5, 4, 4, 4])
        self.assertIsNone(detectors.perception_gap(self.relationship))

    def test_a_sustained_divergence_is_a_gap(self):
        self.check_ins([5, 5, 4, 5, 5, 4, 5, 5], [2, 3, 2, 2, 3, 2, 3, 2])
        found = detectors.perception_gap(self.relationship)

        self.assertIsNotNone(found)
        self.assertGreaterEqual(found["confidence"], detectors.MIN_CONFIDENCE)
        self.assertLessEqual(found["confidence"], 0.95)

    def test_the_shape_never_says_who_rated_higher(self):
        """The property the whole detector is built around.

        Direction is the one thing that cannot cross. Each partner already
        knows their own number, so naming whose was higher would hand them the
        other's private self-report by subtraction. The same phrase has to come
        back whichever way the gap runs.
        """
        self.check_ins([5, 5, 4, 5, 5, 4, 5, 5], [2, 3, 2, 2, 3, 2, 3, 2])
        a_high = detectors.perception_gap(self.relationship)

        from apps.engagement.models import RelationshipCheckIn

        RelationshipCheckIn.objects.all().delete()
        self.check_ins([2, 3, 2, 2, 3, 2, 3, 2], [5, 5, 4, 5, 5, 4, 5, 5])
        b_high = detectors.perception_gap(self.relationship)

        self.assertEqual(a_high, b_high)
        for forbidden in ("you", "your partner", "higher", "lower", "more", "less"):
            self.assertNotIn(forbidden, a_high["theme"].lower().split())

    def test_scores_that_cross_back_and_forth_are_noise(self):
        """Two partners having different Tuesdays is not a perception gap. The
        gap has to hold its direction to mean anything."""
        self.check_ins([5, 1, 5, 1, 5, 1, 5, 1], [1, 5, 1, 5, 1, 5, 1, 5])
        self.assertIsNone(detectors.perception_gap(self.relationship))

    def test_one_partner_checking_in_alone_proves_nothing(self):
        self.check_ins([5, 5, 5, 5, 5, 5, 5, 5], [None] * 8)
        self.assertIsNone(detectors.perception_gap(self.relationship))

    def test_too_few_paired_days(self):
        self.check_ins([5, 5, 5], [2, 2, 2])
        self.assertIsNone(detectors.perception_gap(self.relationship))

    def test_confidence_rises_with_evidence(self):
        """What §6 asked for and no model could give."""
        self.check_ins([5] * 6, [2] * 6)
        thin = detectors.perception_gap(self.relationship)

        from apps.engagement.models import RelationshipCheckIn

        RelationshipCheckIn.objects.all().delete()
        self.check_ins([5] * 14, [2] * 14, start_days_ago=20)
        thick = detectors.perception_gap(self.relationship)

        self.assertGreater(thick["confidence"], thin["confidence"])

    def test_the_private_note_is_never_read(self):
        """A check-in note is free text somebody wrote for themselves. Nothing
        in a shape-only insight could justify decrypting it."""
        from apps.engagement.models import RelationshipCheckIn

        self.check_ins([5] * 8, [2] * 8)
        RelationshipCheckIn.objects.filter(user=self.alex).update(note="ENC:whatever")

        with patch(
            "apps.engagement.models.decrypt_field_value",
            side_effect=AssertionError("the note was read"),
        ):
            self.assertIsNotNone(detectors.perception_gap(self.relationship))

    def test_stale_check_ins_fall_out_of_the_window(self):
        self.check_ins([5] * 8, [2] * 8, start_days_ago=90)
        self.assertIsNone(detectors.perception_gap(self.relationship))

    def test_a_closed_gap_stops_being_shown(self):
        """Thirty days is far too long to keep reporting a gap a couple has
        already closed, so a detector returning None retires its own row."""
        self.check_ins([5] * 8, [2] * 8)
        tasks.synthesise_insights()
        self.assertTrue(
            RelationshipInsight.objects.filter(
                relationship=self.relationship, type="perception_gap", shared_with_a=True
            ).exists()
        )

        from apps.engagement.models import RelationshipCheckIn

        RelationshipCheckIn.objects.all().delete()
        self.check_ins([4] * 8, [4] * 8)
        tasks.synthesise_insights()

        row = RelationshipInsight.objects.get(
            relationship=self.relationship, type="perception_gap"
        )
        self.assertFalse(row.shared_with_a)
        self.assertFalse(row.shared_with_b)

    def test_one_point_apart_is_rounding_not_a_gap(self):
        """Five points is a coarse scale. A couple steadily on 5 and 4 are
        agreeing and rounding differently, and saying otherwise would invent a
        problem out of the granularity of the widget."""
        self.check_ins([5] * 8, [4] * 8)
        self.assertIsNone(detectors.perception_gap(self.relationship))

    def test_genuinely_different_places_is_a_gap(self):
        """One of them is having a good fortnight and the other is not."""
        self.check_ins([5, 4, 5, 5, 4, 5, 4, 5], [3, 2, 3, 3, 2, 3, 3, 2])
        self.assertIsNotNone(detectors.perception_gap(self.relationship))
