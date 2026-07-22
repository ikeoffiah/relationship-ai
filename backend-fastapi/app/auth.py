"""
Request authentication for the FastAPI service.

Tokens are issued by the Django service (apps/accounts/auth.py:generate_jwt),
signed HS256 with its SECRET_KEY. This service verifies the same tokens, so
**both services must be configured with the identical SECRET_KEY** or every
request here will 401.

This replaces two earlier placeholders:
  * a `get_current_user` that returned a hardcoded UUID for every caller, so
    all users shared one memory namespace;
  * a `get_current_user_id` that trusted an `X-User-ID` request header, which
    let any caller assert any identity simply by setting it.
Neither is accepted any more — identity comes only from a signed token.
"""

import os
import secrets
from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import HTTPException, Request, status

ALGORITHM = "HS256"


@dataclass
class User:
    id: UUID


def _secret() -> str:
    secret = os.environ.get("SECRET_KEY")
    if not secret:
        # Fail closed: without a secret we cannot verify anything, and
        # defaulting to a placeholder would accept forged tokens.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SECRET_KEY is not configured; cannot verify credentials",
        )
    return secret


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def decode_token(token: str) -> dict:
    """Verify signature and expiry, returning the claims."""
    try:
        return jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Token has expired")
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid token")


def _bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise _unauthorized("Bearer token required")
    return token.strip()


async def get_current_user_id(request: Request) -> str:
    """The authenticated caller's user id, taken from the token's `sub`."""
    claims = decode_token(_bearer_token(request))
    subject = claims.get("sub")
    if not subject:
        raise _unauthorized("Token is missing a subject")
    return str(subject)


async def get_current_user(request: Request) -> User:
    """As above, as a User object for callers that expect `.id`."""
    subject = await get_current_user_id(request)
    try:
        return User(id=UUID(subject))
    except (ValueError, AttributeError, TypeError):
        raise _unauthorized("Token subject is not a valid user id")


async def require_internal_token(request: Request) -> None:
    """
    Guard for service-to-service endpoints (e.g. Celery → FastAPI) that are not
    called by an end user and so carry no JWT.

    The caller must present X-Internal-Token matching INTERNAL_API_TOKEN. Fails
    closed: if the secret is unset the endpoint is unreachable rather than open,
    so a misconfigured deployment can't be exploited.
    """
    expected = os.environ.get("INTERNAL_API_TOKEN")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal endpoint is not configured",
        )
    provided = request.headers.get("X-Internal-Token", "")
    # Constant-time compare to avoid leaking the secret via timing.
    if not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal token",
        )
