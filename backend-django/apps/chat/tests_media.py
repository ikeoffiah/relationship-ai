"""Tests for photos and voice notes in the couple thread.

Grouped by the property under test, following tests.py. The things most likely
to hurt someone here are not "does upload work" but: a photo reaching a third
party, GPS coordinates surviving an upload, and bytes outliving the moment
somebody chose to delete them.
"""

import io
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from apps.chat import media as media_processing
from apps.chat import storage
from apps.chat.models import CoupleMessage, MessageMedia
from apps.chat.tasks import sweep_orphan_media
from apps.relationships.models import Relationship
from utils.encryption import DecryptionError, decrypt_bytes, encrypt_bytes

User = get_user_model()


def jpeg_bytes(size=(64, 48), colour=(200, 120, 90)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, colour).save(buffer, format="JPEG")
    return buffer.getvalue()


#: EXIF tag numbers, so the fixture needs no extra dependency.
_EXIF_MAKE = 0x010F
_EXIF_GPS_IFD = 0x8825
_GPS_LAT_REF, _GPS_LAT = 1, 2
_GPS_LON_REF, _GPS_LON = 3, 4


def jpeg_with_gps() -> bytes:
    """A JPEG carrying GPS EXIF, as a phone camera produces."""
    image = Image.new("RGB", (64, 48), (10, 20, 30))
    exif = image.getexif()
    exif[_EXIF_MAKE] = "TestPhone"
    gps = exif.get_ifd(_EXIF_GPS_IFD)
    gps[_GPS_LAT_REF] = "N"
    gps[_GPS_LAT] = (51.0, 30.0, 0.0)
    gps[_GPS_LON_REF] = "W"
    gps[_GPS_LON] = (0.0, 7.0, 0.0)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


def m4a_bytes(payload_size=2048) -> bytes:
    """Enough of an MP4 container header to satisfy the sniffer."""
    return b"\x00\x00\x00\x20ftypM4A " + b"\x00" * payload_size


class MediaTestCase(TestCase):
    def setUp(self):
        self.alex = User.objects.create_user(email="alex@test.local", password="pw12345!")
        self.sam = User.objects.create_user(email="sam@test.local", password="pw12345!")
        self.stranger = User.objects.create_user(
            email="stranger@test.local", password="pw12345!"
        )
        self.relationship = Relationship.objects.create(
            partner_a=self.alex, partner_b=self.sam, status="active"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.alex)

        patcher = patch("apps.chat.views.realtime.publish", return_value=True)
        self.publish = patcher.start()
        self.addCleanup(patcher.stop)

        # Every test runs against the in-memory backend, freshly emptied, so
        # nothing leaks between cases and no test needs a Cloudinary account.
        storage.reset_backend()
        self.addCleanup(storage.reset_backend)

    # helpers
    def upload_url(self, relationship=None):
        return reverse("chat-media-upload", args=[(relationship or self.relationship).id])

    def send_url(self, relationship=None):
        return reverse("chat-send", args=[(relationship or self.relationship).id])

    def upload_image(self, blob=None, **extra):
        upload = io.BytesIO(blob if blob is not None else jpeg_bytes())
        upload.name = "photo.jpg"
        return self.client.post(
            self.upload_url(),
            {"kind": "image", "file": upload, **extra},
            format="multipart",
        )

    def upload_voice(self, blob=None, duration_ms=5000, **extra):
        upload = io.BytesIO(blob if blob is not None else m4a_bytes())
        upload.name = "note.m4a"
        return self.client.post(
            self.upload_url(),
            {"kind": "voice", "file": upload, "duration_ms": duration_ms, **extra},
            format="multipart",
        )


class ByteEncryptionTests(TestCase):
    """The primitive everything else rests on."""

    def test_round_trip(self):
        blob = b"\x00\xff" * 5000
        self.assertEqual(decrypt_bytes(encrypt_bytes(blob, "scope-a"), "scope-a"), blob)

    def test_each_encryption_uses_a_fresh_nonce(self):
        blob = b"same input"
        self.assertNotEqual(encrypt_bytes(blob, "s"), encrypt_bytes(blob, "s"))

    def test_wrong_scope_cannot_decrypt(self):
        blob = encrypt_bytes(b"a private photo", "relationship-a")
        with self.assertRaises(DecryptionError):
            decrypt_bytes(blob, "relationship-b")

    def test_tampered_ciphertext_raises_rather_than_returning_garbage(self):
        blob = bytearray(encrypt_bytes(b"a private photo", "s"))
        blob[-1] ^= 0x01
        with self.assertRaises(DecryptionError):
            decrypt_bytes(bytes(blob), "s")

    def test_truncated_blob_raises(self):
        with self.assertRaises(DecryptionError):
            decrypt_bytes(b"short", "s")


