import base64
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from django.conf import settings


def get_master_key():
    """Retrieve and decode the master key from settings."""
    master_key_hex = getattr(settings, "ENCRYPTION_MASTER_SECRET", None)
    if not master_key_hex:
        raise ValueError("ENCRYPTION_MASTER_SECRET not set in settings.")
    return bytes.fromhex(master_key_hex.strip())


def derive_user_key(user_id: str) -> bytes:
    """Derive a per-user key from master secret + user_id using HKDF."""
    master_key = get_master_key()
    hkdf = HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None, info=str(user_id).encode()
    )
    return hkdf.derive(master_key)


def encrypt(plaintext: str, user_id: str) -> str:
    """Returns base64(nonce + ciphertext). Nonce is random 12 bytes."""
    if not plaintext:
        return plaintext

    key = derive_user_key(user_id)
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()


def decrypt(ciphertext_b64: str, user_id: str) -> str:
    """Decrypt ciphertext using derived user key."""
    if not ciphertext_b64:
        return ciphertext_b64

    try:
        key = derive_user_key(user_id)
        aesgcm = AESGCM(key)
        raw = base64.b64decode(ciphertext_b64)
        nonce, ct = raw[:12], raw[12:]
        return aesgcm.decrypt(nonce, ct, None).decode()
    except Exception:
        return "[ENCRYPTION_ERROR]"


# ── Binary payloads ─────────────────────────────────────────────────────────
# Media blobs use the same cipher and the same derivation as message bodies —
# the scope is a relationship id, so a photo is readable by exactly whoever can
# read the thread it was sent in. What differs is the shape and the failure
# mode. Nothing is base64'd, because these are files rather than columns and a
# 33% size tax on every megabyte buys nothing.


class DecryptionError(Exception):
    """Raised when a blob will not decrypt: wrong scope, or tampered bytes."""


def encrypt_bytes(data: bytes, scope: str) -> bytes:
    """Encrypt raw bytes. Returns nonce(12) || ciphertext."""
    key = derive_user_key(scope)
    nonce = secrets.token_bytes(12)
    return nonce + AESGCM(key).encrypt(nonce, data, None)


def decrypt_bytes(blob: bytes, scope: str) -> bytes:
    """Inverse of :func:`encrypt_bytes`.

    Raises :class:`DecryptionError` rather than returning a sentinel the way
    :func:`decrypt` does. A body that will not decrypt can degrade to an empty
    bubble; a file that will not decrypt must not be handed to an image decoder
    or an audio player as if it were content.
    """
    if len(blob) <= 12:
        raise DecryptionError("blob too short to contain a nonce")
    try:
        key = derive_user_key(scope)
        return AESGCM(key).decrypt(blob[:12], blob[12:], None)
    except Exception as exc:
        raise DecryptionError("could not decrypt blob") from exc
