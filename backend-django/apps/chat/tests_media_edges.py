"""The paths the happy-path tests never take.

Failure branches, degenerate inputs and background tasks. Nothing here is
exotic — it is the behaviour a couple actually meets when a network is bad, a
file is odd, or a model is unavailable, which is exactly the behaviour least
likely to have been tried by hand.
"""

import io
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from apps.chat import assist, media as media_processing, moderation, storage, transcription
from apps.chat.erasure import erase_media_for_user, relationships_for
from apps.chat.models import (
    ChatAssistSettings,
    CoupleMessage,
    MessageMedia,
    ThreadSummary,
)
from apps.chat.tasks import refresh_thread_summary, summary_is_stale
from apps.relationships.models import Relationship

User = get_user_model()


def jpeg_bytes(size=(64, 48)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, (120, 80, 60)).save(buffer, format="JPEG")
    return buffer.getvalue()


def png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), (10, 10, 10)).save(buffer, format="PNG")
    return buffer.getvalue()


def m4a_bytes(brand=b"M4A ", size=2048) -> bytes:
    return b"\x00\x00\x00\x20ftyp" + brand + b"\x00" * size


class SniffingTests(TestCase):
    """Type comes from the bytes, never from what the client claimed."""

    def test_png_is_recognised(self):
        self.assertEqual(media_processing.sniff_image(png_bytes()), "image/png")

    def test_gif_is_recognised(self):
        self.assertEqual(media_processing.sniff_image(b"GIF89a" + b"\x00" * 10), "image/gif")
        self.assertEqual(media_processing.sniff_image(b"GIF87a" + b"\x00" * 10), "image/gif")

    def test_avif_is_recognised(self):
        self.assertEqual(
            media_processing.sniff_image(b"\x00\x00\x00\x18ftypavif" + b"\x00" * 8),
            "image/avif",
        )

    def test_heic_is_refused_rather_than_half_supported(self):
        # Pillow cannot decode it without a plugin, and carrying an image codec
        # we would have to keep patched is worse than converting on the client.
        with self.assertRaises(media_processing.MediaRejected):
            media_processing.sniff_image(b"\x00\x00\x00\x18ftypheic" + b"\x00" * 8)

    def test_audio_brands_we_accept(self):
        for brand in (b"M4A ", b"mp42", b"isom", b"iso2", b"mp41"):
            self.assertEqual(media_processing.sniff_audio(m4a_bytes(brand)), "audio/mp4")

    def test_an_unknown_audio_brand_is_refused(self):
        with self.assertRaises(media_processing.MediaRejected):
            media_processing.sniff_audio(m4a_bytes(b"qt  "))

    def test_a_short_file_is_not_audio(self):
        with self.assertRaises(media_processing.MediaRejected):
            media_processing.sniff_audio(b"tiny")

    def test_a_png_that_pillow_cannot_decode_is_rejected(self):
        # Right magic bytes, corrupt body — the sniff passes and the decode
        # must be what refuses it.
        with self.assertRaises(media_processing.MediaRejected):
            media_processing.process_image(b"\x89PNG\r\n\x1a\n" + b"\x00" * 200)

    def test_has_metadata_on_something_that_is_not_an_image(self):
        self.assertFalse(media_processing.has_metadata(b"not an image"))

    def test_a_png_upload_is_stored_as_jpeg(self):
        stored, _thumb, _w, _h = media_processing.process_image(png_bytes())
        self.assertTrue(stored.startswith(b"\xff\xd8\xff"))


@override_settings(
    CLOUDINARY_CLOUD_NAME=None, CLOUDINARY_API_KEY=None, CLOUDINARY_API_SECRET=None
)
class ChatMediaEdgeTestCase(TestCase):
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

        queue = patch("apps.chat.views._queue")
        self.queue = queue.start()
        self.addCleanup(queue.stop)

        storage.reset_backend()
        self.addCleanup(storage.reset_backend)

    def upload_image(self):
        upload = io.BytesIO(jpeg_bytes())
        upload.name = "photo.jpg"
        return self.client.post(
            reverse("chat-media-upload", args=[self.relationship.id]),
            {"kind": "image", "file": upload},
            format="multipart",
        )

    def upload_voice(self, duration_ms=4000):
        upload = io.BytesIO(m4a_bytes())
        upload.name = "note.m4a"
        return self.client.post(
            reverse("chat-media-upload", args=[self.relationship.id]),
            {"kind": "voice", "file": upload, "duration_ms": duration_ms},
            format="multipart",
        )

    def send(self, **payload):
        return self.client.post(
            reverse("chat-send", args=[self.relationship.id]), payload, format="json"
        )