class ImageProcessingTests(TestCase):
    """What we store is not what was uploaded."""

    def test_gps_metadata_does_not_survive(self):
        original = jpeg_with_gps()
        self.assertTrue(media_processing.has_metadata(original), "fixture is not testing anything")

        stored, _thumb, _w, _h = media_processing.process_image(original)

        self.assertFalse(media_processing.has_metadata(stored))

    def test_large_images_are_downscaled(self):
        stored, _thumb, width, height = media_processing.process_image(
            jpeg_bytes(size=(4000, 3000))
        )
        self.assertLessEqual(max(width, height), media_processing.IMAGE_MAX_EDGE)
        self.assertLessEqual(max(Image.open(io.BytesIO(stored)).size), media_processing.IMAGE_MAX_EDGE)

    def test_thumbnail_is_smaller_than_the_image(self):
        stored, thumb, _w, _h = media_processing.process_image(jpeg_bytes(size=(1200, 900)))
        self.assertLess(len(thumb), len(stored))
        self.assertLessEqual(max(Image.open(io.BytesIO(thumb)).size), media_processing.THUMB_MAX_EDGE)

    def test_a_file_that_is_not_an_image_is_rejected(self):
        with self.assertRaises(media_processing.MediaRejected):
            media_processing.process_image(b"MZ\x90\x00 this is an executable")

    def test_a_renamed_executable_is_rejected_on_content_not_extension(self):
        with self.assertRaises(media_processing.MediaRejected):
            media_processing.sniff_image(b"#!/bin/sh\nrm -rf /")

    def test_oversized_image_is_rejected(self):
        with self.assertRaises(media_processing.MediaRejected):
            media_processing.process_image(b"\xff\xd8\xff" + b"\x00" * media_processing.MAX_IMAGE_BYTES)


class VoiceProcessingTests(TestCase):
    def test_accepts_an_mp4_container(self):
        blob, mime = media_processing.process_voice(m4a_bytes(), 5000)
        self.assertEqual(mime, "audio/mp4")
        self.assertEqual(blob, m4a_bytes())

    def test_rejects_audio_over_two_minutes(self):
        with self.assertRaises(media_processing.MediaRejected):
            media_processing.process_voice(m4a_bytes(), media_processing.MAX_VOICE_MS + 1)

    def test_rejects_a_missing_duration(self):
        with self.assertRaises(media_processing.MediaRejected):
            media_processing.process_voice(m4a_bytes(), 0)

    def test_rejects_something_that_is_not_audio(self):
        with self.assertRaises(media_processing.MediaRejected):
            media_processing.process_voice(jpeg_bytes(), 5000)

    def test_waveform_is_clamped_and_bounded(self):
        normalised = media_processing.normalise_waveform([-5, 50, 500, "x"] * 40)
        self.assertLessEqual(len(normalised), media_processing.WAVEFORM_BUCKETS)
        self.assertTrue(all(0 <= v <= 100 for v in normalised))

    def test_a_junk_waveform_degrades_rather_than_raising(self):
        self.assertEqual(media_processing.normalise_waveform("not a list"), [])


