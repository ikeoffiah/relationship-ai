"""
Tests for session-scoped access to the memory endpoint, used by the
session-history detail screen.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.memory.models import Memory

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="u@example.com", password="pw")


def api(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def make_memory(user, session_id, content="a memory", category="trigger"):
    return Memory.objects.create(
        user=user,
        content=content,
        metadata={"source_session_id": session_id, "category": category},
    )


@pytest.mark.django_db
def test_filters_memories_by_session(user):
    make_memory(user, "sess-A", content="from A")
    make_memory(user, "sess-B", content="from B")

    res = api(user).get(f"/api/v1/users/{user.id}/memory", {"session_id": "sess-A"})

    assert res.status_code == 200
    results = res.json()["results"]
    assert len(results) == 1
    assert results[0]["content"] == "from A"


@pytest.mark.django_db
def test_surfaces_category_and_session_id_at_top_level(user):
    make_memory(user, "sess-A", category="conflict_pattern")

    res = api(user).get(f"/api/v1/users/{user.id}/memory", {"session_id": "sess-A"})

    item = res.json()["results"][0]
    assert item["category"] == "conflict_pattern"
    assert item["session_id"] == "sess-A"


@pytest.mark.django_db
def test_without_session_id_returns_all(user):
    make_memory(user, "sess-A")
    make_memory(user, "sess-B")

    res = api(user).get(f"/api/v1/users/{user.id}/memory")

    assert len(res.json()["results"]) == 2


@pytest.mark.django_db
def test_bulk_delete_scoped_to_one_session(user):
    make_memory(user, "sess-A")
    make_memory(user, "sess-A")
    keep = make_memory(user, "sess-B")

    res = api(user).delete(
        f"/api/v1/users/{user.id}/memory?session_id=sess-A"
    )

    assert res.status_code == 200
    assert res.json()["deleted"] == 2
    # Other sessions' memories are untouched.
    assert Memory.objects.filter(id=keep.id).exists()
    assert Memory.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_bulk_delete_requires_session_id(user):
    make_memory(user, "sess-A")

    res = api(user).delete(f"/api/v1/users/{user.id}/memory")

    assert res.status_code == 400
    # A blanket wipe is not exposed through this route.
    assert Memory.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_cannot_read_another_users_memories(user):
    other = User.objects.create_user(email="other@example.com", password="pw")
    make_memory(other, "sess-A")

    res = api(user).get(f"/api/v1/users/{other.id}/memory")

    assert res.status_code == 403
