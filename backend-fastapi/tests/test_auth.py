"""
Tests for app/auth.py.

These cover the properties the previous placeholders did not have: that
identity comes from a signed token, that forged or expired tokens are refused,
and that a missing secret fails closed rather than open.
"""

import jwt
import pytest
from fastapi import HTTPException

from app.auth import ALGORITHM, decode_token, get_current_user, get_current_user_id
from tests.conftest import TEST_SECRET, make_token

USER = "11111111-1111-1111-1111-111111111111"


class FakeRequest:
    def __init__(self, headers=None):
        self.headers = headers or {}


def bearer(token: str) -> FakeRequest:
    return FakeRequest({"Authorization": f"Bearer {token}"})


# ---------------------------------------------------------------------------
# happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_valid_token_yields_its_subject():
    assert await get_current_user_id(bearer(make_token(USER))) == USER


@pytest.mark.asyncio
async def test_get_current_user_returns_user_object():
    user = await get_current_user(bearer(make_token(USER)))
    assert str(user.id) == USER


def test_decode_returns_claims():
    claims = decode_token(make_token(USER, scope=["user"]))
    assert claims["sub"] == USER
    assert claims["scope"] == ["user"]


# ---------------------------------------------------------------------------
# rejection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_token_signed_with_another_secret_is_rejected():
    """The core property: an attacker cannot mint their own identity."""
    forged = make_token(USER, secret="attacker-secret")
    with pytest.raises(HTTPException) as exc:
        await get_current_user_id(bearer(forged))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_expired_token_is_rejected():
    with pytest.raises(HTTPException) as exc:
        await get_current_user_id(bearer(make_token(USER, expires_in=-60)))
    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_unsigned_alg_none_token_is_rejected():
    """`alg: none` must not be accepted as a signature bypass."""
    unsigned = jwt.encode({"sub": USER}, key="", algorithm="none")
    with pytest.raises(HTTPException) as exc:
        await get_current_user_id(bearer(unsigned))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_token_without_subject_is_rejected():
    token = jwt.encode({"scope": ["user"]}, TEST_SECRET, algorithm=ALGORITHM)
    with pytest.raises(HTTPException) as exc:
        await get_current_user_id(bearer(token))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_non_uuid_subject_is_rejected_for_user_objects():
    with pytest.raises(HTTPException) as exc:
        await get_current_user(bearer(make_token("not-a-uuid")))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": ""},
        {"Authorization": "Bearer"},
        {"Authorization": "Bearer   "},
        {"Authorization": "Basic abc123"},
        {"Authorization": "token abc123"},
    ],
)
async def test_missing_or_malformed_authorization_is_rejected(headers):
    with pytest.raises(HTTPException) as exc:
        await get_current_user_id(FakeRequest(headers))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_x_user_id_header_is_no_longer_trusted():
    """The old scheme let any caller assert any identity."""
    with pytest.raises(HTTPException) as exc:
        await get_current_user_id(FakeRequest({"X-User-ID": "someone-else"}))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_bearer_scheme_is_case_insensitive():
    token = make_token(USER)
    assert await get_current_user_id(FakeRequest({"Authorization": f"bearer {token}"})) == USER


# ---------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------

def test_missing_secret_fails_closed(monkeypatch):
    """Without a secret, verification must error rather than accept anything."""
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        decode_token(make_token(USER))
    assert exc.value.status_code == 500


# ---------------------------------------------------------------------------
# key fingerprints
#
# These exist to make one specific failure loud. Django signs tokens with its
# SECRET_KEY and this service verifies with its own; nothing checks they agree,
# and when they diverged every WebSocket rejected every token as a bare HTTP
# 403 that read as a permissions bug. A fingerprint each service can log makes
# the diagnosis a two-second comparison.
# ---------------------------------------------------------------------------


class TestKeyFingerprint:
    def test_the_same_key_gives_the_same_fingerprint(self):
        from app.auth import key_fingerprint

        assert key_fingerprint("shared-key") == key_fingerprint("shared-key")

    def test_different_keys_give_different_fingerprints(self):
        """The whole point. If this ever collided, two mismatched services
        would report agreement and the check would be worse than nothing."""
        from app.auth import key_fingerprint

        assert key_fingerprint("django-key") != key_fingerprint("fastapi-key")

    def test_a_missing_key_says_so_rather_than_hashing_the_empty_string(self):
        from app.auth import key_fingerprint

        assert key_fingerprint("") == "unset"

    def test_the_fingerprint_does_not_contain_the_key(self):
        """It gets logged and pasted into issues, so it must not be a step
        towards recovering the secret. An HMAC of a fixed public label under
        the key, never a hash of the key itself."""
        from app.auth import key_fingerprint

        secret = "correct-horse-battery-staple"
        assert secret not in key_fingerprint(secret)

    def test_it_is_short_enough_to_compare_by_eye(self):
        from app.auth import key_fingerprint

        assert len(key_fingerprint("anything")) == 12

    def test_a_wrongly_signed_token_is_reported_as_a_signature_failure(self, caplog):
        """The log line that turns an afternoon into five minutes: a valid,
        unexpired token whose signature does not verify almost always means the
        two services hold different keys, not that anyone forged anything."""
        import logging

        forged = jwt.encode(
            {"sub": USER, "exp": 9999999999}, "some-other-key", algorithm=ALGORITHM
        )
        with caplog.at_level(logging.ERROR):
            with pytest.raises(HTTPException):
                decode_token(forged)

        assert any("jwt_signature_rejected" in r.message for r in caplog.records)
        assert any("signing key does not match" in r.getMessage() for r in caplog.records)
