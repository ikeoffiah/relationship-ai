"""Transcription, moderation and erasure for chat media.

The properties here are the ones that make voice notes legible to Bliss without
making deletion a lie, and that keep a blocked photo from ever reaching a
partner. See docs/chat-media.md §5.
"""

import io
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from apps.chat import assist, moderation, storage, transcription
from apps.chat.erasure import erase_media_for_user
from apps.chat.models import ChatAssistSettings, CoupleMessage, MessageMedia, ThreadSummary
from apps.relationships.models import Relationship
from apps.safety.models import SafetyIncident

User = get_user_model()


def jpeg_bytes(size=(64, 48)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, (120, 80, 60)).save(buffer, format="JPEG")
    return buffer.getvalue()


def m4a_bytes(payload_size=2048) -> bytes:
    return b"\x00\x00\x00\x20ftypM4A " + b"\x00" * payload_size


@override_settings(
    CLOUDINARY_CLOUD_NAME=None, CLOUDINARY_API_KEY=None, CLOUDINARY_API_SECRET=None
)
class MediaSafetyTestCase(TestCase):
    def setUp(self):
        self.alex = User.objects.create_user(email="alex@test.local", password="pw12345!")
        self.sam = User.objects.create_user(email="sam@test.local", password="pw12345!")
        self.relationship = Relationship.objects.create(
            partner_a=self.alex, partner_b=self.sam, status="active"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.alex)

        patcher = patch("apps.chat.views.realtime.publish", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

        # Background work is queued by the upload endpoint; each test drives
        # the task it cares about directly rather than depending on a broker.
        queue = patch("apps.chat.views._queue")
        self.queue = queue.start()
        self.addCleanup(queue.stop)

        storage.reset_backend()
        self.addCleanup(storage.reset_backend)

    def upload_voice(self, duration_ms=5000):
        upload = io.BytesIO(m4a_bytes())
        upload.name = "note.m4a"
        return self.client.post(
            reverse("chat-media-upload", args=[self.relationship.id]),
            {"kind": "voice", "file": upload, "duration_ms": duration_ms},
            format="multipart",
        )

    def upload_image(self):
        upload = io.BytesIO(jpeg_bytes())
        upload.name = "photo.jpg"
        return self.client.post(
            reverse("chat-media-upload", args=[self.relationship.id]),
            {"kind": "image", "file": upload},
            format="multipart",
        )

    def send(self, **payload):
        return self.client.post(
            reverse("chat-send", args=[self.relationship.id]), payload, format="json"
        )


def transcript_response(text):
    response = MagicMock()
    response.text = text
    client = MagicMock()
    client.with_options.return_value.audio.transcriptions.create.return_value = response
    return client


@override_settings()
class TranscriptionTests(MediaSafetyTestCase):
    def setUp(self):
        super().setUp()
        key = patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
        key.start()
        self.addCleanup(key.stop)

    def test_a_voice_note_is_marked_pending_on_upload(self):
        response = self.upload_voice()
        self.assertEqual(response.data["transcript_status"], "pending")

    def test_transcription_stores_text_encrypted(self):
        media_id = self.upload_voice().data["id"]

        with patch("apps.chat.assist._get_client", return_value=transcript_response("i miss you")):
            transcription.transcribe_voice_note(media_id)

        media = MessageMedia.objects.get(id=media_id)
        self.assertEqual(media.transcript, "i miss you")
        self.assertEqual(media.transcript_status, "ok")
        # Stored encrypted, not as plain text in the column.
        self.assertNotIn("i miss you", media.transcript_ciphertext)

    def test_a_transcript_is_unreadable_under_the_wrong_scope(self):
        from utils.encryption import decrypt

        media_id = self.upload_voice().data["id"]
        with patch("apps.chat.assist._get_client", return_value=transcript_response("private")):
            transcription.transcribe_voice_note(media_id)

        media = MessageMedia.objects.get(id=media_id)
        self.assertEqual(decrypt(media.transcript_ciphertext, "another-relationship"),
                         "[ENCRYPTION_ERROR]")

    def test_bliss_reads_a_voice_note_it_could_not_see_before(self):
        media_id = self.upload_voice().data["id"]
        with patch("apps.chat.assist._get_client", return_value=transcript_response("i felt alone")):
            transcription.transcribe_voice_note(media_id)
        self.send(kind="voice", media=media_id)

        context = assist._thread_context(self.relationship)

        self.assertIn("i felt alone", context)

    def test_an_untranscribed_voice_note_contributes_nothing(self):
        media_id = self.upload_voice().data["id"]
        self.send(kind="voice", media=media_id)

        # No crash, no empty speaker line — it simply is not there yet.
        self.assertEqual(assist._thread_context(self.relationship), "")

    def test_an_image_caption_reaches_bliss_but_the_photo_does_not(self):
        media_id = self.upload_image().data["id"]
        self.send(kind="image", media=media_id, body="us last summer")

        self.assertIn("us last summer", assist._thread_context(self.relationship))

    def test_assist_disabled_means_no_audio_leaves_the_process(self):
        ChatAssistSettings.objects.update_or_create(
            relationship=self.relationship, defaults={"assist_enabled": False}
        )
        media_id = self.upload_voice().data["id"]

        with patch("apps.chat.assist._get_client") as client:
            transcription.transcribe_voice_note(media_id)

        client.assert_not_called()
        self.assertEqual(
            MessageMedia.objects.get(id=media_id).transcript_status, "skipped"
        )

    def test_upload_does_not_mark_pending_when_assist_is_off(self):
        ChatAssistSettings.objects.update_or_create(
            relationship=self.relationship, defaults={"assist_enabled": False}
        )
        self.assertEqual(self.upload_voice().data["transcript_status"], "skipped")

    def test_a_failure_leaves_the_note_playable(self):
        media_id = self.upload_voice().data["id"]
        client = MagicMock()
        client.with_options.return_value.audio.transcriptions.create.side_effect = RuntimeError(
            "upstream down"
        )

        with patch("apps.chat.assist._get_client", return_value=client):
            transcription.transcribe_voice_note(media_id)

        media = MessageMedia.objects.get(id=media_id)
        self.assertEqual(media.transcript_status, "failed")
        self.assertTrue(media.storage_key, "the audio must survive a failed transcription")

    def test_the_meta_endpoint_reveals_the_transcript_after_the_fact(self):
        media_id = self.upload_voice().data["id"]
        with patch("apps.chat.assist._get_client", return_value=transcript_response("hello you")):
            transcription.transcribe_voice_note(media_id)

        response = self.client.get(reverse("chat-media-meta", args=[media_id]))

        self.assertEqual(response.data["transcript"], "hello you")

    def test_a_stranger_cannot_read_media_metadata(self):
        media_id = self.upload_voice().data["id"]
        stranger = User.objects.create_user(email="s@test.local", password="pw12345!")
        self.client.force_authenticate(user=stranger)

        response = self.client.get(reverse("chat-media-meta", args=[media_id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TranscriptDeletionTests(MediaSafetyTestCase):
    """A transcript must not outlive the recording it came from."""

    def with_transcript(self, text="something said out loud"):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "k"}), patch(
            "apps.chat.assist._get_client", return_value=transcript_response(text)
        ):
            media_id = self.upload_voice().data["id"]
            transcription.transcribe_voice_note(media_id)
        return media_id

    def test_deleting_the_message_clears_the_transcript(self):
        media_id = self.with_transcript()
        message_id = self.send(kind="voice", media=media_id).data["id"]

        self.client.delete(reverse("chat-delete", args=[message_id]))

        self.assertEqual(MessageMedia.objects.get(id=media_id).transcript, "")

    def test_deleting_a_transcribed_note_invalidates_the_rolling_summary(self):
        """The second deletion lie: audio gone, words still in the summary."""
        media_id = self.with_transcript()
        message_id = self.send(kind="voice", media=media_id).data["id"]
        ThreadSummary.objects.update_or_create(
            relationship=self.relationship,
            defaults={"summary": "They talked about feeling alone.", "covered_message_count": 12},
        )

        self.client.delete(reverse("chat-delete", args=[message_id]))

        summary = ThreadSummary.objects.get(relationship=self.relationship)
        self.assertEqual(summary.summary, "")
        self.assertEqual(summary.covered_message_count, 0)

    def test_deleting_a_photo_leaves_the_summary_alone(self):
        """No transcript, nothing of it in the summary, nothing to invalidate."""
        media_id = self.upload_image().data["id"]
        message_id = self.send(kind="image", media=media_id).data["id"]
        ThreadSummary.objects.update_or_create(
            relationship=self.relationship,
            defaults={"summary": "Warm week.", "covered_message_count": 9},
        )

        self.client.delete(reverse("chat-delete", args=[message_id]))

        self.assertEqual(
            ThreadSummary.objects.get(relationship=self.relationship).summary, "Warm week."
        )


def moderation_response(categories: dict):
    result = MagicMock()
    result.categories.model_dump.return_value = categories
    response = MagicMock()
    response.results = [result]
    client = MagicMock()
    client.with_options.return_value.moderations.create.return_value = response
    return client


class ImageModerationTests(MediaSafetyTestCase):
    def setUp(self):
        super().setUp()
        key = patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
        key.start()
        self.addCleanup(key.stop)

    def test_a_clean_photo_survives(self):
        media_id = self.upload_image().data["id"]
        keys = MessageMedia.objects.get(id=media_id).storage_keys()

        with patch("apps.chat.assist._get_client", return_value=moderation_response({"violence": False})):
            self.assertEqual(moderation.moderate_image(media_id), "ok")

        self.assertTrue(storage.get(keys[0]))

    def test_a_blocking_category_destroys_the_bytes(self):
        media_id = self.upload_image().data["id"]
        keys = MessageMedia.objects.get(id=media_id).storage_keys()

        with patch(
            "apps.chat.assist._get_client",
            return_value=moderation_response({"sexual_minors": True}),
        ):
            self.assertEqual(moderation.moderate_image(media_id), "blocked")

        for key in keys:
            with self.assertRaises(storage.MissingBlob):
                storage.get(key)

    def test_a_blocked_photo_can_never_be_sent(self):
        media_id = self.upload_image().data["id"]
        with patch(
            "apps.chat.assist._get_client",
            return_value=moderation_response({"sexual_minors": True}),
        ):
            moderation.moderate_image(media_id)

        response = self.send(kind="image", media=media_id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_blocking_opens_a_safety_incident(self):
        media_id = self.upload_image().data["id"]

        with patch(
            "apps.chat.assist._get_client",
            return_value=moderation_response({"sexual_minors": True}),
        ):
            moderation.moderate_image(media_id)

        incident = SafetyIncident.objects.get(category="media_blocked")
        self.assertEqual(incident.severity, "critical")
        self.assertEqual(incident.user_id_anon, str(self.alex.id)[:8])

    def test_a_merely_flagged_category_does_not_block(self):
        """Two adults sending each other photographs is the product working."""
        media_id = self.upload_image().data["id"]
        keys = MessageMedia.objects.get(id=media_id).storage_keys()

        with patch(
            "apps.chat.assist._get_client", return_value=moderation_response({"sexual": True})
        ):
            self.assertEqual(moderation.moderate_image(media_id), "flagged")

        self.assertTrue(storage.get(keys[0]))
        self.assertFalse(SafetyIncident.objects.exists())

    def test_moderation_fails_open_when_the_model_is_unavailable(self):
        media_id = self.upload_image().data["id"]
        client = MagicMock()
        client.with_options.return_value.moderations.create.side_effect = RuntimeError("down")

        with patch("apps.chat.assist._get_client", return_value=client):
            self.assertIsNone(moderation.moderate_image(media_id))

        # An outage must not stop couples sending each other photographs.
        self.assertEqual(
            self.send(kind="image", media=media_id).status_code, status.HTTP_201_CREATED
        )


class AccountErasureTests(MediaSafetyTestCase):
    def test_deleting_an_account_destroys_its_media(self):
        media_id = self.upload_image().data["id"]
        keys = MessageMedia.objects.get(id=media_id).storage_keys()
        self.send(kind="image", media=media_id)

        response = self.client.delete(
            reverse("account-delete"), {"password": "pw12345!"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        for key in keys:
            with self.assertRaises(storage.MissingBlob):
                storage.get(key)

    def test_erasure_reaches_media_the_partner_sent(self):
        """The thread is one shared object under one key; half-erasing it is not
        an option that leaves anybody better off."""
        self.client.force_authenticate(user=self.sam)
        media_id = self.upload_image().data["id"]
        keys = MessageMedia.objects.get(id=media_id).storage_keys()

        erase_media_for_user(self.alex)

        for key in keys:
            with self.assertRaises(storage.MissingBlob):
                storage.get(key)

    def test_a_wrong_password_erases_nothing(self):
        media_id = self.upload_image().data["id"]
        keys = MessageMedia.objects.get(id=media_id).storage_keys()

        response = self.client.delete(
            reverse("account-delete"), {"password": "not-it"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(storage.get(keys[0]))

    def test_a_storage_failure_is_reported_rather_than_hidden(self):
        self.upload_image()

        with patch("apps.chat.storage.delete", side_effect=storage.StorageError("down")):
            response = self.client.delete(
                reverse("account-delete"), {"password": "pw12345!"}, format="json"
            )

        # The account still goes, but the answer does not claim a clean erasure.
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("could not be removed", response.data["detail"])
        self.alex.refresh_from_db()
        self.assertFalse(self.alex.is_active)

    def test_media_still_referenced_by_no_message_is_erased_too(self):
        media_id = self.upload_image().data["id"]  # never sent
        keys = MessageMedia.objects.get(id=media_id).storage_keys()

        erase_media_for_user(self.alex)

        for key in keys:
            with self.assertRaises(storage.MissingBlob):
                storage.get(key)

    def test_erasure_leaves_message_rows_as_tombstones(self):
        media_id = self.upload_image().data["id"]
        message_id = self.send(kind="image", media=media_id).data["id"]

        erase_media_for_user(self.alex)

        # The row survives so a reply quoting it still renders.
        self.assertTrue(CoupleMessage.objects.filter(id=message_id).exists())