class UploadTests(MediaTestCase):
    def test_uploading_an_image_stores_ciphertext_only(self):
        response = self.upload_image()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        record = MessageMedia.objects.get(id=response.data["id"])
        raw = storage.get(record.storage_key)
        # The bytes in storage must not be a readable JPEG.
        self.assertFalse(raw.startswith(b"\xff\xd8\xff"))
        self.assertTrue(decrypt_bytes(raw, str(self.relationship.id)).startswith(b"\xff\xd8\xff"))

    def test_uploaded_image_gets_a_thumbnail(self):
        response = self.upload_image()
        record = MessageMedia.objects.get(id=response.data["id"])
        self.assertTrue(record.thumb_key)
        self.assertIsNotNone(response.data["thumb_url"])

    def test_uploading_a_voice_note_records_duration_and_waveform(self):
        response = self.upload_voice(duration_ms=8200, waveform="[10, 90, 40]")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["duration_ms"], 8200)
        self.assertEqual(response.data["waveform"], [10, 90, 40])
        # Voice has no thumbnail.
        self.assertIsNone(response.data["thumb_url"])

    def test_upload_arrives_unattached(self):
        response = self.upload_image()
        self.assertIsNone(MessageMedia.objects.get(id=response.data["id"]).attached_at)

    def test_a_stranger_cannot_upload_into_the_thread(self):
        self.client.force_authenticate(user=self.stranger)
        self.assertEqual(self.upload_image().status_code, status.HTTP_404_NOT_FOUND)

    def test_upload_rejects_a_file_that_is_not_what_it_claims(self):
        response = self.upload_image(blob=b"MZ\x90\x00 definitely not a photo")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_rejects_an_oversized_file(self):
        oversize = b"\xff\xd8\xff" + b"\x00" * (media_processing.MAX_IMAGE_BYTES + 1)
        response = self.upload_image(blob=oversize)
        self.assertEqual(response.status_code, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    def test_a_storage_failure_leaves_nothing_behind(self):
        with patch("apps.chat.views.storage.put", side_effect=storage.StorageError("down")):
            response = self.upload_image()

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(MessageMedia.objects.count(), 0)


class MediaDownloadTests(MediaTestCase):
    def setUp(self):
        super().setUp()
        self.media_id = self.upload_image().data["id"]

    def blob_url(self, media_id=None):
        return reverse("chat-media-blob", args=[media_id or self.media_id])

    def test_a_partner_can_read_the_decrypted_photo(self):
        self.client.force_authenticate(user=self.sam)
        response = self.client.get(self.blob_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.content.startswith(b"\xff\xd8\xff"))

    def test_plaintext_is_never_cacheable(self):
        response = self.client.get(self.blob_url())
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_a_stranger_cannot_read_the_photo(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(self.blob_url())
        # 404, not 403: probing must not confirm the photo exists.
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_an_unknown_id_is_a_404(self):
        self.assertEqual(
            self.client.get(self.blob_url(uuid.uuid4())).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_a_row_whose_bytes_are_gone_degrades_to_404(self):
        record = MessageMedia.objects.get(id=self.media_id)
        storage.delete(record.storage_key)

        response = self.client.get(self.blob_url())

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_thumbnail_is_served_separately(self):
        response = self.client.get(reverse("chat-media-thumb", args=[self.media_id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.content.startswith(b"\xff\xd8\xff"))


class SendingMediaTests(MediaTestCase):
    def send(self, **payload):
        return self.client.post(self.send_url(), payload, format="json")

    def test_sending_a_photo_attaches_it(self):
        media_id = self.upload_image().data["id"]

        response = self.send(kind="image", media=media_id, client_id="c1")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["media"]["id"], str(media_id))
        self.assertIsNotNone(MessageMedia.objects.get(id=media_id).attached_at)

    def test_an_image_can_carry_a_caption(self):
        media_id = self.upload_image().data["id"]
        response = self.send(kind="image", media=media_id, body="us, last summer")
        self.assertEqual(response.data["body"], "us, last summer")

    def test_a_voice_note_needs_no_body(self):
        media_id = self.upload_voice().data["id"]
        response = self.send(kind="voice", media=media_id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_a_media_message_without_media_is_rejected(self):
        response = self.send(kind="image", body="where is it")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_media_from_another_couple_cannot_be_attached(self):
        other = Relationship.objects.create(
            partner_a=self.stranger,
            partner_b=User.objects.create_user(email="x@test.local", password="pw12345!"),
            status="active",
        )
        theirs = MessageMedia.objects.create(
            relationship=other,
            uploader=self.stranger,
            kind=MessageMedia.KIND_IMAGE,
            storage_key="chat/other/key",
            mime="image/jpeg",
        )

        response = self.send(kind="image", media=str(theirs.id))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_kind_must_match_the_upload(self):
        voice_id = self.upload_voice().data["id"]
        response = self.send(kind="image", media=voice_id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_one_upload_cannot_be_sent_twice(self):
        media_id = self.upload_image().data["id"]
        self.send(kind="image", media=media_id, client_id="first")

        response = self.send(kind="image", media=media_id, client_id="second")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_a_retried_send_does_not_double_post(self):
        media_id = self.upload_image().data["id"]
        first = self.send(kind="image", media=media_id, client_id="same")
        second = self.send(kind="image", media=media_id, client_id="same")

        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(CoupleMessage.objects.filter(kind="image").count(), 1)

    def test_a_reply_quoting_a_photo_carries_its_thumbnail(self):
        media_id = self.upload_image().data["id"]
        photo_id = self.send(kind="image", media=media_id).data["id"]

        reply = self.send(body="that one is lovely", reply_to=photo_id)

        self.assertIsNotNone(reply.data["reply_to"]["thumb_url"])

    def test_a_quote_of_a_destroyed_photo_shows_no_thumbnail(self):
        media_id = self.upload_image().data["id"]
        photo_id = self.send(kind="image", media=media_id).data["id"]
        reply_id = self.send(body="that one", reply_to=photo_id).data["id"]
        self.client.delete(reverse("chat-delete", args=[photo_id]))

        listing = self.client.get(reverse("chat-messages", args=[self.relationship.id]))
        reply = next(m for m in listing.data["results"] if m["id"] == str(reply_id))

        self.assertIsNone(reply["reply_to"]["thumb_url"])

    def test_the_thread_lists_media_messages(self):
        media_id = self.upload_image().data["id"]
        self.send(kind="image", media=media_id)

        response = self.client.get(reverse("chat-messages", args=[self.relationship.id]))

        # The list is newest-first.
        message = response.data["results"][0]
        self.assertEqual(message["kind"], "image")
        self.assertEqual(message["media"]["id"], str(media_id))


class MediaDeletionTests(MediaTestCase):
    """Deleting media must destroy bytes, not just hide a row."""

    def test_deleting_a_photo_message_destroys_the_blob(self):
        media_id = self.upload_image().data["id"]
        record = MessageMedia.objects.get(id=media_id)
        keys = record.storage_keys()
        message_id = self.client.post(
            self.send_url(), {"kind": "image", "media": media_id}, format="json"
        ).data["id"]

        self.client.delete(reverse("chat-delete", args=[message_id]))

        for key in keys:
            with self.assertRaises(storage.MissingBlob):
                storage.get(key)

    def test_the_tombstone_survives_so_replies_still_render(self):
        media_id = self.upload_image().data["id"]
        message_id = self.client.post(
            self.send_url(), {"kind": "image", "media": media_id}, format="json"
        ).data["id"]

        response = self.client.delete(reverse("chat-delete", args=[message_id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(CoupleMessage.objects.filter(id=message_id).exists())
        self.assertIsNone(response.data["media"])

    def test_destroy_clears_the_transcript_with_the_audio(self):
        record = MessageMedia.objects.get(id=self.upload_voice().data["id"])
        record.transcript = "something said out loud"
        record.transcript_status = MessageMedia.TRANSCRIPT_OK
        record.save()

        record.destroy()

        record.refresh_from_db()
        self.assertEqual(record.transcript, "")
        self.assertEqual(record.transcript_status, MessageMedia.TRANSCRIPT_SKIPPED)


class OrphanSweepTests(MediaTestCase):
    """An upload whose send never happened is storage nobody can find again."""

    def age(self, media_id, hours):
        MessageMedia.objects.filter(id=media_id).update(
            created_at=timezone.now() - timedelta(hours=hours)
        )

    def test_old_unattached_uploads_are_destroyed(self):
        media_id = self.upload_image().data["id"]
        keys = MessageMedia.objects.get(id=media_id).storage_keys()
        self.age(media_id, 25)

        self.assertEqual(sweep_orphan_media(), 1)

        for key in keys:
            with self.assertRaises(storage.MissingBlob):
                storage.get(key)

    def test_recent_uploads_are_left_alone(self):
        media_id = self.upload_image().data["id"]
        self.age(media_id, 1)

        self.assertEqual(sweep_orphan_media(), 0)
        self.assertIsNone(MessageMedia.objects.get(id=media_id).deleted_at)

    def test_attached_media_is_never_swept(self):
        media_id = self.upload_image().data["id"]
        self.client.post(self.send_url(), {"kind": "image", "media": media_id}, format="json")
        self.age(media_id, 200)

        self.assertEqual(sweep_orphan_media(), 0)
        self.assertIsNone(MessageMedia.objects.get(id=media_id).deleted_at)

    def test_a_delete_that_could_not_reach_storage_is_swept_later(self):
        """The leak that keying the sweep off `attached_at` would have left."""
        media_id = self.upload_image().data["id"]
        keys = MessageMedia.objects.get(id=media_id).storage_keys()
        message_id = self.client.post(
            self.send_url(), {"kind": "image", "media": media_id}, format="json"
        ).data["id"]

        with patch("apps.chat.storage.delete", side_effect=storage.StorageError("down")):
            response = self.client.delete(reverse("chat-delete", args=[message_id]))

        # The user's delete still succeeded — the bubble is a tombstone.
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # ...but the bytes are still there, now referenced by nothing.
        self.assertTrue(storage.get(keys[0]))
        self.assertFalse(CoupleMessage.objects.filter(media_id=media_id).exists())

        self.age(media_id, 25)
        self.assertEqual(sweep_orphan_media(), 1)
        for key in keys:
            with self.assertRaises(storage.MissingBlob):
                storage.get(key)

    def test_one_failure_does_not_abandon_the_rest(self):
        first = self.upload_image().data["id"]
        second = self.upload_image().data["id"]
        self.age(first, 25)
        self.age(second, 25)

        real_delete = storage.delete
        calls = {"n": 0}

        def flaky(key):
            calls["n"] += 1
            if calls["n"] == 1:
                raise storage.StorageError("transient")
            return real_delete(key)

        # Patched on the storage module rather than on models, because
        # MessageMedia.destroy imports it at call time.
        with patch("apps.chat.storage.delete", side_effect=flaky):
            swept = sweep_orphan_media()

        self.assertEqual(swept, 1)
        # The one that failed is still unattached, so the next run retries it.
        self.assertEqual(
            MessageMedia.objects.filter(
                attached_at__isnull=True, deleted_at__isnull=True
            ).count(),
            1,
        )
