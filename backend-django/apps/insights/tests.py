"""What may be read out of an insight, and by whom.

The feature is unbuilt — see ``docs/relationship-insights.md`` — and these
tests exist ahead of it because the model is migrated and reachable now. An
insight is derived from what each partner said to Bliss alone, so the read path
is the whole safety story, and it was previously enforced by nothing at all:
the consent queryset was written and never attached to the model.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

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
