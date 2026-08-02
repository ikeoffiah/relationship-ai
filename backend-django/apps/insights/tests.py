"""What may be read out of an insight, and by whom.

The feature is unbuilt — see ``docs/relationship-insights.md`` — and these
tests exist ahead of it because the model is migrated and reachable now. An
insight is derived from what each partner said to Bliss alone, so the read path
is the whole safety story, and it was previously enforced by nothing at all:
the consent queryset was written and never attached to the model.
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
