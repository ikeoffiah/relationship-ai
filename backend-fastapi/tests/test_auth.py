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
