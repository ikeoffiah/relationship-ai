"""Tests for app/api/feedback_router.py."""

from fastapi.testclient import TestClient

from app.api import feedback_router as feedback
from app.main import app
from tests.conftest import auth_headers

client = TestClient(app)

USER = "user-a"
URL = "/api/v1/sessions/sess-1/feedback"


def setup_function():
    feedback._feedback_store.clear()


def test_requires_authentication():
    # Previously any caller could write feedback for any session.
    res = client.post(URL, json={"rating": 5})
    assert res.status_code == 401


def test_authenticated_user_can_submit_and_is_recorded():
    res = client.post(
        URL,
        json={"rating": 4, "feedback_text": "helpful"},
        headers=auth_headers(USER),
    )

    assert res.status_code == 200
    body = res.json()
    assert body["rating"] == 4
    # The submitter is attributed to the authenticated caller, not the payload.
    assert feedback._feedback_store["sess-1"]["user_id"] == USER


def test_rating_is_bounded():
    res = client.post(URL, json={"rating": 9}, headers=auth_headers(USER))
    assert res.status_code == 422
