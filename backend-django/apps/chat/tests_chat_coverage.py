"""The last uncovered branches in the chat app.

Races, corrupt state, and the small pieces of presentation nobody thinks to
test. Individually unremarkable; collectively they are the difference between
"the tests pass" and "the tests would notice".
"""

import io
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from apps.chat import evalset, media as media_processing, storage
from apps.chat.models import (
    AssistNudge,
    ChatAssistSettings,
    CoupleMessage,
    MessageMedia,
    MessageReaction,
    ReadReceipt,
    ThreadSummary,
)
from apps.chat.serializers import ReactionSerializer
from apps.chat.views import _queue
from apps.relationships.models import Relationship
from django.utils import timezone

User = get_user_model()


def jpeg_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 24), (90, 90, 90)).save(buffer, format="JPEG")
    return buffer.getvalue()


class EvalsetTests(TestCase):
    def test_counts_split_the_drafts(self):
        clean, flagged = evalset.counts()

        self.assertGreater(clean, 0)
        self.assertGreater(flagged, 0)
        self.assertEqual(clean + flagged, len(evalset.EVAL_DRAFTS))


class MediaProcessingBranchTests(TestCase):
    def test_a_jpeg_header_with_a_corrupt_body_is_rejected(self):
        # Sniffs as a JPEG, then fails to decode. The decode is what has to
        # refuse it, and the MediaRejected from the sniff must not be swallowed
        # by the generic handler underneath.
        with self.assertRaises(media_processing.MediaRejected):
            media_processing.process_image(b"\xff\xd8\xff" + b"\x11" * 500)

    def test_an_oversized_voice_note_is_refused_by_the_processor(self):
        blob = b"\x00\x00\x00\x20ftypM4A " + b"\x00" * media_processing.MAX_VOICE_BYTES
        with self.assertRaises(media_processing.MediaRejected):
            media_processing.process_voice(blob, 5000)


class ReactionSerializerTests(TestCase):
    def test_a_blank_emoji_is_rejected(self):
        serializer = ReactionSerializer(data={"emoji": "   "})
        self.assertFalse(serializer.is_valid())

    def test_a_real_emoji_is_trimmed(self):
        serializer = ReactionSerializer(data={"emoji": " 😍 "})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["emoji"], "😍")

    def test_the_blank_guard_is_exercised_directly(self):
        """Reached by unit, not through the serializer.

        ``CharField`` trims whitespace before field validation runs, so a
        whitespace-only emoji is already rejected as blank and never arrives
        here. The guard stays because it is what makes the method correct on
        its own terms rather than by relying on a DRF default, and this is the
        only way to exercise it.
        """
        with self.assertRaises(Exception):
            ReactionSerializer().validate_emoji("   ")


@override_settings(
    CLOUDINARY_CLOUD_NAME=None, CLOUDINARY_API_KEY=None, CLOUDINARY_API_SECRET=None
)
class ChatCoverageTestCase(TestCase):
    def setUp(self):
        self.alex = User.objects.create_user(email="alex@test.local", password="pw12345!")
        self.sam = User.objects.create_user(email="sam@test.local", password="pw12345!")
        self.relationship = Relationship.objects.create(
            partner_a=self.alex, partner_b=self.sam, status="active"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.alex)

        publish = patch("apps.chat.views.realtime.publish", return_value=True)
        publish.start()
        self.addCleanup(publish.stop)

        storage.reset_backend()
        self.addCleanup(storage.reset_backend)

    def send(self, **payload):
        return self.client.post(
            reverse("chat-send", args=[self.relationship.id]), payload, format="json"
        )


class ModelStringTests(ChatCoverageTestCase):
    """Admin-facing reprs. Cheap, and the place a stale field name hides."""

    def test_every_model_names_itself(self):
        message = CoupleMessage(relationship=self.relationship, sender=self.alex)
        message.body = "hi"
        message.save()

        reaction = MessageReaction.objects.create(
            message=message, user=self.alex, emoji="😍"
        )
        receipt = ReadReceipt.objects.create(
            relationship=self.relationship, user=self.alex, last_read_at=timezone.now()
        )
        settings_row, _ = ChatAssistSettings.objects.get_or_create(
            relationship=self.relationship
        )
        nudge = AssistNudge.objects.create(
            relationship=self.relationship,
            user=self.alex,
            kind="repair",
            suggestion="reach out",
        )
        summary = ThreadSummary.objects.create(
            relationship=self.relationship, summary="warm", covered_message_count=3
        )

        self.assertIn(str(message.id), str(message))
        self.assertIn("😍", str(reaction))
        self.assertIn("read", str(receipt))
        self.assertIn("Assist settings", str(settings_row))
        self.assertIn("nudge", str(nudge))
        self.assertIn("Summary", str(summary))


