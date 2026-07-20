"""Unit tests for app/api/relay_router.py (persisted partner relay)."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from app.api.relationships import get_db_pool
from tests.conftest import auth_headers
from app.main import app

client = TestClient(app)

SENDER = "user-a"
RECIPIENT = "user-b"
REL_ID = "rel-1"
SESSION = "session123"
HEADERS = auth_headers(SENDER)
RECIPIENT_HEADERS = auth_headers(RECIPIENT)


class FakeConn:
    """asyncpg connection double driven by scripted fetchrow/fetch results."""

    def __init__(self, fetchrow_results, fetch_results):
        self._fetchrow_results = list(fetchrow_results)
        self._fetch_results = list(fetch_results)
        self.executed = []

    async def fetchrow(self, query, *args):
        return self._fetchrow_results.pop(0)

    async def fetch(self, query, *args):
        return self._fetch_results.pop(0)

    async def execute(self, query, *args):
        self.executed.append((query, args))
        return "OK"


@pytest.fixture
def use_pool():
    def _install(fetchrow_results=(), fetch_results=()):
        conn = FakeConn(fetchrow_results, fetch_results)
        pool = MagicMock()
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=conn)
        ctx.__aexit__ = AsyncMock(return_value=False)
        pool.acquire = MagicMock(return_value=ctx)
        app.dependency_overrides[get_db_pool] = lambda: pool
        return conn

    yield _install
    app.dependency_overrides.pop(get_db_pool, None)


def active_relationship():
    return {"id": REL_ID, "partner_a_id": SENDER, "partner_b_id": RECIPIENT}


def relay_row(**overrides):
    now = datetime.now(timezone.utc)
    row = {
        "relay_id": "relay-1",
        "relationship_id": REL_ID,
        "from_user_id": SENDER,
        "to_user_id": RECIPIENT,
        "original_content": "I feel unhappy with our communication.",
        "translated_content": "Observation: ...",
        "translation_quality_score": 0.85,
        "status": "ready",
        "recipient_chose_version": None,
        "created_at": now,
        "delivered_at": None,
        "expires_at": now + timedelta(days=7),
    }
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# send_relay
# ---------------------------------------------------------------------------

def test_send_relay_persists_row_and_resolves_partner(use_pool):
    conn = use_pool(fetchrow_results=[active_relationship()])

    res = client.post(
        f"/api/v1/sessions/{SESSION}/relay",
        json={"content": "I feel unhappy with our communication.", "consent_to_relay": True},
        headers=HEADERS,
    )

    assert res.status_code == 200
    assert res.json()["status"] == "ready"

    # One INSERT, routed to the resolved partner rather than a hardcoded id.
    assert len(conn.executed) == 1
    query, args = conn.executed[0]
    assert "INSERT INTO relay_messages" in query
    assert args[1] == REL_ID          # relationship_id
    assert args[2] == SENDER          # from_user_id
    assert args[3] == RECIPIENT       # to_user_id
    assert args[7] == "ready"         # status


def test_low_quality_message_is_held_for_review(use_pool):
    conn = use_pool(fetchrow_results=[active_relationship()])

    res = client.post(
        f"/api/v1/sessions/{SESSION}/relay",
        json={"content": "low_quality message", "consent_to_relay": True},
        headers=HEADERS,
    )

    assert res.status_code == 200
    # Client sees "processing" while the stored row is held in quality_review.
    assert res.json()["status"] == "processing"
    assert conn.executed[0][1][7] == "quality_review"


def test_send_relay_without_consent_is_rejected(use_pool):
    conn = use_pool(fetchrow_results=[active_relationship()])

    res = client.post(
        f"/api/v1/sessions/{SESSION}/relay",
        json={"content": "I feel unhappy.", "consent_to_relay": False},
        headers=HEADERS,
    )

    assert res.status_code == 400
    assert conn.executed == []  # nothing written without consent


def test_send_relay_requires_authentication(use_pool):
    use_pool(fetchrow_results=[active_relationship()])
    res = client.post(
        f"/api/v1/sessions/{SESSION}/relay",
        json={"content": "hello", "consent_to_relay": True},
    )
    assert res.status_code == 401


def test_send_relay_without_active_relationship_is_404(use_pool):
    conn = use_pool(fetchrow_results=[None])

    res = client.post(
        f"/api/v1/sessions/{SESSION}/relay",
        json={"content": "hello", "consent_to_relay": True},
        headers=HEADERS,
    )

    assert res.status_code == 404
    assert conn.executed == []


def test_send_relay_with_unpaired_relationship_is_400(use_pool):
    use_pool(fetchrow_results=[{"id": REL_ID, "partner_a_id": SENDER, "partner_b_id": None}])

    res = client.post(
        f"/api/v1/sessions/{SESSION}/relay",
        json={"content": "hello", "consent_to_relay": True},
        headers=HEADERS,
    )

    assert res.status_code == 400


# ---------------------------------------------------------------------------
# pending inbox
# ---------------------------------------------------------------------------

def test_pending_returns_recipient_ready_messages(use_pool):
    use_pool(fetch_results=[[relay_row()]])

    res = client.get(f"/api/v1/users/{RECIPIENT}/relay/pending", headers=RECIPIENT_HEADERS)

    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["relay_id"] == "relay-1"
    assert body[0]["to_user_id"] == RECIPIENT


def test_pending_inbox_is_private_to_its_owner(use_pool):
    use_pool(fetch_results=[[]])
    res = client.get(f"/api/v1/users/{RECIPIENT}/relay/pending", headers=HEADERS)
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# deliver
# ---------------------------------------------------------------------------

def test_deliver_marks_delivered_and_records_choice(use_pool):
    delivered = relay_row(
        status="delivered",
        delivered_at=datetime.now(timezone.utc),
        recipient_chose_version="ai_translated",
    )
    use_pool(fetchrow_results=[relay_row(), delivered])

    res = client.post(
        "/api/v1/relay/relay-1/deliver",
        json={"recipient_chose_version": "ai_translated"},
        headers=RECIPIENT_HEADERS,
    )

    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "delivered"
    assert body["recipient_chose_version"] == "ai_translated"


def test_only_recipient_may_take_delivery(use_pool):
    use_pool(fetchrow_results=[relay_row()])
    res = client.post(
        "/api/v1/relay/relay-1/deliver",
        json={"recipient_chose_version": "original"},
        headers=HEADERS,  # sender, not recipient
    )
    assert res.status_code == 403


def test_deliver_unknown_relay_is_404(use_pool):
    use_pool(fetchrow_results=[None])
    res = client.post(
        "/api/v1/relay/nope/deliver",
        json={"recipient_chose_version": "original"},
        headers=RECIPIENT_HEADERS,
    )
    assert res.status_code == 404


def test_expired_relay_cannot_be_delivered_and_is_marked_expired(use_pool):
    expired = relay_row(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
    conn = use_pool(fetchrow_results=[expired])

    res = client.post(
        "/api/v1/relay/relay-1/deliver",
        json={"recipient_chose_version": "original"},
        headers=RECIPIENT_HEADERS,
    )

    assert res.status_code == 400
    assert "SET status = 'expired'" in conn.executed[0][0]


def test_quality_review_relay_is_not_deliverable(use_pool):
    use_pool(fetchrow_results=[relay_row(status="quality_review")])
    res = client.post(
        "/api/v1/relay/relay-1/deliver",
        json={"recipient_chose_version": "original"},
        headers=RECIPIENT_HEADERS,
    )
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# withdraw
# ---------------------------------------------------------------------------

def test_sender_can_withdraw_before_delivery(use_pool):
    conn = use_pool(fetchrow_results=[{"from_user_id": SENDER, "status": "ready"}])

    res = client.delete("/api/v1/relay/relay-1", headers=HEADERS)

    assert res.status_code == 200
    assert res.json()["status"] == "withdrawn"
    assert "SET status = 'withdrawn'" in conn.executed[0][0]


def test_withdraw_after_delivery_fails(use_pool):
    conn = use_pool(fetchrow_results=[{"from_user_id": SENDER, "status": "delivered"}])
    res = client.delete("/api/v1/relay/relay-1", headers=HEADERS)
    assert res.status_code == 400
    assert conn.executed == []


def test_only_sender_may_withdraw(use_pool):
    use_pool(fetchrow_results=[{"from_user_id": SENDER, "status": "ready"}])
    res = client.delete("/api/v1/relay/relay-1", headers=RECIPIENT_HEADERS)
    assert res.status_code == 403


def test_withdraw_unknown_relay_is_404(use_pool):
    use_pool(fetchrow_results=[None])
    res = client.delete("/api/v1/relay/nope", headers=HEADERS)
    assert res.status_code == 404
