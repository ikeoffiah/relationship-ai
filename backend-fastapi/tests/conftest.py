"""
Shared test fixtures.

Requests are authenticated with real HS256 tokens of the same shape Django
issues, so the tests exercise the actual verification path rather than a
bypass.
"""

import os

# Must be set before app.auth is imported anywhere.
os.environ.setdefault("SECRET_KEY", "test-secret-key")
# Participant membership is verified against the database; unit tests drive the
# socket without one, so opt out explicitly rather than relying on the DB URL.
os.environ.setdefault("WS_SKIP_PARTICIPANT_CHECK", "1")

from datetime import datetime, timedelta, timezone  # noqa: E402

import jwt  # noqa: E402
import pytest  # noqa: E402

from app.auth import ALGORITHM  # noqa: E402

TEST_SECRET = os.environ["SECRET_KEY"]


def make_token(
    user_id: str,
    *,
    expires_in: int = 900,
    secret: str = TEST_SECRET,
    **extra_claims,
) -> str:
    """Mint a token mirroring apps/accounts/auth.py:generate_jwt."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
        "scope": ["user"],
    }
    payload.update(extra_claims)
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def auth_headers(user_id: str, **kwargs) -> dict:
    return {"Authorization": f"Bearer {make_token(user_id, **kwargs)}"}


@pytest.fixture
def token_for():
    return make_token


@pytest.fixture
def headers_for():
    return auth_headers
