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
