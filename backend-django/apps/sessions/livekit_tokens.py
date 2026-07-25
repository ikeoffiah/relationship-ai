"""
LiveKit access tokens for joint video sessions.

A LiveKit token is a standard JWT signed (HS256) with the project's API secret,
carrying a ``video`` grant that scopes the holder to one room. We mint it here
with PyJWT — no LiveKit SDK dependency — so the two partners in a joint session
can join the same peer-to-peer video room and no one else can.
"""

import time
import uuid

import jwt
from django.conf import settings

TOKEN_TTL_SECONDS = 60 * 60  # a joint call token is valid for one hour


def livekit_configured() -> bool:
    return bool(
        settings.LIVEKIT_API_KEY
        and settings.LIVEKIT_API_SECRET
        and settings.LIVEKIT_URL
    )


def room_name(session_id) -> str:
    """Deterministic room per joint session — both partners derive the same one."""
    return f"joint-{session_id}"


def mint_token(room: str, identity: str, name: str = "", ttl: int = TOKEN_TTL_SECONDS) -> str:
    """Return a signed LiveKit join token for ``identity`` scoped to ``room``."""
    now = int(time.time())
    claims = {
        "iss": settings.LIVEKIT_API_KEY,
        "sub": identity,
        "jti": str(uuid.uuid4()),
        "nbf": now,
        "exp": now + ttl,
        "name": name or identity,
        "video": {
            "room": room,
            "roomJoin": True,
            "canPublish": True,
            "canSubscribe": True,
            "canPublishData": True,
        },
    }
    return jwt.encode(claims, settings.LIVEKIT_API_SECRET, algorithm="HS256")
