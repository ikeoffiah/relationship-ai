"""Unit tests for app/api/relationships.py (shared relationship context)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.relationships import (
    decrypt_context,
    encrypt_context,
    get_db_pool,
    router,
)
from app.main import app

client = TestClient(app)

REL_ID = "rel-123"
PARTNER_A = "user-a"
PARTNER_B = "user-b"
BASE = f"/api/v1/relationships/{REL_ID}"
HEADERS = {"X-User-ID": PARTNER_A}


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


def make_pool(fetchrow_results, fetch_results):
    conn = FakeConn(fetchrow_results, fetch_results)
    pool = MagicMock()
    acquire_ctx = MagicMock()
    acquire_ctx.__aenter__ = AsyncMock(return_value=conn)
    acquire_ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock(return_value=acquire_ctx)
    return pool, conn


def active_relationship(partner_b=PARTNER_B):
    return {"partner_a_id": PARTNER_A, "partner_b_id": partner_b}


def consents(a="read_write", b="read_write"):
    rows = []
    if a is not None:
        rows.append({"user_id": PARTNER_A, "shared_relationship_context": a})
    if b is not None:
        rows.append({"user_id": PARTNER_B, "shared_relationship_context": b})
    return rows


@pytest.fixture
def use_pool():
    """Install a scripted pool as the get_db_pool dependency override."""
    def _install(fetchrow_results, fetch_results):
        pool, conn = make_pool(fetchrow_results, fetch_results)
        app.dependency_overrides[get_db_pool] = lambda: pool
        return conn

    yield _install
    app.dependency_overrides.pop(get_db_pool, None)


@pytest.fixture
def mock_vector_store():
    """Patch VectorMemoryStore so no embedding/DB calls are made."""
    instance = MagicMock()
    instance.upsert = AsyncMock(return_value="mem-id")
    with patch(
        "app.memory.vector_store.VectorMemoryStore", return_value=instance
    ) as cls:
        yield cls, instance


CONFLICT_BODY = {
    "conflict_id": "c1",
    "label": "Holiday planning",
    "description": "Disagreement over whose family to visit.",
    "acknowledged_by_both": True,
}
GOAL_BODY = {"goal_id": "g1", "description": "Weekly check-in every Sunday."}
REPAIR_BODY = {
    "event_id": "e1",
    "description": "Apologised and named the impact.",
    "session_id": "s1",
}
STRUCTURAL_BODY = {
    "relationship_duration_months": 42,
    "cohabiting": True,
    "children": 1,
    "cultural_backgrounds": ["Irish", "Nigerian"],
    "religious_values": ["Catholic"],
}


# ---------------------------------------------------------------------------
# Helpers: encryption stubs and router wiring
# ---------------------------------------------------------------------------

def test_encrypt_context_round_trips():
    payload = {"a": [1, 2], "b": "text"}

    assert decrypt_context(encrypt_context(payload, REL_ID), REL_ID) == payload


def test_decrypt_context_returns_empty_dict_on_garbage():
    assert decrypt_context("not json at all", REL_ID) == {}


def test_router_is_mounted_under_expected_prefix():
    assert router.prefix == "/api/v1/relationships"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def test_missing_user_header_returns_401(use_pool):
    use_pool([], [])

    response = client.get(f"{BASE}/context")

    assert response.status_code == 401
    assert response.json()["detail"] == "X-User-ID header required"


# ---------------------------------------------------------------------------
# Consent gate
# ---------------------------------------------------------------------------

def test_unknown_relationship_returns_404(use_pool):
    use_pool([None], [])

    response = client.get(f"{BASE}/context", headers=HEADERS)

    assert response.status_code == 404
    assert response.json()["detail"] == "Active relationship not found"


def test_relationship_without_second_partner_returns_403(use_pool):
    use_pool([active_relationship(partner_b=None)], [])

    response = client.get(f"{BASE}/context", headers=HEADERS)

    assert response.status_code == 403
    assert response.json()["detail"] == "Relationship not fully formed"


def test_partner_not_participating_returns_403(use_pool):
    use_pool([active_relationship()], [consents(a="read_write", b="not_participating")])

    response = client.get(f"{BASE}/context", headers=HEADERS)

    assert response.status_code == 403
    assert response.json()["detail"] == "Shared context access denied by consent gate"


def test_missing_consent_row_defaults_to_not_participating(use_pool):
    # Partner B has no consent row at all.
    use_pool([active_relationship()], [consents(a="read_write", b=None)])

    response = client.get(f"{BASE}/context", headers=HEADERS)

    assert response.status_code == 403
    assert response.json()["detail"] == "Shared context access denied by consent gate"


def test_read_only_consent_permits_reads(use_pool):
    use_pool([active_relationship(), None], [consents(a="read_only", b="read_only")])

    response = client.get(f"{BASE}/context", headers=HEADERS)

    assert response.status_code == 200


def test_read_only_consent_blocks_writes(use_pool, mock_vector_store):
    _, vector_store = mock_vector_store
    use_pool([active_relationship()], [consents(a="read_write", b="read_only")])

    response = client.put(f"{BASE}/context/conflicts", json=CONFLICT_BODY, headers=HEADERS)

    assert response.status_code == 403
    assert response.json()["detail"] == "Bilateral read_write consent required for writes"
    vector_store.upsert.assert_not_awaited()


@pytest.mark.parametrize(
    "path,body",
    [
        ("conflicts", CONFLICT_BODY),
        ("goals", GOAL_BODY),
        ("repairs", REPAIR_BODY),
        ("structural", STRUCTURAL_BODY),
    ],
)
def test_all_write_routes_enforce_bilateral_write_consent(use_pool, path, body):
    use_pool([active_relationship()], [consents(a="read_only", b="read_write")])

    response = client.put(f"{BASE}/context/{path}", json=body, headers=HEADERS)

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /context
# ---------------------------------------------------------------------------

def test_get_context_returns_empty_shape_when_no_row(use_pool):
    use_pool([active_relationship(), None], [consents()])

    body = client.get(f"{BASE}/context", headers=HEADERS).json()

    assert body == {
        "named_recurring_conflicts": [],
        "agreed_goals_and_values": [],
        "repair_history": [],
        "structural_facts": {},
    }


def test_get_context_decrypts_stored_columns(use_pool):
    stored = {
        "named_recurring_conflicts": json.dumps([{"conflict_id": "c1", "label": "Money"}]),
        "agreed_goals_and_values": json.dumps([{"goal_id": "g1"}]),
        "repair_history": json.dumps([{"event_id": "e1"}]),
        "structural_facts": json.dumps({"children": 2}),
    }
    use_pool([active_relationship(), stored], [consents()])

    body = client.get(f"{BASE}/context", headers=HEADERS).json()

    assert body["named_recurring_conflicts"] == [{"conflict_id": "c1", "label": "Money"}]
    assert body["agreed_goals_and_values"] == [{"goal_id": "g1"}]
    assert body["repair_history"] == [{"event_id": "e1"}]
    assert body["structural_facts"] == {"children": 2}


# ---------------------------------------------------------------------------
# PUT /context/conflicts
# ---------------------------------------------------------------------------

def test_create_conflict_inserts_row_and_indexes_vector(use_pool, mock_vector_store):
    _, vector_store = mock_vector_store
    conn = use_pool([active_relationship(), None], [consents()])

    response = client.put(f"{BASE}/context/conflicts", json=CONFLICT_BODY, headers=HEADERS)

    assert response.status_code == 200
    assert response.json() == {"status": "success"}

    query, args = conn.executed[0]
    assert "INSERT INTO shared_relationship_context" in query
    stored = decrypt_context(args[1], REL_ID)
    assert len(stored) == 1
    assert stored[0]["conflict_id"] == "c1"
    assert stored[0]["label"] == "Holiday planning"
    assert "created_at" in stored[0]

    upsert_kwargs = vector_store.upsert.await_args.kwargs
    assert upsert_kwargs["memory_id"] == "conflict_c1"
    assert upsert_kwargs["user_id"] == PARTNER_A
    assert "Holiday planning" in upsert_kwargs["text"]
    assert upsert_kwargs["zone"] == f"shared_{REL_ID}"
    assert upsert_kwargs["metadata"]["type"] == "conflict"


def test_update_existing_conflict_mutates_in_place(use_pool, mock_vector_store):
    existing = [{"conflict_id": "c1", "label": "Old label", "created_at": "2026-01-01"}]
    row = {"named_recurring_conflicts": json.dumps(existing)}
    conn = use_pool([active_relationship(), row], [consents()])

    response = client.put(f"{BASE}/context/conflicts", json=CONFLICT_BODY, headers=HEADERS)

    assert response.status_code == 200
    query, args = conn.executed[0]
    assert "UPDATE shared_relationship_context" in query
    stored = decrypt_context(args[0], REL_ID)
    assert len(stored) == 1, "existing conflict should be updated, not duplicated"
    assert stored[0]["label"] == "Holiday planning"
    assert stored[0]["created_at"] == "2026-01-01", "original timestamp preserved"


def test_new_conflict_appends_to_existing_list(use_pool, mock_vector_store):
    row = {"named_recurring_conflicts": json.dumps([{"conflict_id": "other"}])}
    conn = use_pool([active_relationship(), row], [consents()])

    client.put(f"{BASE}/context/conflicts", json=CONFLICT_BODY, headers=HEADERS)

    stored = decrypt_context(conn.executed[0][1][0], REL_ID)
    assert [c["conflict_id"] for c in stored] == ["other", "c1"]


def test_conflict_payload_validation(use_pool):
    use_pool([active_relationship()], [consents()])

    response = client.put(
        f"{BASE}/context/conflicts", json={"conflict_id": "c1"}, headers=HEADERS
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# PUT /context/goals
# ---------------------------------------------------------------------------

def test_create_goal_records_author_and_indexes_vector(use_pool, mock_vector_store):
    _, vector_store = mock_vector_store
    conn = use_pool([active_relationship(), None], [consents()])

    response = client.put(f"{BASE}/context/goals", json=GOAL_BODY, headers=HEADERS)

    assert response.status_code == 200
    query, args = conn.executed[0]
    assert "INSERT INTO shared_relationship_context" in query
    stored = decrypt_context(args[1], REL_ID)
    assert stored[0]["goal_id"] == "g1"
    assert stored[0]["added_by"] == PARTNER_A
    assert "created_at" in stored[0]

    assert vector_store.upsert.await_args.kwargs["memory_id"] == "goal_g1"
    assert vector_store.upsert.await_args.kwargs["metadata"]["type"] == "goal"


def test_update_existing_goal_does_not_duplicate(use_pool, mock_vector_store):
    row = {
        "agreed_goals_and_values": json.dumps(
            [{"goal_id": "g1", "description": "Old", "added_by": PARTNER_B}]
        )
    }
    conn = use_pool([active_relationship(), row], [consents()])

    client.put(f"{BASE}/context/goals", json=GOAL_BODY, headers=HEADERS)

    query, args = conn.executed[0]
    assert "UPDATE shared_relationship_context" in query
    stored = decrypt_context(args[0], REL_ID)
    assert len(stored) == 1
    assert stored[0]["description"] == "Weekly check-in every Sunday."
    assert stored[0]["added_by"] == PARTNER_B, "original author preserved on update"


# ---------------------------------------------------------------------------
# PUT /context/repairs
# ---------------------------------------------------------------------------

def test_create_repair_appends_with_timestamp(use_pool, mock_vector_store):
    _, vector_store = mock_vector_store
    conn = use_pool([active_relationship(), None], [consents()])

    response = client.put(f"{BASE}/context/repairs", json=REPAIR_BODY, headers=HEADERS)

    assert response.status_code == 200
    query, args = conn.executed[0]
    assert "INSERT INTO shared_relationship_context" in query
    stored = decrypt_context(args[1], REL_ID)
    assert stored[0]["event_id"] == "e1"
    assert stored[0]["added_by"] == PARTNER_A
    assert "timestamp" in stored[0]

    kwargs = vector_store.upsert.await_args.kwargs
    assert kwargs["memory_id"] == "repair_e1"
    assert kwargs["metadata"]["session_id"] == "s1"


def test_repairs_are_append_only(use_pool, mock_vector_store):
    row = {"repair_history": json.dumps([{"event_id": "e1", "description": "earlier"}])}
    conn = use_pool([active_relationship(), row], [consents()])

    client.put(f"{BASE}/context/repairs", json=REPAIR_BODY, headers=HEADERS)

    stored = decrypt_context(conn.executed[0][1][0], REL_ID)
    assert len(stored) == 2, "repair history is an append-only log"
    assert [r["description"] for r in stored] == [
        "earlier",
        "Apologised and named the impact.",
    ]


# ---------------------------------------------------------------------------
# PUT /context/structural
# ---------------------------------------------------------------------------

def test_create_structural_facts_inserts_row(use_pool):
    conn = use_pool([active_relationship(), None], [consents()])

    response = client.put(
        f"{BASE}/context/structural", json=STRUCTURAL_BODY, headers=HEADERS
    )

    assert response.status_code == 200
    query, args = conn.executed[0]
    assert "INSERT INTO shared_relationship_context" in query
    assert decrypt_context(args[1], REL_ID) == STRUCTURAL_BODY


def test_structural_facts_replace_previous_values(use_pool):
    row = {"structural_facts": json.dumps({"children": 0, "cohabiting": False})}
    conn = use_pool([active_relationship(), row], [consents()])

    client.put(f"{BASE}/context/structural", json=STRUCTURAL_BODY, headers=HEADERS)

    query, args = conn.executed[0]
    assert "UPDATE shared_relationship_context" in query
    assert decrypt_context(args[0], REL_ID) == STRUCTURAL_BODY


def test_structural_payload_validation(use_pool):
    use_pool([active_relationship()], [consents()])

    bad = dict(STRUCTURAL_BODY, children="lots")
    response = client.put(f"{BASE}/context/structural", json=bad, headers=HEADERS)

    assert response.status_code == 422
