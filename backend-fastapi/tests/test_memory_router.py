"""Unit tests for app/api/memory_router.py CRUD endpoints."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.memory_router import _memory_store, MemoryOut
from app.dependencies import User
from app.main import app

client = TestClient(app)
BASE = "/api/v1/memory"
CURRENT_USER_ID = User.id


@pytest.fixture(autouse=True)
def clean_store():
    _memory_store.clear()
    yield
    _memory_store.clear()


def create_memory(content="I feel unheard during money talks.", metadata=None):
    response = client.post(
        f"{BASE}/", json={"content": content, "metadata": metadata or {}}
    )
    assert response.status_code == 201, response.text
    return response.json()


def foreign_memory():
    """Insert a memory owned by a different user directly into the store."""
    mem_id = uuid4()
    _memory_store[mem_id] = MemoryOut(
        id=mem_id,
        user_id=uuid4(),
        content="someone else's memory",
        metadata={},
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
    )
    return mem_id


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

def test_create_memory_returns_201_and_persists():
    data = create_memory("We keep circling the same argument.")

    assert data["content"] == "We keep circling the same argument."
    assert UUID(data["user_id"]) == CURRENT_USER_ID
    assert data["content_preview"] == "We keep circling the same argument."
    assert data["created_at"] == data["updated_at"]
    assert UUID(data["id"]) in _memory_store


def test_create_memory_truncates_preview_to_50_chars():
    data = create_memory("z" * 200)

    assert data["content_preview"] == "z" * 50
    assert len(data["content"]) == 200


def test_create_memory_lifts_memory_type_from_metadata():
    data = create_memory("holidays are a flashpoint", {"memory_type": "conflict_pattern"})

    assert data["memory_type"] == "conflict_pattern"
    assert data["metadata"] == {"memory_type": "conflict_pattern"}


def test_create_memory_without_memory_type_leaves_it_null():
    assert create_memory("plain memory")["memory_type"] is None


def test_create_memory_requires_content():
    assert client.post(f"{BASE}/", json={"metadata": {}}).status_code == 422


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

def test_list_memories_returns_only_current_users_memories():
    created = create_memory("mine")
    foreign_memory()

    response = client.get(f"{BASE}/")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == created["id"]


def test_list_memories_empty_by_default():
    assert client.get(f"{BASE}/").json() == []


def test_list_memories_respects_limit_and_offset():
    for i in range(5):
        create_memory(f"memory {i}")

    page = client.get(f"{BASE}/", params={"limit": 2, "offset": 1}).json()

    assert len(page) == 2
    assert [m["content"] for m in page] == ["memory 1", "memory 2"]


def test_list_memories_filters_by_memory_type():
    create_memory("conflict one", {"memory_type": "conflict_pattern"})
    create_memory("a trigger", {"memory_type": "trigger"})

    filtered = client.get(f"{BASE}/", params={"type": "conflict_pattern"}).json()

    assert [m["content"] for m in filtered] == ["conflict one"]


def test_list_memories_filters_by_metadata_type_key():
    create_memory("tagged via metadata", {"type": "repair_event"})
    create_memory("untagged")

    filtered = client.get(f"{BASE}/", params={"type": "repair_event"}).json()

    assert [m["content"] for m in filtered] == ["tagged via metadata"]


def test_list_memories_type_filter_with_no_matches():
    create_memory("conflict one", {"memory_type": "conflict_pattern"})

    assert client.get(f"{BASE}/", params={"type": "trigger"}).json() == []


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------

def test_get_memory_by_id():
    created = create_memory("retrieve me")

    response = client.get(f"{BASE}/{created['id']}")

    assert response.status_code == 200
    assert response.json()["content"] == "retrieve me"


def test_get_missing_memory_returns_404():
    response = client.get(f"{BASE}/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Memory not found"


def test_get_another_users_memory_returns_404():
    assert client.get(f"{BASE}/{foreign_memory()}").status_code == 404


def test_get_memory_with_non_uuid_id_returns_422():
    assert client.get(f"{BASE}/not-a-uuid").status_code == 422


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

def test_update_memory_content_recomputes_preview():
    created = create_memory("original")

    response = client.put(f"{BASE}/{created['id']}", json={"content": "y" * 80})

    assert response.status_code == 200
    body = response.json()
    assert body["content"] == "y" * 80
    assert body["content_preview"] == "y" * 50
    assert body["id"] == created["id"]


def test_update_memory_metadata_only_leaves_content_alone():
    created = create_memory("keep me")

    body = client.put(
        f"{BASE}/{created['id']}", json={"metadata": {"reviewed": True}}
    ).json()

    assert body["content"] == "keep me"
    assert body["metadata"] == {"reviewed": True}
    assert body["content_preview"] == "keep me"


def test_update_memory_persists_to_store():
    created = create_memory("before")

    client.put(f"{BASE}/{created['id']}", json={"content": "after"})

    assert _memory_store[UUID(created["id"])].content == "after"


def test_update_missing_memory_returns_404():
    response = client.put(f"{BASE}/{uuid4()}", json={"content": "nope"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Memory not found"


def test_update_another_users_memory_returns_404():
    mem_id = foreign_memory()

    assert client.put(f"{BASE}/{mem_id}", json={"content": "hijack"}).status_code == 404
    assert _memory_store[mem_id].content == "someone else's memory"


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

def test_delete_memory_returns_204_and_removes_it():
    created = create_memory("delete me")

    response = client.delete(f"{BASE}/{created['id']}")

    assert response.status_code == 204
    assert UUID(created["id"]) not in _memory_store
    assert client.get(f"{BASE}/{created['id']}").status_code == 404


def test_delete_missing_memory_returns_404():
    assert client.delete(f"{BASE}/{uuid4()}").status_code == 404


def test_delete_another_users_memory_returns_404():
    mem_id = foreign_memory()

    assert client.delete(f"{BASE}/{mem_id}").status_code == 404
    assert mem_id in _memory_store


# ---------------------------------------------------------------------------
# bulk-delete
# ---------------------------------------------------------------------------

def test_bulk_delete_removes_owned_memories():
    a = create_memory("a")
    b = create_memory("b")
    keep = create_memory("keep")

    response = client.post(
        f"{BASE}/bulk-delete/", json={"memory_ids": [a["id"], b["id"]]}
    )

    assert response.status_code == 202
    body = response.json()
    assert set(body["deleted"]) == {a["id"], b["id"]}
    assert body["requested"] == 2
    assert list(_memory_store) == [UUID(keep["id"])]


def test_bulk_delete_skips_unknown_and_foreign_ids():
    mine = create_memory("mine")
    theirs = foreign_memory()
    unknown = uuid4()

    body = client.post(
        f"{BASE}/bulk-delete/",
        json={"memory_ids": [mine["id"], str(theirs), str(unknown)]},
    ).json()

    assert body["deleted"] == [mine["id"]]
    assert body["requested"] == 3
    assert theirs in _memory_store


def test_bulk_delete_with_empty_list():
    create_memory("untouched")

    body = client.post(f"{BASE}/bulk-delete/", json={"memory_ids": []}).json()

    assert body == {"deleted": [], "requested": 0}
    assert len(_memory_store) == 1


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------

def test_count_memories_counts_only_current_user():
    create_memory("one")
    create_memory("two")
    foreign_memory()

    response = client.get(f"{BASE}/count/")

    assert response.status_code == 200
    assert response.json() == 2


def test_count_is_zero_when_empty():
    assert client.get(f"{BASE}/count/").json() == 0


def test_count_reflects_deletions():
    a = create_memory("one")
    create_memory("two")

    client.delete(f"{BASE}/{a['id']}")

    assert client.get(f"{BASE}/count/").json() == 1
