"""Tests for Bliss inside the couple thread.

The load-bearing property is that none of this can get between someone and
their own message. Most of what follows checks the failure paths, not the
happy one.
"""

import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.chat import assist
from apps.chat.models import AssistNudge, ChatAssistSettings, CoupleMessage, MessageMedia
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


class RollingSummaryTests(AssistTestCase):
    """Long-arc context at a fixed token cost — and never on the send path."""

    def test_summary_is_prepended_to_context(self):
        from apps.chat.models import ThreadSummary

        self.say(self.sam, "see you tonight")
        ThreadSummary.objects.create(
            relationship=self.relationship,
            summary="Recurring tension about in-laws; both tired lately.",
            covered_message_count=1,
        )

        context = assist._thread_context(self.relationship)

        self.assertIn("Recurring tension about in-laws", context)
        self.assertIn("see you tonight", context)
        # Background first, then the verbatim tail.
        self.assertLess(context.index("Recurring tension"), context.index("see you tonight"))

    def test_context_works_without_a_summary(self):
        self.say(self.sam, "just the tail")
        self.assertEqual(assist._thread_context(self.relationship).count("\n"), 0)

    def test_summarising_never_happens_on_the_send_path(self):
        """The check reads an already-written summary; it must not generate one."""
        from apps.chat.models import ThreadSummary

        ThreadSummary.objects.create(
            relationship=self.relationship, summary="background", covered_message_count=1
        )
        self.say(self.sam, "hi")

        with patch("apps.chat.assist._complete", return_value="VERDICT: ok") as complete:
            assist.check_before_send(self.relationship, self.alex, "you always do this")

        # Exactly one call: the check itself. No summarisation round-trip.
        self.assertEqual(complete.call_count, 1)

    def test_staleness_triggers_only_after_enough_new_messages(self):
        from apps.chat.tasks import REFRESH_EVERY_MESSAGES, summary_is_stale

        self.say(self.sam, "one")
        self.assertFalse(summary_is_stale(self.relationship))

        for i in range(REFRESH_EVERY_MESSAGES):
            self.say(self.sam, f"m{i}")
        self.assertTrue(summary_is_stale(self.relationship))

    def test_send_still_succeeds_when_the_broker_is_down(self):
        with patch(
            "apps.chat.tasks.refresh_thread_summary.delay", side_effect=Exception("no broker")
        ):
            with patch("apps.chat.tasks.summary_is_stale", return_value=True):
                response = self.client.post(
                    reverse("chat-send", args=[self.relationship.id]),
                    {"body": "hello"},
                    format="json",
                )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class ReadCoachTests(AssistTestCase):
    """Guidance for the partner receiving something hard.

    The failure mode that matters here is not a bad suggestion — it is the
    assistant taking a side. An AI that privately tells one partner the other
    is the problem has made itself a third party inside a two-person system.
    """

    def url(self):
        return reverse("chat-assist-read-coach", args=[self.relationship.id])

    def coach_on(self, body, **kw):
        """Ask, as Alex, about a message Sam just sent."""
        message = self.say(self.sam, body, **kw)
        return self.client.post(self.url(), {"message_id": str(message.id)}, format="json")

    def test_guidance_is_returned_for_a_hard_message(self):
        with patch(
            "apps.chat.assist._complete",
            return_value="Take a breath before answering — you can name the "
            "part that stung without matching it.",
        ):
            response = self.coach_on("you never listen, you always do this")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Take a breath", response.data["guidance"])
        self.assertFalse(response.data["defer_to_support"])

    def test_abuse_signals_defer_to_support_instead_of_coaching(self):
        """Coaching someone to respond 'better' to coercive control would be
        coaching them to accommodate it."""
        with patch("apps.chat.assist._complete") as complete:
            response = self.coach_on("you're not allowed to see your friends this weekend")

        self.assertTrue(response.data["defer_to_support"])
        self.assertIsNone(response.data["guidance"])
        # And crucially, no "here's how to respond" was ever generated.
        complete.assert_not_called()

    def test_threats_defer_to_support(self):
        with patch("apps.chat.assist._complete") as complete:
            response = self.coach_on("if you leave I'll take the kids")
        self.assertTrue(response.data["defer_to_support"])
        complete.assert_not_called()

    def test_an_ordinary_message_gets_no_coaching(self):
        with patch("apps.chat.assist._complete") as complete:
            response = self.coach_on("can you grab milk on the way home?")
        self.assertIsNone(response.data["guidance"])
        complete.assert_not_called()

    def test_model_saying_NONE_shows_nothing(self):
        with patch("apps.chat.assist._complete", return_value="NONE"):
            response = self.coach_on("you always do this")
        self.assertIsNone(response.data["guidance"])

    def test_coaching_fails_open_and_silent(self):
        with patch("apps.chat.assist._complete", side_effect=Exception("down")):
            response = self.coach_on("you always do this")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["guidance"])

    # ── who may ask, and about what ─────────────────────────────────────────

    def test_the_sender_is_not_coached_on_their_own_message(self):
        """The endpoint's contract is guidance for the partner who *received*
        this. Asking about your own message is outside it.

        Not a leak — the guidance is built from this text and the shared
        thread, never from Sam's profile, so an answer would give away nothing
        of theirs. It is that someone who has just said a hard thing should not
        be able to discover that the system stepped in to help their partner
        handle it, and that the endpoint should know who sent what rather than
        trusting the client to only ask about messages it received.
        """
        mine = self.say(self.alex, "you never listen, you always do this")
        with patch("apps.chat.assist._complete") as complete:
            response = self.client.post(
                self.url(), {"message_id": str(mine.id)}, format="json"
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["guidance"])
        self.assertFalse(response.data["defer_to_support"])
        complete.assert_not_called()

    def test_a_message_from_another_couples_thread_is_a_404(self):
        other = Relationship.objects.create(
            partner_a=self.sam, partner_b=self.stranger, status="active"
        )
        elsewhere = CoupleMessage(relationship=other, sender=self.stranger)
        elsewhere.body = "you always do this"
        elsewhere.save()

        with patch("apps.chat.assist._complete") as complete:
            response = self.client.post(
                self.url(), {"message_id": str(elsewhere.id)}, format="json"
            )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        complete.assert_not_called()

    def test_an_unknown_or_malformed_id_is_a_404_not_a_500(self):
        """The id arrives in a JSON body, so it is whatever the caller typed."""
        for message_id in ("11111111-1111-1111-1111-111111111111", "not-a-uuid", "", 7, None):
            with patch("apps.chat.assist._complete") as complete:
                response = self.client.post(
                    self.url(), {"message_id": message_id}, format="json"
                )
            self.assertEqual(
                response.status_code, status.HTTP_404_NOT_FOUND, repr(message_id)
            )
            complete.assert_not_called()

    def test_a_voice_note_is_coached_on_its_transcript(self):
        """The text of a spoken message lives on the media row.

        Reading it from the row rather than the request body is most of the
        point of taking an id: a caller passing a string would never have found
        this, so voice — where the loaded messages go — was uncoachable.
        """
        media = MessageMedia.objects.create(
            relationship=self.relationship,
            uploader=self.sam,
            kind=MessageMedia.KIND_VOICE,
            storage_key="k",
            byte_size=1,
        )
        media.transcript = "you never listen, you always do this"
        media.save(update_fields=["transcript_ciphertext"])
        voice = self.say(self.sam, "", kind=CoupleMessage.KIND_VOICE, media=media)

        with patch("apps.chat.assist._complete", return_value="Take a breath.") as complete:
            response = self.client.post(
                self.url(), {"message_id": str(voice.id)}, format="json"
            )

        self.assertEqual(response.data["guidance"], "Take a breath.")
        self.assertIn("you always do this", complete.call_args.args[1])

    def test_the_deprecated_free_text_body_still_answers(self):
        """One release of overlap for a client that has not shipped the id yet.

        Delete this test with the branch it covers.
        """
        with patch("apps.chat.assist._complete", return_value="Take a breath."):
            response = self.client.post(
                self.url(), {"message": "you always do this"}, format="json"
            )
        self.assertEqual(response.data["guidance"], "Take a breath.")

    def test_disabled_assist_means_no_coaching(self):
        ChatAssistSettings.objects.create(
            relationship=self.relationship, assist_enabled=False
        )
        with patch("apps.chat.assist._complete") as complete:
            result = assist.coach_response(self.relationship, self.alex, "you always do this")
        complete.assert_not_called()
        self.assertIsNone(result["guidance"])

    def test_a_stranger_cannot_request_coaching_on_this_thread(self):
        theirs = self.say(self.sam, "you always do this")
        self.client.force_authenticate(user=self.stranger)
        response = self.client.post(
            self.url(), {"message_id": str(theirs.id)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_the_prompt_forbids_characterising_the_partner(self):
        """The instruction is the guardrail; pin it so it cannot be softened."""
        system = assist._READ_COACH_SYSTEM.lower()
        self.assertIn("never diagnose, label or characterise the partner", system)
        self.assertIn("never take the reader's side", system)


class ContemptVocabularyTests(AssistTestCase):
    """The expanded gate vocabulary.

    Recall is asserted absolutely; escalation rate only loosely. A term that
    over-triggers costs one cheap call the model then clears — a term that is
    missing means the model never sees that message at all.
    """

    def test_contempt_the_original_list_missed(self):
        for draft in (
            "oh please, spare me the drama queen act",
            "here we go again, why am I not surprised",
            "you're just like your mother and you'll never change",
            "wow just wow. cry me a river",
            "that never happened, you're imagining things again",
            "fuck you, I'm not doing this",
            "what a joke. absolutely pathetic",
            "don't talk to me, leave me alone",
        ):
            self.assertTrue(assist._needs_model(draft), draft)

    def test_strong_terms_fire_without_a_target(self):
        """Nobody calls the traffic a worthless bastard and means it kindly."""
        self.assertTrue(assist._needs_model("this is pathetic"))

    def test_contextual_terms_need_someone_to_aim_at(self):
        """'That show was ridiculous' is an ordinary sentence."""
        self.assertFalse(assist._needs_model("that show was ridiculous, I laughed"))
        self.assertFalse(assist._needs_model("this traffic is absolutely disgusting"))
        # ...but the same word aimed at a partner does escalate.
        self.assertTrue(assist._needs_model("you are being ridiculous"))

    def test_never_mind_is_not_treated_as_stonewalling(self):
        """Far more often a benign correction. Real stonewalling keeps its
        other markers, which are still in the list."""
        self.assertFalse(assist._needs_model("never mind, I found my keys"))
        self.assertTrue(assist._needs_model("forget it, I'm done talking"))

    def test_word_boundaries_prevent_substring_false_fires(self):
        for benign in ("I need to buy pigment for the wall", "let us assume the best"):
            self.assertFalse(assist._needs_model(benign), benign)

    def test_recall_is_total_across_the_eval_set(self):
        from apps.chat.evalset import EVAL_DRAFTS

        missed = [d for d, should in EVAL_DRAFTS if should and not assist._needs_model(d)]
        self.assertEqual(missed, [], f"gate would skip these entirely: {missed}")

    def test_expanding_the_vocabulary_did_not_wreck_the_escalation_rate(self):
        from apps.chat.evalset import EVAL_DRAFTS

        escalated = sum(1 for d, _ in EVAL_DRAFTS if assist._needs_model(d))
        # Measured at 46% on a set deliberately loaded with hard cases; real
        # traffic skews far more benign. Anywhere near 100% means the tiering
        # has stopped earning its place.
        self.assertLess(escalated / len(EVAL_DRAFTS), 0.7)


class RegisterTests(AssistTestCase):
    """Sharpness is couple-relative, so the caution calibrates per register.

    The disqualifiers carry the weight here. What makes this safe to ship is
    not that it recognises a joke — it is that nothing a couple teaches it can
    reach the patterns the check exists for.
    """

    def test_emoji_and_laughter_read_as_playful(self):
        for draft in (
            "you're the worst 😂",
            "I hate you so much right now 😂😂",
            "you're ridiculous lol",
            "stop it haha",
            "get out of here :)",
        ):
            self.assertEqual(assist.register_of(draft), assist.REGISTER_PLAYFUL, draft)

    def test_plain_sharpness_is_plain(self):
        for draft in (
            "you never follow through on anything",
            "I'm annoyed about it, honestly",
            "can you grab milk on the way home",
        ):
            self.assertEqual(assist.register_of(draft), assist.REGISTER_PLAIN, draft)

    def test_an_emoji_cannot_relabel_name_calling(self):
        """Otherwise a couple could calibrate away the whole vocabulary by
        appending a laugh to it."""
        for draft in (
            "you are an idiot 😂",
            "you're pathetic lol",
            "you always do this and I'm sick of it 😂",
            "you never listen haha",
            "I'm done, watch me 😂",
        ):
            self.assertEqual(assist.register_of(draft), assist.REGISTER_PLAIN, draft)

    def test_absolutes_only_disqualify_when_aimed_at_the_partner(self):
        """"I never sleep well 😂" is not an accusation."""
        self.assertEqual(
            assist.register_of("I never sleep well before a flight 😂"),
            assist.REGISTER_PLAYFUL,
        )


class CautionCalibrationTests(AssistTestCase):
    """What a couple teaches the caution, and what it may not reach."""

    def outcome(self, choice, draft=None):
        body = {"choice": choice}
        if draft is not None:
            body["draft"] = draft
        return self.client.post(
            reverse("chat-assist-caution-outcome", args=[self.relationship.id]),
            body,
            format="json",
        )

    def weights(self):
        from apps.personalization.models import CouplePolicy

        policy = CouplePolicy.objects.filter(relationship=self.relationship).first()
        return policy.weights if policy else {}

    def test_a_draft_files_the_lesson_under_its_register(self):
        for _ in range(5):
            self.assertEqual(self.outcome("sent_anyway", "you're the worst 😂").status_code, 200)
        self.assertIn("caution@playful", self.weights())
        self.assertNotIn("caution", self.weights())

    def test_overriding_on_banter_does_not_quieten_plain_sharpness(self):
        for _ in range(5):
            self.outcome("sent_anyway", "you're the worst 😂")
        self.assertFalse(assist._caution_is_wanted(self.relationship, "playful"))
        self.assertTrue(assist._caution_is_wanted(self.relationship, "plain"))

    def test_an_outcome_without_a_draft_still_quietens_everything(self):
        """The shape a client that has not shipped register reporting sends —
        which is every client today, since mobile does not call this at all."""
        for _ in range(5):
            self.assertEqual(self.outcome("sent_anyway").status_code, 200)
        self.assertIn("caution", self.weights())
        for register in ("playful", "plain", None):
            self.assertFalse(assist._caution_is_wanted(self.relationship, register), register)

    def test_a_lesson_taught_before_registers_existed_keeps_applying(self):
        """The write-here/read-there bug took this loop out once. Reading only
        the register key would have done it again, silently, to every couple
        who had already told us something."""
        from apps.personalization import outcomes

        for _ in range(5):
            outcomes.record(self.relationship, "caution", None, "declined")
        self.assertFalse(assist._caution_is_wanted(self.relationship, "playful"))

    def test_the_draft_is_not_stored(self):
        self.outcome("sent_anyway", "you're the worst 😂")
        self.assertNotIn("worst", json.dumps(self.weights()))

    def test_check_before_send_consults_the_register(self):
        for _ in range(5):
            self.outcome("sent_anyway", "you're the worst 😂")
        with patch.object(assist, "_complete") as complete:
            verdict = assist.check_before_send(self.relationship, self.alex, "you're the worst 😂")
        self.assertEqual(verdict["verdict"], "ok")
        complete.assert_not_called()


class ReadCoachingGateTests(AssistTestCase):
    """Who gets offered help receiving a message, and who is left alone.

    This gate has been wrong in both directions. It was once the send-side
    contempt vocabulary alone, so it fired on "you always do this" — unpleasant
    but survivable — and stayed silent on "I don't know if I want to keep doing
    this", which is the hardest thing a partner can open with. Then, once
    withdrawal was added, it still inherited the send-side gate and so coached
    the receiver of a joke on handling being hurt.
    """

    def test_withdrawal_always_wins(self):
        """Nothing may talk this out of firing — not an emoji, not anything."""
        for incoming in (
            "I don't know if I want to keep doing this",
            "I don't know if I want to keep doing this 😞",
            "I'm so tired of trying lol",
        ):
            self.assertTrue(assist._needs_read_coaching(incoming), incoming)

    def test_playful_sharpness_is_left_alone(self):
        """Telling someone their partner may have hurt them, when their partner
        was playing, does the harm the message did not."""
        for incoming in (
            "you're the worst 😂",
            "I hate you so much right now 😂😂",
            "you're such a menace lol",
        ):
            self.assertFalse(assist._needs_read_coaching(incoming), incoming)

    def test_plain_sharpness_still_offers_help(self):
        for incoming in (
            "you always do this and I'm sick of it",
            "you are pathetic",
        ):
            self.assertTrue(assist._needs_read_coaching(incoming), incoming)

    def test_an_emoji_does_not_silence_coaching_on_real_contempt(self):
        """`register_of` refuses to call name-calling or absolutes playful, so
        the bypass cannot be opened with a laugh."""
        for incoming in (
            "you are an idiot 😂",
            "you always do this and I'm sick of it 😂",
        ):
            self.assertTrue(assist._needs_read_coaching(incoming), incoming)

    def test_abuse_routing_does_not_run_through_this_gate(self):
        """Safety is checked before it, so nothing here can suppress a
        referral — including for a disclosure with a laugh in it."""
        result = assist.coach_response(
            self.relationship, self.sam, "I went through your phone last night 😂"
        )
        self.assertTrue(result["defer_to_support"])
        self.assertIsNone(result["guidance"])


class CoachingReplyParsingTests(AssistTestCase):
    """A refusal to comment must not be rendered to somebody as comment."""

    def parse(self, raw):
        return assist._parse_coaching(raw)

    def test_the_labelled_no(self):
        self.assertIsNone(self.parse("NEEDED: no"))

    def test_the_labelled_yes(self):
        self.assertEqual(
            self.parse("NEEDED: yes\nGUIDANCE: Take a breath and say what is true."),
            "Take a breath and say what is true.",
        )

    def test_declining_in_prose_is_still_a_decline(self):
        """The failure the sentinel could not see: the model says no help is
        needed, in a sentence, and the old code showed that sentence as help."""
        self.assertIsNone(
            self.parse("NEEDED: no\nThis seems playful and teasing, so no help is needed.")
        )

    def test_the_old_sentinel_is_still_understood(self):
        for raw in ("NONE", "none", "  NONE  "):
            self.assertIsNone(self.parse(raw), raw)

    def test_a_model_that_ignores_the_format_is_taken_at_its_word(self):
        self.assertEqual(
            self.parse("Take a moment before replying."),
            "Take a moment before replying.",
        )

    def test_nothing_at_all(self):
        for raw in (None, "", "   "):
            self.assertIsNone(self.parse(raw), repr(raw))

    def test_guidance_spanning_lines_is_kept_whole(self):
        self.assertEqual(
            self.parse("NEEDED: yes\nGUIDANCE: One thought.\nAnd a second."),
            "One thought. And a second.",
        )


class RewriteSofteningTests(AssistTestCase):
    """A rewrite must not hand back the pattern the check just flagged."""

    def test_an_absolute_the_sender_did_not_use_is_softened(self):
        self.assertEqual(
            assist._soften_absolutes("you are impossible", "It's always me picking up"),
            "It's often me picking up",
        )
        self.assertEqual(
            assist._soften_absolutes("you are impossible", "You never listen to me"),
            "You rarely listen to me",
        )

    def test_the_senders_own_words_are_left_alone(self):
        """Echoing what they wrote is quoting them, not editorialising."""
        self.assertEqual(
            assist._soften_absolutes(
                "you always do this", "I feel like you always do this"
            ),
            "I feel like you always do this",
        )

    def test_it_is_case_insensitive_and_word_bounded(self):
        self.assertEqual(
            assist._soften_absolutes("hey", "Always late. Alwaysland is fine."),
            "often late. Alwaysland is fine.",
        )

    def test_an_ordinary_rewrite_is_untouched(self):
        rewrite = "I felt unheard when that happened."
        self.assertEqual(assist._soften_absolutes("you are impossible", rewrite), rewrite)

    def test_the_check_applies_it(self):
        raw = (
            "VERDICT: caution\nREASON: sweeping\n"
            "SUGGESTION: I feel like it's always me sorting this."
        )
        with patch("apps.chat.assist._complete", return_value=raw):
            result = assist.check_before_send(
                self.relationship, self.alex, "you are pathetic and this is typical you"
            )
        self.assertNotIn("always", result["suggestion"])
        self.assertEqual(result["verdict"], "caution")
