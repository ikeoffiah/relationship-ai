"""
Tests for the session-history read endpoints (REL-95).

The list and summary are scoped to the authenticated caller: sessions are
private, so one user must never see another's history.
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.sessions.models import LangGraphSession

User = get_user_model()


@pytest.fixture
def owner(db):
    return User.objects.create_user(email="owner@example.com", password="pw")


@pytest.fixture
def other(db):
    return User.objects.create_user(email="other@example.com", password="pw")


def api(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def make_session(user, session_type="individual", turn_count=1, preview="hello"):
    return LangGraphSession.objects.create(
        user=user,
        session_type=session_type,
        turn_count=turn_count,
        summary_preview=preview,
    )


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_list_returns_only_the_callers_sessions(owner, other):
    make_session(owner, preview="mine")
    make_session(other, preview="theirs")

    res = api(owner).get("/api/v1/sessions/")

    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 1
    assert body["results"][0]["summary_preview"] == "mine"


@pytest.mark.django_db
def test_list_is_newest_first(owner):
    old = make_session(owner, preview="old")
    LangGraphSession.objects.filter(id=old.id).update(
        created_at=timezone.now() - timedelta(days=1)
    )
    make_session(owner, preview="new")

    res = api(owner).get("/api/v1/sessions/")

    previews = [s["summary_preview"] for s in res.json()["results"]]
    assert previews == ["new", "old"]


@pytest.mark.django_db
def test_list_paginates_and_signals_more(owner):
    for i in range(3):
        make_session(owner, preview=f"s{i}")

    res = api(owner).get("/api/v1/sessions/", {"page": 1, "page_size": 2})

    body = res.json()
    assert len(body["results"]) == 2
    assert body["count"] == 3
    assert body["next"] == 2  # non-null => client shows "load more"

    page2 = api(owner).get("/api/v1/sessions/", {"page": 2, "page_size": 2}).json()
    assert len(page2["results"]) == 1
    assert page2["next"] is None


@pytest.mark.django_db
def test_list_filters_by_type_and_maps_relay(owner):
    make_session(owner, session_type="individual")
    make_session(owner, session_type="async_relay", preview="relay one")

    res = api(owner).get("/api/v1/sessions/", {"type": "relay"})

    body = res.json()
    assert body["count"] == 1
    # The stored 'async_relay' is surfaced to the client as 'relay'.
    assert body["results"][0]["type"] == "relay"


@pytest.mark.django_db
def test_list_requires_authentication():
    res = APIClient().get("/api/v1/sessions/")
    assert res.status_code in (401, 403)


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_summary_returns_session_detail(owner):
    session = make_session(owner, turn_count=4, preview="a good talk")

    res = api(owner).get(f"/api/v1/sessions/{session.id}/summary")

    assert res.status_code == 200
    body = res.json()
    assert body["id"] == str(session.id)
    assert body["turn_count"] == 4
    assert body["summary"] == "a good talk"
    assert body["frameworks"] == []
    assert body["duration_minutes"] >= 0


@pytest.mark.django_db
def test_cannot_read_another_users_summary(owner, other):
    session = make_session(other)
    res = api(owner).get(f"/api/v1/sessions/{session.id}/summary")
    assert res.status_code == 404


@pytest.mark.django_db
def test_summary_unknown_session_is_404(owner):
    res = api(owner).get(
        "/api/v1/sessions/00000000-0000-0000-0000-000000000000/summary"
    )
    assert res.status_code == 404
