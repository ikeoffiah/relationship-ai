"""Tests for Bliss inside the couple thread.

The load-bearing property is that none of this can get between someone and
their own message. Most of what follows checks the failure paths, not the
happy one.
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.chat import assist
from apps.chat.models import AssistNudge, ChatAssistSettings, CoupleMessage
from apps.relationships.models import Relationship

User = get_user_model()


class AssistTestCase(TestCase):
    def setUp(self):
        self.alex = User.objects.create_user(email="a@t.local", password="pw12345!")
        self.sam = User.objects.create_user(email="s@t.local", password="pw12345!")
        self.stranger = User.objects.create_user(email="x@t.local", password="pw12345!")
        self.relationship = Relationship.objects.create(
            partner_a=self.alex, partner_b=self.sam, status="active"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.alex)

    def say(self, sender, body, **kw):
        msg = CoupleMessage(relationship=self.relationship, sender=sender, **kw)
        msg.body = body
        msg.save()
        return msg


class FailOpenTests(AssistTestCase):
    """If Bliss cannot answer, the message still sends."""

    def test_check_returns_ok_when_the_model_is_unavailable(self):
        self.say(self.sam, "hey")
        with patch("apps.chat.assist._complete", return_value=None):
            response = self.client.post(
                reverse("chat-assist-check", args=[self.relationship.id]),
                {"draft": "you always do this"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["verdict"], "ok")

    def test_check_returns_ok_when_the_model_raises(self):
        """Even an exception escaping _complete must not strand the message.

        _complete already swallows provider errors, so this exercises the outer
        guard: anything unexpected at all — a database hiccup building context,
        a future refactor — still resolves to "send it".
        """
        with patch("apps.chat.assist._complete", side_effect=Exception("boom")):
            result = assist.check_before_send(self.relationship, self.alex, "whatever")

        self.assertEqual(result["verdict"], "ok")

    def test_rephrase_survives_an_unexpected_failure(self):
        with patch("apps.chat.assist._thread_context", side_effect=Exception("db down")):
            result = assist.rephrase(self.relationship, self.alex, "hey")
        self.assertIsNone(result["suggestion"])

    def test_nudge_survives_an_unexpected_failure(self):
        with patch("apps.chat.assist._thread_context", side_effect=Exception("db down")):
            self.assertIsNone(assist.nudge_for(self.relationship, self.alex, local_hour=22))

    def test_complete_swallows_provider_failures(self):
        """_complete is the only place a provider error may surface."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "k"}):
            with patch("openai.OpenAI", side_effect=Exception("network down")):
                self.assertIsNone(assist._complete("s", "u", 1.0))

    def test_no_api_key_is_not_an_error(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(assist._complete("s", "u", 1.0))

    def test_a_caution_without_an_alternative_is_downgraded(self):
        """Flagging a message while offering nothing is just scolding."""
        parsed = assist._parse_check("VERDICT: caution\nREASON: harsh")
        self.assertEqual(parsed["verdict"], "ok")

    def test_empty_draft_never_calls_the_model(self):
        with patch("apps.chat.assist._complete") as complete:
            assist.check_before_send(self.relationship, self.alex, "   ")
        complete.assert_not_called()


class CheckTests(AssistTestCase):
    def test_caution_is_returned_with_a_usable_alternative(self):
        raw = (
            "VERDICT: caution\n"
            "REASON: reads as a sweeping accusation\n"
            "SUGGESTION: I felt unheard when that happened."
        )
        with patch("apps.chat.assist._complete", return_value=raw):
            response = self.client.post(
                reverse("chat-assist-check", args=[self.relationship.id]),
                {"draft": "you never listen"},
                format="json",
            )

        self.assertEqual(response.data["verdict"], "caution")
        self.assertEqual(response.data["reason"], "reads as a sweeping accusation")
        self.assertTrue(response.data["suggestion"])

    def test_ordinary_upset_is_not_flagged(self):
        with patch("apps.chat.assist._complete", return_value="VERDICT: ok"):
            response = self.client.post(
                reverse("chat-assist-check", args=[self.relationship.id]),
                {"draft": "I'm frustrated and I need to talk about it"},
                format="json",
            )
        self.assertEqual(response.data["verdict"], "ok")

    def test_check_is_skipped_when_interception_is_off(self):
        ChatAssistSettings.objects.create(
            relationship=self.relationship, interception_enabled=False
        )
        with patch("apps.chat.assist._complete") as complete:
            result = assist.check_before_send(self.relationship, self.alex, "you always")
        complete.assert_not_called()
        self.assertEqual(result["verdict"], "ok")

    def test_check_is_skipped_when_assist_is_off_entirely(self):
        ChatAssistSettings.objects.create(
            relationship=self.relationship, assist_enabled=False
        )
        with patch("apps.chat.assist._complete") as complete:
            assist.check_before_send(self.relationship, self.alex, "you always")
        complete.assert_not_called()


class RephraseTests(AssistTestCase):
    def test_rephrase_returns_the_suggestion(self):
        with patch("apps.chat.assist._complete", return_value="I felt hurt by that."):
            response = self.client.post(
                reverse("chat-assist-rephrase", args=[self.relationship.id]),
                {"draft": "you're impossible"},
                format="json",
            )
        self.assertEqual(response.data["suggestion"], "I felt hurt by that.")

    def test_blank_draft_is_rejected(self):
        response = self.client.post(
            reverse("chat-assist-rephrase", args=[self.relationship.id]),
            {"draft": "  "},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rephrase_is_off_when_assist_is_disabled(self):
        ChatAssistSettings.objects.create(
            relationship=self.relationship, assist_enabled=False
        )
        with patch("apps.chat.assist._complete") as complete:
            result = assist.rephrase(self.relationship, self.alex, "hey")
        complete.assert_not_called()
        self.assertIsNone(result["suggestion"])


class NudgeTests(AssistTestCase):
    def test_no_nudge_on_an_empty_thread(self):
        with patch("apps.chat.assist._complete") as complete:
            self.assertIsNone(assist.nudge_for(self.relationship, self.alex))
        complete.assert_not_called()

    def test_night_suggestion_fires_in_the_evening(self):
        self.say(self.sam, "long day")
        with patch("apps.chat.assist._complete", return_value="Glad we got through today together."):
            nudge = assist.nudge_for(self.relationship, self.alex, local_hour=22)

        self.assertIsNotNone(nudge)
        self.assertEqual(nudge.kind, AssistNudge.KIND_NIGHT)

    def test_night_suggestion_does_not_fire_at_midday(self):
        self.say(self.sam, "long day")
        with patch("apps.chat.assist._complete", return_value="NONE"):
            nudge = assist.nudge_for(self.relationship, self.alex, local_hour=13)
        self.assertIsNone(nudge)

    def test_repair_outranks_the_night_suggestion(self):
        """A warm goodnight on top of an unresolved row reads as tone-deaf."""
        self.say(self.alex, "you never listen to me")
        with patch("apps.chat.assist._complete", return_value="Can we start over tomorrow?"):
            nudge = assist.nudge_for(self.relationship, self.alex, local_hour=22)

        self.assertEqual(nudge.kind, AssistNudge.KIND_REPAIR)

    def test_opportunity_declines_when_there_is_no_opening(self):
        """The model is told to say NONE, and NONE must mean nothing shown."""
        self.say(self.sam, "ok")
        with patch("apps.chat.assist._complete", return_value="NONE"):
            self.assertIsNone(assist.nudge_for(self.relationship, self.alex, local_hour=13))
        self.assertEqual(AssistNudge.objects.count(), 0)

    def test_only_one_nudge_of_a_kind_per_day(self):
        self.say(self.sam, "stressed about the interview")
        with patch("apps.chat.assist._complete", return_value="Want to talk it through?"):
            first = assist.nudge_for(self.relationship, self.alex, local_hour=13)
            second = assist.nudge_for(self.relationship, self.alex, local_hour=13)

        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertEqual(AssistNudge.objects.count(), 1)

    def test_budget_frees_up_after_the_cooldown(self):
        self.say(self.sam, "stressed")
        AssistNudge.objects.create(
            relationship=self.relationship,
            user=self.alex,
            kind=AssistNudge.KIND_OPPORTUNITY,
            suggestion="old",
        )
        AssistNudge.objects.update(
            created_at=timezone.now() - assist.NUDGE_COOLDOWN - timedelta(minutes=1)
        )

        with patch("apps.chat.assist._complete", return_value="Want to talk it through?"):
            self.assertIsNotNone(assist.nudge_for(self.relationship, self.alex, local_hour=13))

    def test_budget_is_per_person(self):
        """One partner's nudge must not consume the other's."""
        self.say(self.sam, "stressed")
        with patch("apps.chat.assist._complete", return_value="Want to talk?"):
            assist.nudge_for(self.relationship, self.alex, local_hour=13)
            other = assist.nudge_for(self.relationship, self.sam, local_hour=13)
        self.assertIsNotNone(other)

    def test_nudges_are_off_when_assist_is_disabled(self):
        self.say(self.sam, "hi")
        ChatAssistSettings.objects.create(
            relationship=self.relationship, assist_enabled=False
        )
        with patch("apps.chat.assist._complete") as complete:
            self.assertIsNone(assist.nudge_for(self.relationship, self.alex, local_hour=22))
        complete.assert_not_called()

    def test_endpoint_ignores_a_nonsense_local_hour(self):
        self.say(self.sam, "hi")
        with patch("apps.chat.assist._complete", return_value="NONE"):
            response = self.client.get(
                reverse("chat-assist-nudge", args=[self.relationship.id]),
                {"local_hour": "99"},
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["nudge"])


class NudgeFeedbackTests(AssistTestCase):
    def make_nudge(self, user=None):
        return AssistNudge.objects.create(
            relationship=self.relationship,
            user=user or self.alex,
            kind=AssistNudge.KIND_NIGHT,
            suggestion="night",
        )

    def test_acting_on_a_nudge_is_recorded(self):
        nudge = self.make_nudge()
        self.client.post(
            reverse("chat-assist-feedback", args=[nudge.id]),
            {"action": "acted"},
            format="json",
        )
        nudge.refresh_from_db()
        self.assertIsNotNone(nudge.acted_at)

    def test_dismissal_is_recorded(self):
        nudge = self.make_nudge()
        self.client.post(
            reverse("chat-assist-feedback", args=[nudge.id]),
            {"action": "dismissed"},
            format="json",
        )
        nudge.refresh_from_db()
        self.assertIsNotNone(nudge.dismissed_at)

    def test_cannot_give_feedback_on_someone_elses_nudge(self):
        nudge = self.make_nudge(user=self.sam)
        response = self.client.post(
            reverse("chat-assist-feedback", args=[nudge.id]),
            {"action": "acted"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unknown_action_is_rejected(self):
        nudge = self.make_nudge()
        response = self.client.post(
            reverse("chat-assist-feedback", args=[nudge.id]),
            {"action": "sideways"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AssistSettingsTests(AssistTestCase):
    def test_defaults_are_on(self):
        response = self.client.get(
            reverse("chat-assist-settings", args=[self.relationship.id])
        )
        self.assertTrue(response.data["assist_enabled"])
        self.assertTrue(response.data["interception_enabled"])

    def test_either_partner_can_change_the_shared_setting(self):
        url = reverse("chat-assist-settings", args=[self.relationship.id])
        self.client.patch(url, {"interception_enabled": False}, format="json")

        self.client.force_authenticate(user=self.sam)
        response = self.client.get(url)
        self.assertFalse(response.data["interception_enabled"])
        self.assertEqual(ChatAssistSettings.objects.count(), 1)

    def test_stranger_cannot_read_or_change_settings(self):
        self.client.force_authenticate(user=self.stranger)
        url = reverse("chat-assist-settings", args=[self.relationship.id])
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.client.patch(url, {"assist_enabled": False}, format="json").status_code,
            status.HTTP_404_NOT_FOUND,
        )


class ContextTests(AssistTestCase):
    def test_context_excludes_deleted_messages(self):
        kept = self.say(self.sam, "still here")
        gone = self.say(self.sam, "deleted secret")
        gone.deleted_at = timezone.now()
        gone.ciphertext = ""
        gone.save()

        context = assist._thread_context(self.relationship)

        self.assertIn("still here", context)
        self.assertNotIn("deleted secret", context)
        self.assertIn(str(kept.sender_id), context)

    def test_context_never_crosses_into_another_thread(self):
        other = Relationship.objects.create(
            partner_a=self.stranger, partner_b=None, status="pending"
        )
        foreign = CoupleMessage(relationship=other, sender=self.stranger)
        foreign.body = "another couple's words"
        foreign.save()
        self.say(self.sam, "ours")

        self.assertNotIn("another couple", assist._thread_context(self.relationship))

    def test_sharp_exchange_detection(self):
        self.assertFalse(assist._had_sharp_exchange(self.relationship))
        self.say(self.alex, "honestly, you always do this")
        self.assertTrue(assist._had_sharp_exchange(self.relationship))

    def test_old_sharp_exchanges_do_not_count(self):
        msg = self.say(self.alex, "you always do this")
        CoupleMessage.objects.filter(id=msg.id).update(
            created_at=timezone.now() - timedelta(hours=12)
        )
        self.assertFalse(assist._had_sharp_exchange(self.relationship))


class LocalGateTests(AssistTestCase):
    """The gate decides which sends are worth a model call.

    Its recall is load-bearing: anything it skips, the model never sees. Its
    precision only costs money. So the asymmetry in these tests is deliberate —
    recall is asserted absolutely, escalation rate only loosely.
    """

    def test_gate_never_skips_a_message_that_should_flag(self):
        from apps.chat.evalset import EVAL_DRAFTS

        missed = [d for d, should in EVAL_DRAFTS if should and not assist._needs_model(d)]

        self.assertEqual(missed, [], f"gate would skip these entirely: {missed}")

    def test_gate_skips_most_ordinary_messages(self):
        """Most of what partners send each other is logistics and warmth."""
        from apps.chat.evalset import EVAL_DRAFTS

        escalated = sum(1 for d, _ in EVAL_DRAFTS if assist._needs_model(d))

        # Measured at 33%. Anything approaching 100% means the gate has stopped
        # earning its place and every send is paying for a model call again.
        self.assertLess(escalated / len(EVAL_DRAFTS), 0.6)

    def test_second_person_is_matched_on_word_boundaries(self):
        """Regression: matching "you " with a trailing space missed contempt
        whenever the word ended the sentence."""
        self.assertTrue(assist._needs_model("nobody else would put up with you"))

    def test_being_upset_is_not_enough_to_escalate(self):
        for benign in (
            "I'm really tired and I don't have it in me tonight",
            "I felt hurt when you left without saying anything",
            "I'm angry about what happened yesterday",
        ):
            self.assertFalse(assist._needs_model(benign), benign)

    def test_shouting_escalates(self):
        self.assertTrue(assist._needs_model("WHY DO I EVEN BOTHER WITH THIS"))

    def test_a_skipped_draft_never_reaches_the_model(self):
        with patch("apps.chat.assist._complete") as complete:
            result = assist.check_before_send(self.relationship, self.alex, "ok see you at 7")
        complete.assert_not_called()
        self.assertEqual(result["verdict"], "ok")


class VerdictCacheTests(AssistTestCase):
    """The client checks on a typing pause and again on send; the second call
    must not pay for the first's answer."""

    def setUp(self):
        super().setUp()
        from django.core.cache import cache

        cache.clear()

    def test_repeat_check_of_the_same_draft_hits_the_cache(self):
        draft = "you never listen and you always do this"
        raw = "VERDICT: caution\nREASON: sweeping\nSUGGESTION: I felt unheard."

        with patch("apps.chat.assist._complete", return_value=raw) as complete:
            first = assist.check_before_send(self.relationship, self.alex, draft)
            second = assist.check_before_send(self.relationship, self.alex, draft)

        self.assertEqual(complete.call_count, 1)
        self.assertEqual(first, second)

    def test_editing_the_draft_re_checks(self):
        raw = "VERDICT: ok"
        with patch("apps.chat.assist._complete", return_value=raw) as complete:
            assist.check_before_send(self.relationship, self.alex, "you always do this")
            assist.check_before_send(self.relationship, self.alex, "you always do that")
        self.assertEqual(complete.call_count, 2)

    def test_cache_is_scoped_per_couple(self):
        """One couple's verdict must never resolve another's draft."""
        other = Relationship.objects.create(
            partner_a=self.stranger, partner_b=None, status="pending"
        )
        draft = "you never listen and you always do this"
        with patch("apps.chat.assist._complete", return_value="VERDICT: ok") as complete:
            assist.check_before_send(self.relationship, self.alex, draft)
            assist.check_before_send(other, self.stranger, draft)
        self.assertEqual(complete.call_count, 2)
