"""Live delivery for the couple thread.

Django owns the data; FastAPI owns the sockets. Rather than duplicate a
connection manager here, we publish onto the same Redis channel the FastAPI
``JointSessionBroker`` already subscribes to, so a message written by an HTTP
request reaches both partners' open sockets — including sockets held by a
different FastAPI replica, since the broker fans out over Redis.

Publishing is strictly best-effort. A message that is persisted but not
delivered live is recoverable — the client picks it up on next fetch. A message
that fails to persist because Redis was unreachable is not. So nothing in here
is allowed to raise into the request path.
"""

import json
import logging

from django.conf import settings

log = logging.getLogger(__name__)

# Must match app/counseling/broker.py, which subscribes to
# f"joint_session:{room}". The couple thread uses the relationship id as its
# room, so a couple has one durable room rather than one per session.
CHANNEL_TEMPLATE = "joint_session:{room}"


def channel_for(relationship_id) -> str:
    return CHANNEL_TEMPLATE.format(room=str(relationship_id))


def publish(relationship_id, event: dict, exclude_user_id=None) -> bool:
    """Fan an event out to the couple's open sockets.

    Returns True if it was handed to Redis, False if it could not be — never
    raises, so a delivery failure cannot roll back a persisted message.
    """
    payload = json.dumps(
        {
            "target_user_id": None,
            "exclude_user_id": str(exclude_user_id) if exclude_user_id else None,
            "event": event,
        }
    )
    try:
        import redis

        client = redis.from_url(settings.REDIS_URL)
        client.publish(channel_for(relationship_id), payload)
        return True
    except Exception as exc:  # pragma: no cover - exercised via the failure test
        log.warning(
            "couple_chat_publish_failed relationship=%s: %s", relationship_id, exc
        )
        return False
