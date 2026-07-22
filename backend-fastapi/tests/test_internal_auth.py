"""
Tests for the internal service-token guard on POST
/api/v1/memory/internal/extract-memories.

The endpoint is called by Celery, not an end user, so it carries no JWT. It
previously had no auth at all — any caller could inject memories into any
user's namespace via the body's user_id.
"""

import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

URL = "/api/v1/memory/internal/extract-memories"
BODY = {"session_id": "s1", "user_id": "victim", "messages": []}


def test_rejected_without_the_internal_token():
    with patch.dict(os.environ, {"INTERNAL_API_TOKEN": "s3cret"}):
        res = client.post(URL, json=BODY)
    assert res.status_code == 403


def test_rejected_with_a_wrong_token():
    with patch.dict(os.environ, {"INTERNAL_API_TOKEN": "s3cret"}):
        res = client.post(URL, json=BODY, headers={"X-Internal-Token": "nope"})
    assert res.status_code == 403


def test_fails_closed_when_secret_is_unconfigured():
    # No configured secret must not mean "open"; it means unavailable.
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("INTERNAL_API_TOKEN", None)
        res = client.post(URL, json=BODY, headers={"X-Internal-Token": "anything"})
    assert res.status_code == 503


def test_accepts_the_correct_token_and_reaches_the_handler():
    # With the right token the guard passes; the handler then runs (and, with
    # no real DB/Anthropic key, returns its own error — not a 403).
    with patch.dict(os.environ, {"INTERNAL_API_TOKEN": "s3cret"}):
        res = client.post(URL, json=BODY, headers={"X-Internal-Token": "s3cret"})
    assert res.status_code != 403
    assert res.status_code != 503
