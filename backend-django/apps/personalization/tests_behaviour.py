"""The behavioural profile.

Most of these are negative tests, because the risks here are all in the
direction of the feature saying too much: acting on thin evidence, holding a
grudge past the point the evidence supports, letting one partner read the
other, or hardening an observation into a label.
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.personalization import behaviour
from apps.personalization.models import BehaviourProfile

User = get_user_model()


class BehaviourProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="obs@t.local", password="pw12345!")

    def observe_n(self, signal, n, user=None):
        for _ in range(n):
            behaviour.observe(user or self.user, signal)

    def backdate(self, days, user=None):
        """Age every stored signal by `days`, as if nothing had happened since."""
        profile = BehaviourProfile.objects.get(user=user or self.user)
        then = (timezone.now() - timedelta(days=days)).isoformat()
        profile.signals = {
            key: {**entry, "updated_at": then} for key, entry in profile.signals.items()
        }
        profile.save()

    # ── Evidence thresholds ──────────────────────────────────────────────

    def test_one_observation_says_nothing(self):
        """The single most important property. A person who was short once is
        not 'someone who escalates', and guidance built on one bad evening is
        guidance that is wrong about them."""
        behaviour.observe(self.user, behaviour.ESCALATES)
        self.assertEqual(behaviour.tendencies_for(self.user.id), [])

    def test_below_the_observation_floor_says_nothing(self):
        self.observe_n(behaviour.ESCALATES, behaviour.MIN_OBSERVATIONS - 1)
        self.assertEqual(behaviour.tendencies_for(self.user.id), [])

    def test_a_repeated_pattern_is_recognised(self):
        self.observe_n(behaviour.ESCALATES, behaviour.MIN_OBSERVATIONS)
        self.assertIn(behaviour.ESCALATES, behaviour.tendencies_for(self.user.id))

    def test_an_unknown_signal_is_ignored_rather_than_stored(self):
        behaviour.observe(self.user, "is_a_bad_person")
        self.assertFalse(BehaviourProfile.objects.filter(user=self.user).exists())

    # ── Decay ────────────────────────────────────────────────────────────

    def test_a_pattern_fades_when_it_stops(self):
        """Three months of nothing should not still be read as a tendency. A
        bad fortnight during a bereavement must not define someone later."""
        self.observe_n(behaviour.WITHDRAWS, 8)
        self.assertIn(behaviour.WITHDRAWS, behaviour.tendencies_for(self.user.id))

        self.backdate(days=90)
        self.assertEqual(behaviour.tendencies_for(self.user.id), [])

    def test_one_half_life_halves_the_score(self):
        self.observe_n(behaviour.REPAIRS, 4)
        before = BehaviourProfile.objects.get(user=self.user).signals[behaviour.REPAIRS]["score"]

        self.backdate(days=behaviour.HALF_LIFE_DAYS)
        behaviour.observe(self.user, behaviour.REPAIRS)
        after = BehaviourProfile.objects.get(user=self.user).signals[behaviour.REPAIRS]["score"]

        # The new observation adds its own weight (1.0 by default; the 1.5 lives
        # in note_repair, not in observe) on top of the halved total.
        self.assertAlmostEqual(after, before / 2 + 1.0, places=2)

    def test_a_repair_counts_for_more_than_an_ordinary_observation(self):
        """Weighted up deliberately: a repair sticker is the least ambiguous
        gesture in the product, where a caution is an inference."""
        behaviour.note_repair(self.user)
        behaviour.observe(self.user, behaviour.ESCALATES)
        signals = BehaviourProfile.objects.get(user=self.user).signals
        self.assertGreater(
            signals[behaviour.REPAIRS]["score"], signals[behaviour.ESCALATES]["score"]
        )

    def test_a_faded_pattern_revives_on_new_evidence(self):
        self.observe_n(behaviour.PURSUES, 6)
        self.backdate(days=120)
        self.assertEqual(behaviour.tendencies_for(self.user.id), [])

        self.observe_n(behaviour.PURSUES, 3)
        self.assertIn(behaviour.PURSUES, behaviour.tendencies_for(self.user.id))

    # ── Coherence ────────────────────────────────────────────────────────

    def test_withdrawing_and_pursuing_do_not_both_win(self):
        """They are the two halves of demand-withdraw. Reporting both gives
        Bliss contradictory instructions — leave them space, and answer them
        quickly — so only the stronger survives."""
        self.observe_n(behaviour.WITHDRAWS, 10)
        self.observe_n(behaviour.PURSUES, 4)

        tendencies = behaviour.tendencies_for(self.user.id)
        self.assertIn(behaviour.WITHDRAWS, tendencies)
        self.assertNotIn(behaviour.PURSUES, tendencies)

    def test_the_stronger_of_the_pair_is_the_one_kept(self):
        self.observe_n(behaviour.PURSUES, 10)
        self.observe_n(behaviour.WITHDRAWS, 4)
        self.assertIn(behaviour.PURSUES, behaviour.tendencies_for(self.user.id))

    # ── What comes out ───────────────────────────────────────────────────

    def test_guidance_describes_behaviour_and_never_diagnoses(self):
        """The line this feature must not cross. 'Goes quiet when things get
        sharp' is an observation; 'avoidant' is a clinical label we are not
        qualified to apply and cannot support from chat timings."""
        labels = (
            "avoidant",
            "anxious",
            "secure",
            "disorganised",
            "disorganized",
            "narcissist",
            "toxic",
            "abusive",
            "codependent",
        )
        for text in list(behaviour.GUIDANCE.values()) + list(
            behaviour.SELF_DESCRIPTION.values()
        ):
            for label in labels:
                self.assertNotIn(label, text.lower(), f"{label!r} appears in {text!r}")

    def test_every_signal_has_both_phrasings(self):
        for signal in behaviour.SIGNALS:
            self.assertIn(signal, behaviour.GUIDANCE)
            self.assertIn(signal, behaviour.SELF_DESCRIPTION)

    def test_self_descriptions_are_hedged_to_the_recent_past(self):
        """The scores decay, so a claim about someone's character would be a
        claim the data does not support."""
        for signal, text in behaviour.SELF_DESCRIPTION.items():
            if signal == behaviour.ACCEPTS_HELP:
                continue  # not a pattern over time, so not hedged
            self.assertIn("lately", text.lower(), text)

    def test_an_unknown_user_yields_nothing_rather_than_failing(self):
        import uuid

        self.assertEqual(behaviour.tendencies_for(uuid.uuid4()), [])

    # ── Never in the way ─────────────────────────────────────────────────

    def test_a_broken_write_is_swallowed(self):
        """This runs on the same request as somebody's message. A lost
        observation costs a staler profile; a raised exception costs a send."""
        with patch.object(
            BehaviourProfile.objects, "get_or_create", side_effect=RuntimeError("boom")
        ):
            behaviour.observe(self.user, behaviour.REPAIRS)  # must not raise


class BehaviourPrivacyTests(TestCase):
    """Who can read what. The whole design rests on this."""

    def setUp(self):
        self.alex = User.objects.create_user(email="alex-b@t.local", password="pw12345!")
        self.sam = User.objects.create_user(email="sam-b@t.local", password="pw12345!")
        for _ in range(6):
            behaviour.observe(self.sam, behaviour.WITHDRAWS)
        self.client = APIClient()
        self.url = reverse("personalization-behaviour")

    def test_the_endpoint_returns_your_own_observations(self):
        self.client.force_authenticate(user=self.sam)
        body = self.client.get(self.url).json()
        self.assertTrue(body["observations"])
        self.assertIn("lately", body["observations"][0].lower())

    def test_you_cannot_reach_your_partners(self):
        """There is no id parameter to pass, so this is less a check than a
        demonstration: Alex asking gets Alex's answer, and Sam's row is not
        addressable from the API at all."""
        self.client.force_authenticate(user=self.alex)
        self.assertEqual(self.client.get(self.url).json()["observations"], [])

    def test_it_requires_authentication(self):
        self.assertIn(self.client.get(self.url).status_code, (401, 403))

    def test_no_scores_or_signal_keys_leak_through_the_api(self):
        """Only plain language comes out. A number invites comparison and a
        raw key ('withdraws_after_conflict') invites being read as a verdict."""
        self.client.force_authenticate(user=self.sam)
        body = self.client.get(self.url).json()
        rendered = str(body)
        for signal in behaviour.SIGNALS:
            self.assertNotIn(signal, rendered)
        self.assertNotIn("score", rendered)
