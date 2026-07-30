"""The storage backend, including the Cloudinary path the suite never takes.

Every other test in this app runs against the in-memory backend, deliberately:
with real credentials in the environment the suite would otherwise upload to
and delete from a live account on every run. That leaves the vendor path
untested, which is precisely where the one bug that matters lives — a `destroy`
that reports success while the blob stays put.

So the SDK is mocked here. That is weaker than the real thing, and it is worth
saying why out loud: these tests assert against our *model* of Cloudinary, not
against Cloudinary. They catch a regression in our own logic — the wrong
resource type, a swallowed failure, a "not found" treated as an error — and
they cannot catch the SDK behaving differently than we believe. The live smoke
check is what covers that, and it needs credentials.
"""

from unittest.mock import MagicMock, patch

import requests
from django.test import SimpleTestCase, override_settings

from apps.chat import storage


class KeyTests(SimpleTestCase):
    def test_keys_are_scoped_and_unique(self):
        first = storage.key_for("rel-1")
        second = storage.key_for("rel-1")

        self.assertTrue(first.startswith("chat/rel-1/"))
        self.assertNotEqual(first, second)

    def test_a_suffix_distinguishes_the_thumbnail(self):
        self.assertTrue(storage.key_for("rel-1", suffix="-thumb").endswith("-thumb"))

    def test_checksum_is_stable(self):
        self.assertEqual(storage.checksum(b"abc"), storage.checksum(b"abc"))
        self.assertNotEqual(storage.checksum(b"abc"), storage.checksum(b"abd"))

    def test_key_comparison_is_constant_time(self):
        self.assertTrue(storage.keys_match("a/b", "a/b"))
        self.assertFalse(storage.keys_match("a/b", "a/c"))


class InMemoryBackendTests(SimpleTestCase):
    def setUp(self):
        self.backend = storage.InMemoryBackend()

    def test_round_trip(self):
        self.backend.put("k", b"bytes")
        self.assertEqual(self.backend.get("k"), b"bytes")

    def test_a_missing_key_raises_missing_blob(self):
        with self.assertRaises(storage.MissingBlob):
            self.backend.get("nope")

    def test_delete_is_idempotent(self):
        self.backend.put("k", b"bytes")
        self.backend.delete("k")
        # Deleting something already gone is success: the caller wanted it gone.
        self.backend.delete("k")
        with self.assertRaises(storage.MissingBlob):
            self.backend.get("k")