class UploadValidationTests(ChatMediaEdgeTestCase):
    def test_a_request_with_no_file_is_rejected(self):
        response = self.client.post(
            reverse("chat-media-upload", args=[self.relationship.id]),
            {"kind": "image"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_a_voice_upload_without_a_duration_is_rejected(self):
        upload = io.BytesIO(m4a_bytes())
        upload.name = "note.m4a"
        response = self.client.post(
            reverse("chat-media-upload", args=[self.relationship.id]),
            {"kind": "voice", "file": upload},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_an_unknown_kind_is_rejected(self):
        upload = io.BytesIO(jpeg_bytes())
        upload.name = "x.jpg"
        response = self.client.post(
            reverse("chat-media-upload", args=[self.relationship.id]),
            {"kind": "video", "file": upload},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_an_oversized_voice_note_is_rejected_before_it_is_read(self):
        upload = io.BytesIO(m4a_bytes(size=media_processing.MAX_VOICE_BYTES + 10))
        upload.name = "note.m4a"
        response = self.client.post(
            reverse("chat-media-upload", args=[self.relationship.id]),
            {"kind": "voice", "file": upload, "duration_ms": 5000},
            format="multipart",
        )
        self.assertEqual(
            response.status_code, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        )

    def test_a_thumbnail_failure_is_cleaned_up_too(self):
        # The second put fails, so the first must not be left orphaned.
        real_put = storage.get_backend().put
        calls = {"n": 0}

        def flaky(key, blob):
            calls["n"] += 1
            if calls["n"] == 2:
                raise storage.StorageError("down")
            return real_put(key, blob)

        with patch("apps.chat.views.storage.put", side_effect=flaky):
            response = self.upload_image()

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(MessageMedia.objects.count(), 0)

    def test_a_cleanup_failure_does_not_mask_the_upload_failure(self):
        with patch(
            "apps.chat.views.storage.put", side_effect=storage.StorageError("down")
        ), patch(
            "apps.chat.views.storage.delete", side_effect=storage.StorageError("also down")
        ):
            response = self.upload_image()

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)


class MediaServingTests(ChatMediaEdgeTestCase):
    def test_a_voice_note_has_no_thumbnail_to_serve(self):
        media_id = self.upload_voice().data["id"]

        response = self.client.get(reverse("chat-media-thumb", args=[media_id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_an_unreadable_blob_degrades_to_404(self):
        media_id = self.upload_image().data["id"]
        record = MessageMedia.objects.get(id=media_id)
        # Ciphertext replaced with something that will not decrypt.
        storage.put(record.storage_key, b"garbage that is not a valid blob")

        response = self.client.get(reverse("chat-media-blob", args=[media_id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_a_storage_outage_degrades_to_404_rather_than_500(self):
        media_id = self.upload_image().data["id"]

        with patch(
            "apps.chat.views.storage.get", side_effect=storage.StorageError("down")
        ):
            response = self.client.get(reverse("chat-media-blob", args=[media_id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_a_deleted_media_row_is_not_served(self):
        media_id = self.upload_image().data["id"]
        MessageMedia.objects.get(id=media_id).destroy()

        response = self.client.get(reverse("chat-media-blob", args=[media_id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SendValidationTests(ChatMediaEdgeTestCase):
    def test_a_reply_to_another_thread_is_rejected(self):
        stranger = User.objects.create_user(email="x@test.local", password="pw12345!")
        other = Relationship.objects.create(
            partner_a=stranger,
            partner_b=User.objects.create_user(email="y@test.local", password="pw12345!"),
            status="active",
        )
        theirs = CoupleMessage(relationship=other, sender=stranger)
        theirs.body = "private"
        theirs.save()

        response = self.send(body="hi", reply_to=str(theirs.id))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_an_empty_text_message_is_rejected(self):
        self.assertEqual(
            self.send(body="   ").status_code, status.HTTP_400_BAD_REQUEST
        )

    def test_a_sticker_message_needs_a_sticker(self):
        self.assertEqual(
            self.send(kind="sticker").status_code, status.HTTP_400_BAD_REQUEST
        )

    def test_media_that_does_not_exist_is_rejected(self):
        import uuid

        response = self.send(kind="image", media=str(uuid.uuid4()))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_a_reply_to_a_photo_carries_the_quote_kind(self):
        media_id = self.upload_image().data["id"]
        photo_id = self.send(kind="image", media=media_id).data["id"]

        reply = self.send(body="lovely", reply_to=photo_id)

        self.assertEqual(reply.data["reply_to"]["kind"], "image")

    def test_a_quote_of_a_deleted_message_shows_no_body(self):
        first = self.send(body="something").data["id"]
        reply = self.send(body="re", reply_to=first).data["id"]
        self.client.delete(reverse("chat-delete", args=[first]))

        listing = self.client.get(reverse("chat-messages", args=[self.relationship.id]))
        quoted = next(
            m for m in listing.data["results"] if m["id"] == str(reply)
        )["reply_to"]

        self.assertEqual(quoted["body"], "")
        self.assertIsNone(quoted["thumb_url"])


class DeletionEdgeTests(ChatMediaEdgeTestCase):
    def test_only_the_author_may_delete(self):
        message_id = self.send(body="mine").data["id"]
        self.client.force_authenticate(user=self.sam)

        response = self.client.delete(reverse("chat-delete", args=[message_id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_deleting_twice_is_harmless(self):
        message_id = self.send(body="mine").data["id"]
        self.client.delete(reverse("chat-delete", args=[message_id]))

        response = self.client.delete(reverse("chat-delete", args=[message_id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_destroying_media_twice_is_harmless(self):
        record = MessageMedia.objects.get(id=self.upload_image().data["id"])
        record.destroy()
        record.destroy()  # no keys left to delete

        self.assertIsNotNone(record.deleted_at)

    def test_a_destroyed_row_reports_no_transcript(self):
        record = MessageMedia.objects.get(id=self.upload_voice().data["id"])
        record.transcript = "said out loud"
        record.save()
        record.destroy()

        self.assertEqual(record.transcript, "")

    def test_setting_an_empty_transcript_clears_the_ciphertext(self):
        record = MessageMedia.objects.get(id=self.upload_voice().data["id"])
        record.transcript = "something"
        record.transcript = ""

        self.assertEqual(record.transcript_ciphertext, "")

    def test_media_string_representation(self):
        record = MessageMedia.objects.get(id=self.upload_image().data["id"])
        self.assertIn("image", str(record))
        self.assertTrue(record.is_attached is False)


class QueueingTests(ChatMediaEdgeTestCase):
    def test_a_broker_that_is_down_does_not_break_an_upload(self):
        # _queue is patched out in the base case; here the real one runs against
        # a task whose delay explodes.
        self.queue.stop()
        self.addCleanup(self.queue.start)

        with patch(
            "apps.chat.transcription.transcribe_voice_note.delay",
            side_effect=RuntimeError("no broker"),
        ), patch.dict("os.environ", {"OPENAI_API_KEY": "k"}):
            response = self.upload_voice()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class TranscriptionEdgeTests(ChatMediaEdgeTestCase):
    def test_a_missing_media_row_is_ignored(self):
        import uuid

        self.assertIsNone(transcription.transcribe_voice_note(uuid.uuid4()))

    def test_an_image_is_never_transcribed(self):
        media_id = self.upload_image().data["id"]
        self.assertIsNone(transcription.transcribe_voice_note(media_id))

    def test_without_an_api_key_nothing_is_transcribed(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(transcription.should_transcribe(self.relationship))

    def test_unreadable_audio_marks_the_transcript_failed(self):
        media_id = self.upload_voice().data["id"]

        with patch.dict("os.environ", {"OPENAI_API_KEY": "k"}), patch(
            "apps.chat.storage.get", side_effect=storage.StorageError("down")
        ):
            transcription.transcribe_voice_note(media_id)

        self.assertEqual(
            MessageMedia.objects.get(id=media_id).transcript_status, "failed"
        )

    def test_an_empty_transcript_counts_as_a_failure(self):
        media_id = self.upload_voice().data["id"]
        client = MagicMock()
        client.with_options.return_value.audio.transcriptions.create.return_value = (
            MagicMock(text="   ")
        )

        with patch.dict("os.environ", {"OPENAI_API_KEY": "k"}), patch(
            "apps.chat.assist._get_client", return_value=client
        ):
            transcription.transcribe_voice_note(media_id)

        self.assertEqual(
            MessageMedia.objects.get(id=media_id).transcript_status, "failed"
        )


class ModerationEdgeTests(ChatMediaEdgeTestCase):
    def test_without_an_api_key_nothing_is_screened(self):
        media_id = self.upload_image().data["id"]
        with patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(moderation.moderate_image(media_id))

    def test_a_missing_media_row_is_ignored(self):
        import uuid

        with patch.dict("os.environ", {"OPENAI_API_KEY": "k"}):
            self.assertIsNone(moderation.moderate_image(uuid.uuid4()))

    def test_a_voice_note_is_never_image_screened(self):
        media_id = self.upload_voice().data["id"]
        with patch.dict("os.environ", {"OPENAI_API_KEY": "k"}):
            self.assertIsNone(moderation.moderate_image(media_id))

    def test_unreadable_bytes_are_not_screened(self):
        media_id = self.upload_image().data["id"]
        with patch.dict("os.environ", {"OPENAI_API_KEY": "k"}), patch(
            "apps.chat.storage.get", side_effect=storage.StorageError("down")
        ):
            self.assertIsNone(moderation.moderate_image(media_id))

    def test_a_response_with_no_categories_is_treated_as_clean(self):
        media_id = self.upload_image().data["id"]
        result = MagicMock()
        result.categories = None
        response = MagicMock()
        response.results = [result]
        client = MagicMock()
        client.with_options.return_value.moderations.create.return_value = response

        with patch.dict("os.environ", {"OPENAI_API_KEY": "k"}), patch(
            "apps.chat.assist._get_client", return_value=client
        ):
            self.assertEqual(moderation.moderate_image(media_id), "ok")

    def test_a_block_whose_destroy_fails_still_records_the_incident(self):
        from apps.safety.models import SafetyIncident

        media_id = self.upload_image().data["id"]
        result = MagicMock()
        result.categories.model_dump.return_value = {"violence_graphic": True}
        response = MagicMock()
        response.results = [result]
        client = MagicMock()
        client.with_options.return_value.moderations.create.return_value = response

        with patch.dict("os.environ", {"OPENAI_API_KEY": "k"}), patch(
            "apps.chat.assist._get_client", return_value=client
        ), patch("apps.chat.storage.delete", side_effect=storage.StorageError("down")):
            self.assertEqual(moderation.moderate_image(media_id), "blocked")

        self.assertTrue(SafetyIncident.objects.filter(category="media_blocked").exists())

    def test_incident_recording_never_breaks_the_block(self):
        media_id = self.upload_image().data["id"]
        result = MagicMock()
        result.categories.model_dump.return_value = {"sexual_minors": True}
        response = MagicMock()
        response.results = [result]
        client = MagicMock()
        client.with_options.return_value.moderations.create.return_value = response

        with patch.dict("os.environ", {"OPENAI_API_KEY": "k"}), patch(
            "apps.chat.assist._get_client", return_value=client
        ), patch(
            "apps.safety.models.SafetyIncident.objects.create",
            side_effect=RuntimeError("db down"),
        ):
            self.assertEqual(moderation.moderate_image(media_id), "blocked")

        # The bytes are the harm; the bookkeeping failing must not save them.
        with self.assertRaises(storage.MissingBlob):
            storage.get(MessageMedia.objects.get(id=media_id).storage_key or "gone")


class ErasureEdgeTests(ChatMediaEdgeTestCase):
    def test_relationships_for_finds_both_sides(self):
        self.assertEqual(len(relationships_for(self.alex)), 1)
        self.assertEqual(len(relationships_for(self.sam)), 1)

    def test_a_user_with_nothing_to_erase(self):
        loner = User.objects.create_user(email="l@test.local", password="pw12345!")
        self.assertEqual(erase_media_for_user(loner), (0, 0))

    def test_failures_are_counted_not_raised(self):
        self.upload_image()

        with patch("apps.chat.storage.delete", side_effect=storage.StorageError("down")):
            destroyed, failed = erase_media_for_user(self.alex)

        self.assertEqual((destroyed, failed), (0, 1))

    def test_an_audit_failure_does_not_break_erasure(self):
        self.upload_image()

        with patch(
            "apps.audit.logger.AuditLogger.get_instance", side_effect=RuntimeError("no")
        ):
            destroyed, _failed = erase_media_for_user(self.alex)

        self.assertEqual(destroyed, 1)


class SummaryTests(ChatMediaEdgeTestCase):
    def test_a_missing_relationship_summarises_nothing(self):
        import uuid

        self.assertIsNone(refresh_thread_summary(uuid.uuid4()))

    def test_assist_off_summarises_nothing(self):
        ChatAssistSettings.objects.update_or_create(
            relationship=self.relationship, defaults={"assist_enabled": False}
        )
        self.assertIsNone(refresh_thread_summary(self.relationship.id))

    def test_an_empty_thread_summarises_nothing(self):
        self.assertIsNone(refresh_thread_summary(self.relationship.id))

    def test_a_thread_of_untranscribed_voice_notes_summarises_nothing(self):
        media_id = self.upload_voice().data["id"]
        self.send(kind="voice", media=media_id)

        # No transcripts yet, so there is no text to summarise — and inventing
        # one from "a voice note happened" would be worse than saying nothing.
        self.assertIsNone(refresh_thread_summary(self.relationship.id))

    def test_a_model_that_declines_writes_no_summary(self):
        self.send(body="hello")
        with patch("apps.chat.assist._complete", return_value=None):
            self.assertIsNone(refresh_thread_summary(self.relationship.id))
        self.assertFalse(ThreadSummary.objects.exists())

    def test_a_transcribed_voice_note_reaches_the_summary(self):
        media_id = self.upload_voice().data["id"]
        record = MessageMedia.objects.get(id=media_id)
        record.transcript = "i have been feeling distant"
        record.transcript_status = MessageMedia.TRANSCRIPT_OK
        record.save()
        self.send(kind="voice", media=media_id)

        with patch("apps.chat.assist._complete", return_value="They talked.") as complete:
            refresh_thread_summary(self.relationship.id)

        self.assertIn("i have been feeling distant", complete.call_args.args[1])
        self.assertEqual(
            ThreadSummary.objects.get(relationship=self.relationship).summary,
            "They talked.",
        )

    def test_staleness_counts_messages_since_the_last_summary(self):
        self.assertFalse(summary_is_stale(self.relationship))
        for i in range(21):
            self.send(body=f"message {i}")
        self.assertTrue(summary_is_stale(self.relationship))


class MessageTextTests(ChatMediaEdgeTestCase):
    def test_a_photo_with_no_caption_contributes_nothing(self):
        media_id = self.upload_image().data["id"]
        self.send(kind="image", media=media_id)

        message = CoupleMessage.objects.get(kind="image")

        # There is no point telling a text model that a photo happened.
        self.assertEqual(assist.message_text(message), "")

    def test_a_voice_note_with_no_media_row_contributes_nothing(self):
        media_id = self.upload_voice().data["id"]
        message_id = self.send(kind="voice", media=media_id).data["id"]
        MessageMedia.objects.get(id=media_id).destroy()
        CoupleMessage.objects.filter(id=message_id).update(media=None)

        message = CoupleMessage.objects.get(id=message_id)

        self.assertEqual(assist.message_text(message), "")
