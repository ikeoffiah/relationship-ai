"""Tests for parsing the FIREBASE_SERVICE_ACCOUNT_JSON env value."""

import base64
import json

import pytest

from apps.notifications.push_service import _parse_service_account

SAMPLE = {"type": "service_account", "project_id": "bliss-d7721", "private_key": "x"}


def test_parses_raw_json():
    assert _parse_service_account(json.dumps(SAMPLE)) == SAMPLE


def test_parses_base64_json():
    encoded = base64.b64encode(json.dumps(SAMPLE).encode()).decode()
    assert _parse_service_account(encoded) == SAMPLE


def test_raises_on_garbage():
    with pytest.raises(Exception):
        _parse_service_account("not json and not base64!!!")


def test_send_failure_is_handled_not_raised(monkeypatch):
    """A failing FCM send must return False and log cleanly — never let the
    error handler itself raise (regression: log.error was passed kwargs that
    stdlib logging rejects, so every send failure crashed with TypeError)."""
    firebase_admin = pytest.importorskip("firebase_admin")
    from firebase_admin import messaging

    from apps.notifications.push_service import PushNotification, push_service

    monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_JSON", json.dumps(SAMPLE))
    monkeypatch.setattr(firebase_admin, "_apps", {"stub": object()})  # skip init

    def boom(*a, **k):
        raise RuntimeError("registration token is not valid")

    monkeypatch.setattr(messaging, "send", boom)

    result = push_service.send_to_user("tok", PushNotification("t", "b"))
    assert result is False