@override_settings(
    CLOUDINARY_CLOUD_NAME="test-cloud",
    CLOUDINARY_API_KEY="key",
    CLOUDINARY_API_SECRET="secret",
)
class CloudinaryBackendTests(SimpleTestCase):
    def setUp(self):
        storage.reset_backend()
        self.addCleanup(storage.reset_backend)
        config = patch("cloudinary.Config")
        config.start()
        self.addCleanup(config.stop)
        self.backend = storage.CloudinaryBackend("test-cloud", "key", "secret")

    # ── put ─────────────────────────────────────────────────────────────────

    def test_upload_uses_raw_and_authenticated(self):
        with patch("cloudinary.uploader.upload") as upload:
            self.backend.put("chat/r/abc", b"ciphertext")

        kwargs = upload.call_args.kwargs
        # Raw because the blob is ciphertext: Cloudinary cannot transform what
        # it cannot read, and asking it to would corrupt the file.
        self.assertEqual(kwargs["resource_type"], "raw")
        self.assertEqual(kwargs["type"], "authenticated")
        self.assertEqual(kwargs["public_id"], "chat/r/abc")
        self.assertFalse(kwargs["overwrite"])

    def test_an_upload_failure_becomes_a_storage_error(self):
        with patch("cloudinary.uploader.upload", side_effect=RuntimeError("boom")):
            with self.assertRaises(storage.StorageError):
                self.backend.put("k", b"x")

    # ── get ─────────────────────────────────────────────────────────────────

    def _response(self, status_code=200, content=b"ciphertext"):
        response = MagicMock()
        response.status_code = status_code
        response.ok = 200 <= status_code < 300
        response.content = content
        return response

    def test_fetch_signs_the_delivery_url(self):
        with patch(
            "cloudinary.utils.cloudinary_url", return_value=("https://res/x", {})
        ) as url, patch("requests.get", return_value=self._response()) as get:
            self.assertEqual(self.backend.get("k"), b"ciphertext")

        self.assertTrue(url.call_args.kwargs["sign_url"])
        self.assertEqual(url.call_args.kwargs["type"], "authenticated")
        get.assert_called_once()

    def test_a_404_is_a_missing_blob_not_an_error(self):
        with patch("cloudinary.utils.cloudinary_url", return_value=("u", {})), patch(
            "requests.get", return_value=self._response(status_code=404)
        ):
            with self.assertRaises(storage.MissingBlob):
                self.backend.get("k")

    def test_another_bad_status_is_a_storage_error(self):
        with patch("cloudinary.utils.cloudinary_url", return_value=("u", {})), patch(
            "requests.get", return_value=self._response(status_code=500)
        ):
            with self.assertRaises(storage.StorageError):
                self.backend.get("k")

    def test_a_network_failure_is_a_storage_error(self):
        with patch("cloudinary.utils.cloudinary_url", return_value=("u", {})), patch(
            "requests.get", side_effect=requests.RequestException("dns")
        ):
            with self.assertRaises(storage.StorageError):
                self.backend.get("k")

    # ── delete ──────────────────────────────────────────────────────────────

    def test_destroy_passes_the_authenticated_type(self):
        """The bug this exists for.

        Without ``type="authenticated"`` Cloudinary addresses a different asset,
        answers ``{"result": "not found"}``, and reports success while the real
        blob stays exactly where it was.
        """
        with patch(
            "cloudinary.uploader.destroy", return_value={"result": "ok"}
        ) as destroy:
            self.backend.delete("chat/r/abc")

        kwargs = destroy.call_args.kwargs
        self.assertEqual(kwargs["type"], "authenticated")
        self.assertEqual(kwargs["resource_type"], "raw")
        self.assertTrue(kwargs["invalidate"])

    def test_not_found_counts_as_already_gone(self):
        with patch("cloudinary.uploader.destroy", return_value={"result": "not found"}):
            self.backend.delete("k")  # must not raise

    def test_any_other_result_is_a_failure(self):
        # A delete that quietly did nothing is the one lie this module cannot
        # tell, so an unrecognised result is an error rather than a shrug.
        with patch("cloudinary.uploader.destroy", return_value={"result": "error"}):
            with self.assertRaises(storage.StorageError):
                self.backend.delete("k")

    def test_a_destroy_exception_is_a_storage_error(self):
        with patch("cloudinary.uploader.destroy", side_effect=RuntimeError("boom")):
            with self.assertRaises(storage.StorageError):
                self.backend.delete("k")


class BackendResolutionTests(SimpleTestCase):
    def setUp(self):
        storage.reset_backend()
        self.addCleanup(storage.reset_backend)

    @override_settings(
        CLOUDINARY_CLOUD_NAME=None, CLOUDINARY_API_KEY=None, CLOUDINARY_API_SECRET=None
    )
    def test_unconfigured_falls_back_to_memory(self):
        self.assertFalse(storage.configured())
        self.assertIsInstance(storage.get_backend(), storage.InMemoryBackend)

    @override_settings(
        CLOUDINARY_CLOUD_NAME="c", CLOUDINARY_API_KEY="k", CLOUDINARY_API_SECRET=None
    )
    def test_partial_configuration_is_not_configured(self):
        # Two of three credentials is a misconfiguration, not a half-working
        # vendor — falling back is safer than failing at the first upload.
        self.assertFalse(storage.configured())

    @override_settings(
        CLOUDINARY_CLOUD_NAME="c", CLOUDINARY_API_KEY="k", CLOUDINARY_API_SECRET="s"
    )
    def test_configured_builds_the_cloudinary_backend_once(self):
        with patch("cloudinary.Config"):
            first = storage.get_backend()
            second = storage.get_backend()

        self.assertIsInstance(first, storage.CloudinaryBackend)
        self.assertIs(first, second)

    @override_settings(
        CLOUDINARY_CLOUD_NAME=None, CLOUDINARY_API_KEY=None, CLOUDINARY_API_SECRET=None
    )
    def test_module_functions_delegate_to_the_backend(self):
        storage.put("k", b"v")
        self.assertEqual(storage.get("k"), b"v")
        storage.delete("k")
        with self.assertRaises(storage.MissingBlob):
            storage.get("k")
