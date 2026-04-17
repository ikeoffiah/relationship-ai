import os
import importlib
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    from app.main import app

    with TestClient(app) as client:
        yield client


def test_read_main(test_client):
    response = test_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "RelationshipAI FastAPI Service is running"}


def test_health(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_sentry_initialization():
    # Reload the module with SENTRY_DSN set to cover the import-time init block
    with patch.dict(
        os.environ,
        {"SENTRY_DSN": "https://test@sentry.io/123", "REDIS_URL": "redis://mock"},
    ):
        with patch("app.main.sentry_sdk.init") as mock_init:
            import app.main

            importlib.reload(app.main)
            mock_init.assert_called_once()