class CorruptCiphertextTests(ChatCoverageTestCase):
    def test_a_body_that_will_not_decrypt_empties_rather_than_raising(self):
        message = CoupleMessage(relationship=self.relationship, sender=self.alex)
        message.body = "readable"
        message.save()
        CoupleMessage.objects.filter(id=message.id).update(ciphertext="not base64 at all")

        # One unreadable row must not take down the whole thread.
        self.assertEqual(CoupleMessage.objects.get(id=message.id).body, "")

    def test_a_transcript_that_will_not_decrypt_empties_rather_than_raising(self):
        media = MessageMedia.objects.create(
            relationship=self.relationship,
            uploader=self.alex,
            kind=MessageMedia.KIND_VOICE,
            storage_key="k",
            mime="audio/mp4",
            transcript_ciphertext="not base64 at all",
        )
        self.assertEqual(media.transcript, "")


class RaceTests(ChatCoverageTestCase):
    def test_two_sends_racing_on_one_client_id_return_the_winner(self):
        first = self.send(body="hello", client_id="same")

        # The pre-check misses because the row lands between it and the insert;
        # the unique constraint is what actually holds the line.
        original_save = CoupleMessage.save

        def racing_save(self_message, *args, **kwargs):
            raise IntegrityError("duplicate key")

        with patch.object(CoupleMessage, "save", racing_save):
            with patch(
                "apps.chat.views.CoupleMessage.objects.filter"
            ) as filter_mock:
                filter_mock.return_value.first.side_effect = [
                    None,  # the idempotency pre-check
                    CoupleMessage.objects.get(id=first.data["id"]),  # after the race
                ]
                response = self.send(body="hello", client_id="same")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        CoupleMessage.save = original_save

    def test_an_integrity_error_with_no_winner_is_not_swallowed(self):
        with patch.object(
            CoupleMessage, "save", side_effect=IntegrityError("something else")
        ):
            with self.assertRaises(IntegrityError):
                self.send(body="hello", client_id="unique-one")

    def test_a_double_tapped_reaction_does_not_error(self):
        message_id = self.send(body="hi").data["id"]
        url = reverse("chat-react", args=[message_id])

        with patch.object(
            MessageReaction.objects, "create", side_effect=IntegrityError("raced")
        ):
            response = self.client.post(url, {"emoji": "😍"}, format="json")

        # The reaction is present either way; a race must not surface as a 500.
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class QueueHelperTests(TestCase):
    def test_a_broker_failure_is_logged_not_raised(self):
        task = patch("apps.chat.transcription.transcribe_voice_note").start()
        task.delay.side_effect = RuntimeError("no broker")
        task.name = "chat.transcribe_voice_note"
        self.addCleanup(patch.stopall)

        _queue(task, "media-id")  # must not raise


class NudgeParameterTests(ChatCoverageTestCase):
    def test_a_nonsense_hour_is_ignored_rather_than_rejected(self):
        url = reverse("chat-assist-nudge", args=[self.relationship.id])

        with patch("apps.chat.assist.nudge_for", return_value=None) as nudge_for:
            self.client.get(url, {"local_hour": "not-a-number"})

        self.assertIsNone(nudge_for.call_args.kwargs["local_hour"])

    def test_an_out_of_range_hour_is_ignored(self):
        url = reverse("chat-assist-nudge", args=[self.relationship.id])

        with patch("apps.chat.assist.nudge_for", return_value=None) as nudge_for:
            self.client.get(url, {"local_hour": "47"})

        self.assertIsNone(nudge_for.call_args.kwargs["local_hour"])

    def test_a_valid_hour_is_passed_through(self):
        url = reverse("chat-assist-nudge", args=[self.relationship.id])

        with patch("apps.chat.assist.nudge_for", return_value=None) as nudge_for:
            self.client.get(url, {"local_hour": "22"})

        self.assertEqual(nudge_for.call_args.kwargs["local_hour"], 22)

    def test_an_actual_nudge_is_rendered(self):
        nudge = AssistNudge.objects.create(
            relationship=self.relationship,
            user=self.alex,
            kind="repair",
            suggestion="tell them what you needed",
        )
        url = reverse("chat-assist-nudge", args=[self.relationship.id])

        with patch("apps.chat.assist.nudge_for", return_value=nudge):
            response = self.client.get(url)

        self.assertEqual(response.data["nudge"]["id"], str(nudge.id))
        self.assertEqual(response.data["nudge"]["kind"], "repair")
        self.assertEqual(
            response.data["nudge"]["suggestion"], "tell them what you needed"
        )
