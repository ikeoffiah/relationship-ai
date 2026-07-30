"""The remaining branches in Bliss's in-thread coaching.

Mostly failure paths and the parts of the contempt heuristic that only fire on
input nobody types by hand. The heuristic ones matter more than they look: this
is the machinery that decides whether to interrupt someone mid-argument, and a
false positive there is its own small harm.
"""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.chat import assist
from apps.chat.models import AssistNudge, ChatAssistSettings, CoupleMessage
from apps.relationships.models import Relationship

User = get_user_model()


class ClientTests(TestCase):
    def test_the_client_is_built_once_and_reused(self):
        assist._client = None
        self.addCleanup(lambda: setattr(assist, "_client", None))

        with patch.dict("os.environ", {"OPENAI_API_KEY": "k"}), patch(
            "openai.OpenAI"
        ) as ctor:
            first = assist._get_client()
            second = assist._get_client()

        # A client per call meant a fresh TLS handshake every time.
        self.assertIs(first, second)
        ctor.assert_called_once()


class CompletionTests(TestCase):
    def test_no_api_key_means_no_opinion(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(assist._complete("sys", "user", timeout=1.0))

    def test_an_upstream_failure_is_no_opinion_rather_than_an_error(self):
        client = MagicMock()
        client.with_options.return_value.chat.completions.create.side_effect = (
            RuntimeError("timeout")
        )

        with patch.dict("os.environ", {"OPENAI_API_KEY": "k"}), patch(
            "apps.chat.assist._get_client", return_value=client
        ):
            self.assertIsNone(assist._complete("sys", "user", timeout=1.0))

    def test_a_response_with_no_content_is_empty_not_none(self):
        response = MagicMock()
        response.choices[0].message.content = None
        client = MagicMock()
        client.with_options.return_value.chat.completions.create.return_value = response

        with patch.dict("os.environ", {"OPENAI_API_KEY": "k"}), patch(
            "apps.chat.assist._get_client", return_value=client
        ):
            self.assertEqual(assist._complete("sys", "user", timeout=1.0), "")


class ContemptHeuristicTests(TestCase):
    """The pre-send check. A false positive interrupts a real conversation."""

    def test_sustained_shouting_at_length_is_caution(self):
        self.assertTrue(assist._needs_model("WHY DO YOU NEVER LISTEN TO ME"))

    def test_a_short_shout_is_not(self):
        # "OK!" and "YES" are not contempt, and treating them as such would
        # make the feature feel like a censor.
        self.assertFalse(assist._needs_model("OK FINE"))

    def test_three_exclamations_aimed_at_someone_is_caution(self):
        self.assertTrue(assist._needs_model("you did it again!!!"))

    def test_three_exclamations_with_no_target_are_not(self):
        # "I got the job!!!" is by far the commonest form.
        self.assertFalse(assist._needs_model("I got the job!!!"))

    def test_an_absolute_aimed_at_someone_is_caution(self):
        self.assertTrue(assist._needs_model("you always do this"))

    def test_a_negative_word_aimed_at_someone_is_caution(self):
        # Second person plus a blaming word, and deliberately no "always" or
        # "never" — this has to be the negative-word branch rather than the
        # absolute-marker one above it.
        self.assertTrue(assist._needs_model("this is your fault"))

    def test_the_same_word_with_no_target_is_not(self):
        self.assertFalse(assist._needs_model("the traffic was the worst"))

    def test_ordinary_disagreement_passes(self):
        self.assertFalse(assist._needs_model("I see it differently"))


class PartnerNotesTests(TestCase):
    def setUp(self):
        self.alex = User.objects.create_user(email="a@test.local", password="pw12345!")
        self.sam = User.objects.create_user(email="s@test.local", password="pw12345!")
        self.relationship = Relationship.objects.create(
            partner_a=self.alex, partner_b=self.sam, status="active"
        )

    def test_a_missing_personalization_app_degrades_to_nothing(self):
        with patch(
            "apps.personalization.models.UserProfile.objects.filter",
            side_effect=RuntimeError("table gone"),
        ):
            self.assertEqual(assist._partner_notes(self.relationship, self.alex), "")

    def test_no_profile_means_no_notes(self):
        with patch(
            "apps.personalization.models.UserProfile.objects.filter"
        ) as filter_mock:
            filter_mock.return_value.first.return_value = None
            self.assertEqual(assist._partner_notes(self.relationship, self.alex), "")

    def test_a_profile_contributes_style_notes(self):
        profile = MagicMock()
        profile.attachment_style = "anxious"
        profile.communication_style_preference = "direct"

        with patch(
            "apps.personalization.models.UserProfile.objects.filter"
        ) as filter_mock, patch(
            "apps.personalization.behaviour.guidance_for", return_value=["goes quiet"]
        ):
            filter_mock.return_value.first.return_value = profile
            notes = assist._partner_notes(self.relationship, self.alex)

        self.assertIn("attachment style: anxious", notes)
        self.assertIn("prefers direct communication", notes)
        # Phrased as an observable, never as a label.
        self.assertIn("goes quiet", notes)

    def test_a_behaviour_lookup_failure_leaves_the_rest_intact(self):
        profile = MagicMock()
        profile.attachment_style = "secure"
        profile.communication_style_preference = ""

        with patch(
            "apps.personalization.models.UserProfile.objects.filter"
        ) as filter_mock, patch(
            "apps.personalization.behaviour.guidance_for",
            side_effect=RuntimeError("no module"),
        ):
            filter_mock.return_value.first.return_value = profile
            notes = assist._partner_notes(self.relationship, self.alex)

        self.assertEqual(notes, "attachment style: secure")


class AssistFailureTests(TestCase):
    def setUp(self):
        self.alex = User.objects.create_user(email="a@test.local", password="pw12345!")
        self.sam = User.objects.create_user(email="s@test.local", password="pw12345!")
        self.relationship = Relationship.objects.create(
            partner_a=self.alex, partner_b=self.sam, status="active"
        )

    def test_an_empty_draft_is_never_rephrased(self):
        self.assertIsNone(assist.rephrase(self.relationship, self.alex, "  ")["suggestion"])

    def test_the_check_fails_open(self):
        """A broken check must not stop someone sending a message.

        Failing closed here would mean an outage silently blocks the thread,
        which is a worse and more certain harm than missing one caution.
        """
        with patch(
            "apps.chat.assist.settings_for", side_effect=RuntimeError("db down")
        ):
            verdict = assist.check_before_send(self.relationship, self.alex, "you always do this")

        self.assertEqual(verdict["verdict"], "ok")

    def test_an_empty_incoming_message_gets_no_read_coaching(self):
        result = assist.coach_response(self.relationship, self.alex, "   ")
        self.assertIsNone(result["guidance"])
        self.assertFalse(result["defer_to_support"])


class NudgeBranchTests(TestCase):
    def setUp(self):
        self.alex = User.objects.create_user(email="a@test.local", password="pw12345!")
        self.sam = User.objects.create_user(email="s@test.local", password="pw12345!")
        self.relationship = Relationship.objects.create(
            partner_a=self.alex, partner_b=self.sam, status="active"
        )
        ChatAssistSettings.objects.update_or_create(
            relationship=self.relationship,
            defaults={"assist_enabled": True, "night_nudge_enabled": True},
        )

    def _message(self, sender, body):
        message = CoupleMessage(relationship=self.relationship, sender=sender)
        message.body = body
        message.save()
        return message

    def test_a_repair_opening_that_the_model_declines_produces_nothing(self):
        self._message(self.alex, "that was harsh, sorry")

        with patch("apps.chat.assist._had_sharp_exchange", return_value=True), patch(
            "apps.chat.assist._complete", return_value=None
        ):
            nudge = assist.nudge_for(self.relationship, self.alex, local_hour=14)

        # No suggestion means no nudge, rather than an empty card — and it stops
        # here rather than falling through to offer an end-of-day one instead.
        self.assertIsNone(nudge)
        self.assertFalse(AssistNudge.objects.exists())

    def test_a_repair_nudge_is_created_after_a_sharp_exchange(self):
        self._message(self.alex, "that came out wrong")

        with patch("apps.chat.assist._had_sharp_exchange", return_value=True), patch(
            "apps.chat.assist._complete", return_value="tell them what you needed"
        ):
            nudge = assist.nudge_for(self.relationship, self.alex, local_hour=14)

        self.assertIsNotNone(nudge)
        self.assertEqual(nudge.kind, AssistNudge.KIND_REPAIR)
        self.assertEqual(nudge.suggestion, "tell them what you needed")

    def test_an_end_of_day_nudge_that_the_model_declines_produces_nothing(self):
        self._message(self.sam, "long day")

        with patch("apps.chat.assist._complete", return_value=None):
            nudge = assist.nudge_for(self.relationship, self.alex, local_hour=22)

        self.assertIsNone(nudge)
