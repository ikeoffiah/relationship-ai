"""Where encrypted media blobs live.

The entire vendor surface, deliberately three functions wide. Everything above
this module deals in opaque keys and ciphertext, so swapping Cloudinary for S3
or B2 is a new backend here and nothing else.

Cloudinary holds ciphertext and nothing else. It cannot transform what it
cannot read, so uploads go up as ``resource_type="raw"`` and every transform,
thumbnail and transcode happens on our side of the boundary — see
``docs/chat-media.md`` §1 for why that trade is the right way round.

Clients never talk to this. They *cannot*: the key is derived from the master
secret and can never ship to a device, so reads are proxied and decrypted by
Django on the way out.
"""

import hashlib
import hmac
import logging
import uuid

import requests
from django.conf import settings

log = logging.getLogger(__name__)

# Cloudinary rejects a signed upload whose timestamp has drifted too far, and
# a slow worker should fail loudly rather than silently retry forever.
_UPLOAD_TIMEOUT = 30.0
_FETCH_TIMEOUT = 30.0


class StorageError(Exception):
    """Any failure to put, get or delete a blob."""


class MissingBlob(StorageError):
    """The key is not in storage. Renders as an unavailable bubble, not a 500."""


def key_for(relationship_id, suffix: str = "") -> str:
    """A fresh opaque key.

    Random, so it reveals nothing and needs no encryption of its own; scoped by
    relationship so a stray bucket listing is at least sortable when erasure
    comes calling.
    """
    return f"chat/{relationship_id}/{uuid.uuid4().hex}{suffix}"


# ── Backends ────────────────────────────────────────────────────────────────


class InMemoryBackend:
    """The backend used by tests, and whenever Cloudinary is unconfigured.

    Keeping this in the production module rather than in the test tree is
    deliberate: it means the whole media path — upload, encrypt, store, fetch,
    decrypt, serve — is exercised by the suite without a network call or a
    vendor account, and a developer with no Cloudinary credentials still gets a
    working local app instead of a 500.
    """

    def __init__(self):
        self._blobs: dict[str, bytes] = {}

    def put(self, key: str, blob: bytes) -> None:
        self._blobs[key] = blob

    def get(self, key: str) -> bytes:
        try:
            return self._blobs[key]
        except KeyError:
            raise MissingBlob(key) from None

    def delete(self, key: str) -> None:
        self._blobs.pop(key, None)


class CloudinaryBackend:
    """Signed upload, authenticated delivery, raw resource type.

    ``type=authenticated`` is defence in depth. The blob is useless without a
    key we never publish, but a guessable public id should not be publicly
    fetchable either.

    Signing goes through Cloudinary's own SDK rather than being hand-rolled.
    A subtly wrong signature does not raise — it produces a URL that 401s or,
    worse, one that is less private than intended — so this is not a place to
    reimplement someone else's scheme from the docs.
    """

    def __init__(self, cloud_name: str, api_key: str, api_secret: str):
        import cloudinary

        self._config = cloudinary.Config()
        self._config.update(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )

    def put(self, key: str, blob: bytes) -> None:
        import cloudinary.uploader

        try:
            cloudinary.uploader.upload(
                blob,
                public_id=key,
                resource_type="raw",
                type="authenticated",
                overwrite=False,
                timeout=_UPLOAD_TIMEOUT,
            )
        except Exception as exc:
            raise StorageError(f"upload failed for {key}") from exc

    def get(self, key: str) -> bytes:
        """Fetch through the signed delivery URL, which is CDN-backed.

        Caching at the edge is wanted here: keys are random and a blob is never
        rewritten, so a cached copy is always the right copy. The one surprise
        is that a *destroyed* asset keeps being served from the edge for a
        while after ``delete`` — see the note there. Nothing in the app can hit
        that, because destroying media clears the keys that would ask for it.
        """
        import cloudinary.utils

        url, _ = cloudinary.utils.cloudinary_url(
            key, resource_type="raw", type="authenticated", sign_url=True
        )
        try:
            response = requests.get(url, timeout=_FETCH_TIMEOUT)
        except requests.RequestException as exc:
            raise StorageError(f"fetch failed for {key}") from exc
        if response.status_code == 404:
            raise MissingBlob(key)
        if not response.ok:
            raise StorageError(f"fetch failed for {key}: {response.status_code}")
        return response.content

    def delete(self, key: str) -> None:
        """Destroy the stored asset.

        ``type="authenticated"`` is not optional here. Uploads are stored under
        that delivery type, and ``destroy`` without it addresses a different
        asset entirely: it returns ``{"result": "not found"}`` and reports
        success while the real blob stays exactly where it was. That is the one
        failure this module must never have, so the type is passed explicitly
        and a "not found" is only ever accepted as *already gone*.

        ``invalidate`` asks for a CDN purge, which is asynchronous: for a short
        window after this returns, the signed delivery URL can still serve the
        bytes from an edge cache even though the asset itself is gone (the
        Admin API 404s immediately). That is survivable because destroying
        media clears the keys, so nothing will ask for it again.
        """
        import cloudinary.uploader

        try:
            result = cloudinary.uploader.destroy(
                key, resource_type="raw", type="authenticated", invalidate=True
            )
        except Exception as exc:
            # Deletion is called from erasure paths and from the orphan sweep.
            # Both must be retryable, so this raises rather than swallowing —
            # a blob we believe is gone but is not is the one lie this module
            # must never tell.
            raise StorageError(f"delete failed for {key}") from exc
        # "not found" is success: the caller wanted the bytes gone.
        if result.get("result") not in ("ok", "not found"):
            raise StorageError(f"delete failed for {key}: {result.get('result')}")


# ── Resolution ──────────────────────────────────────────────────────────────

_backend = None


def get_backend():
    """The configured backend, built once.

    Falls back to in-memory when Cloudinary is unconfigured, which keeps tests
    and a fresh checkout working. In-memory storage does not survive a restart,
    so production is expected to set the three env vars; ``configured()`` lets
    a health check say so out loud.
    """
    global _backend
    if _backend is None:
        if configured():
            _backend = CloudinaryBackend(
                settings.CLOUDINARY_CLOUD_NAME,
                settings.CLOUDINARY_API_KEY,
                settings.CLOUDINARY_API_SECRET,
            )
        else:
            log.warning("cloudinary_unconfigured: chat media is using in-memory storage")
            _backend = InMemoryBackend()
    return _backend


def configured() -> bool:
    return all(
        bool(getattr(settings, name, None))
        for name in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")
    )


def reset_backend() -> None:
    """Drop the cached backend. For tests and for settings overrides."""
    global _backend
    _backend = None


def put(key: str, blob: bytes) -> None:
    get_backend().put(key, blob)


def get(key: str) -> bytes:
    return get_backend().get(key)


def delete(key: str) -> None:
    get_backend().delete(key)


def checksum(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def keys_match(a: str, b: str) -> bool:
    """Constant-time compare, for anywhere a key is checked against user input."""
    return hmac.compare_digest(a, b)
