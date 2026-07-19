import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.api.relay_router import _relay_store, _audit_trail

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_store():
    _relay_store.clear()
    _audit_trail.clear()

def test_send_relay_success():
    response = client.post(
        "/api/v1/sessions/session123/relay",
        json={"content": "I feel unhappy with our communication.", "consent_to_relay": True}
    )
    assert response.status_code == 200
    data = response.json()
    assert "relay_id" in data
    assert data["status"] == "ready"
    
    # Verify in-memory store has it
    relay_id = data["relay_id"]
    assert relay_id in _relay_store
    assert _relay_store[relay_id]["original_content"] == "I feel unhappy with our communication."
    assert "Observation:" in _relay_store[relay_id]["translated_content"]
    assert _relay_store[relay_id]["translation_quality_score"] >= 0.6

def test_send_relay_without_consent():
    response = client.post(
        "/api/v1/sessions/session123/relay",
        json={"content": "I feel unhappy.", "consent_to_relay": False}
    )
    assert response.status_code == 400

def test_send_relay_low_quality():
    response = client.post(
        "/api/v1/sessions/session123/relay",
        json={"content": "low_quality message", "consent_to_relay": True}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    
    # Should be flagged for quality review and not ready
    relay_id = data["relay_id"]
    assert _relay_store[relay_id]["status"] == "quality_review"

def test_get_pending_relays():
    # Send a normal one
    res1 = client.post(
        "/api/v1/sessions/session123/relay",
        json={"content": "Hello partner", "consent_to_relay": True}
    )
    
    # Send a low quality one
    client.post(
        "/api/v1/sessions/session123/relay",
        json={"content": "low_quality hello", "consent_to_relay": True}
    )
    
    # Fetch pending for user-B (recipient)
    pending_res = client.get("/api/v1/users/user-B/relay/pending")
    assert pending_res.status_code == 200
    pending_data = pending_res.json()
    
    # Only the first (ready) message should be here, the quality_review one should be omitted
    assert len(pending_data) == 1
    assert pending_data[0]["relay_id"] == res1.json()["relay_id"]

def test_deliver_relay():
    res = client.post(
        "/api/v1/sessions/session123/relay",
        json={"content": "Message to deliver", "consent_to_relay": True}
    )
    relay_id = res.json()["relay_id"]
    
    delivery_res = client.post(
        f"/api/v1/relay/{relay_id}/deliver",
        json={"recipient_chose_version": "ai_translated"}
    )
    assert delivery_res.status_code == 200
    data = delivery_res.json()
    assert data["status"] == "delivered"
    assert data["recipient_chose_version"] == "ai_translated"
    
    # Verify it is no longer pending
    pending_res = client.get("/api/v1/users/user-B/relay/pending")
    assert len(pending_res.json()) == 0

def test_withdraw_relay():
    res = client.post(
        "/api/v1/sessions/session123/relay",
        json={"content": "Withdraw me", "consent_to_relay": True}
    )
    relay_id = res.json()["relay_id"]
    
    # Withdraw
    withdraw_res = client.delete(f"/api/v1/relay/{relay_id}")
    assert withdraw_res.status_code == 200
    assert withdraw_res.json()["status"] == "withdrawn"
    
    # Delivery should now fail
    delivery_res = client.post(
        f"/api/v1/relay/{relay_id}/deliver",
        json={"recipient_chose_version": "original"}
    )
    assert delivery_res.status_code == 400

def test_withdraw_after_delivery_fails():
    res = client.post(
        "/api/v1/sessions/session123/relay",
        json={"content": "Message", "consent_to_relay": True}
    )
    relay_id = res.json()["relay_id"]
    
    # Deliver
    client.post(
        f"/api/v1/relay/{relay_id}/deliver",
        json={"recipient_chose_version": "original"}
    )
    
    # Withdraw should fail
    withdraw_res = client.delete(f"/api/v1/relay/{relay_id}")
    assert withdraw_res.status_code == 400

def test_expired_relay():
    res = client.post(
        "/api/v1/sessions/session123/relay",
        json={"content": "Message", "consent_to_relay": True}
    )
    relay_id = res.json()["relay_id"]
    
    # Force expire in-memory store
    _relay_store[relay_id]["expires_at"] = datetime.utcnow() - timedelta(minutes=1)
    
    # Delivery should fail
    delivery_res = client.post(
        f"/api/v1/relay/{relay_id}/deliver",
        json={"recipient_chose_version": "original"}
    )
    assert delivery_res.status_code == 400
    
    # Pending list should omit it
    pending_res = client.get("/api/v1/users/user-B/relay/pending")
    assert len(pending_res.json()) == 0
