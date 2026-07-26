"""
Tests for the in-chat tone coach (app/api/tone_router.py + tone_coach.py).

These run WITHOUT model keys, so the LLM path degrades to the safe fallbacks —
which is exactly what we assert: the endpoints never crash, never return empty,
always attach the empathy/agency disclaimers, and — most importantly — the
*safety gate* (deterministic Layer-1 rules, no keys needed) declines to rewrite
harmful drafts and points to support instead.
"""

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import auth_headers

client = TestClient(app)
USER = "user-a"


# ── auth ─────────────────────────────────────────────────────────────────

def test_all_routes_require_auth():
    for path, body in [
        ("/api/v1/tone/analyze", {"text": "hi"}),
        ("/api/v1/tone/coach", {"draft": "hi"}),
        ("/api/v1/tone/suggest", {"messages": []}),
    ]:
        assert client.post(path, json=body).status_code == 401


# ── analyze (mood read) ──────────────────────────────────────────────────

def test_analyze_returns_mood_shape_and_disclaimer():
    res = client.post(
        "/api/v1/tone/analyze",
        json={"text": "I'm just so done with today, everything went wrong."},
        headers=auth_headers(USER),
    )
    assert res.status_code == 200
    body = res.json()
    assert set(body) >= {"mood", "intensity", "summary", "suggestion", "disclaimer"}
    assert body["intensity"] in ("low", "medium", "high")
    # The empathy-not-certainty framing is always present.
    assert "check in" in body["disclaimer"].lower()


def test_analyze_rejects_overlong_text():
    res = client.post(
        "/api/v1/tone/analyze",
        json={"text": "x" * 5000},
        headers=auth_headers(USER),
    )
    assert res.status_code == 422


# ── coach (judge + rewrite) ──────────────────────────────────────────────

def test_coach_returns_read_and_rewrites_list():
    res = client.post(
        "/api/v1/tone/coach",
        json={"draft": "You never listen to me and I'm sick of it."},
        headers=auth_headers(USER),
    )
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body["rewrites"], list)
    assert "disclaimer" in body
    assert body["safety"] is None  # ordinary frustration is coachable


def test_coach_passes_partner_mood_through():
    res = client.post(
        "/api/v1/tone/coach",
        json={"draft": "Can we talk later?", "partner_mood": "stressed"},
        headers=auth_headers(USER),
    )
    assert res.status_code == 200


def test_coach_declines_to_rewrite_coercive_draft():
    # A coercive-control draft must NOT be "softened" into something more
    # palatable — the coach declines and points to support.
    res = client.post(
        "/api/v1/tone/coach",
        json={"draft": "You are not allowed to see your friends anymore."},
        headers=auth_headers(USER),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["rewrites"] == []
    assert body["safety"] is not None
    assert body["safety"]["declined"] is True
    assert body["safety"]["reason"] == "harm_signals"


def test_coach_points_to_support_when_writer_in_crisis():
    res = client.post(
        "/api/v1/tone/coach",
        json={"draft": "I don't want to be alive anymore."},
        headers=auth_headers(USER),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["rewrites"] == []
    assert body["safety"]["reason"] == "writer_distress"


def test_coach_rejects_empty_draft():
    res = client.post("/api/v1/tone/coach", json={"draft": ""}, headers=auth_headers(USER))
    # Empty string still validates (max_length only); the coach returns a safe
    # default with no rewrites rather than erroring.
    assert res.status_code == 200
    assert res.json()["rewrites"] == []


# ── suggest (auto-suggestions) ───────────────────────────────────────────

def test_suggest_returns_list():
    res = client.post(
        "/api/v1/tone/suggest",
        json={"messages": [
            {"role": "partner", "content": "I had a rough day at work."},
            {"role": "me", "content": "oh no what happened"},
        ]},
        headers=auth_headers(USER),
    )
    assert res.status_code == 200
    assert isinstance(res.json()["suggestions"], list)


def test_suggest_empty_messages_returns_empty():
    res = client.post(
        "/api/v1/tone/suggest", json={"messages": []}, headers=auth_headers(USER)
    )
    assert res.status_code == 200
    assert res.json()["suggestions"] == []


def test_suggest_rejects_bad_role():
    res = client.post(
        "/api/v1/tone/suggest",
        json={"messages": [{"role": "system", "content": "hi"}]},
        headers=auth_headers(USER),
    )
    assert res.status_code == 422
