import pytest
from tests.conftest import make_token
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket, WebSocketDisconnect
from app.api.websockets import joint_session_websocket
from app.counseling.broker import TurnHoldManager


@pytest.fixture
def mock_websocket():
    ws = AsyncMock(spec=WebSocket)
    app_mock = MagicMock()
    ws.app = app_mock
    return ws


@pytest.mark.asyncio
async def test_jwt_validation_failure(mock_websocket):
    # Invalid token should close the connection with 4001
    await joint_session_websocket(mock_websocket, "session123", token="invalid")
    mock_websocket.close.assert_called_once_with(code=4001)


@pytest.mark.asyncio
async def test_jwt_validation_success_and_routing(mock_websocket):
    token = make_token("user123")
    
    broker = AsyncMock()
    mock_websocket.app.state.broker = broker

    # Setup the receive_text to yield one typing_start then disconnect
    mock_websocket.receive_text.side_effect = [
        '{"type": "typing_start"}',
        WebSocketDisconnect()
    ]

    with patch("app.api.websockets.verify_session_and_user", return_value=True):
        await joint_session_websocket(mock_websocket, "session123", token=token)
        
        # Verify connect and routing
        broker.connect.assert_called_once_with("session123", "user123", mock_websocket)
        broker.broadcast_to_session.assert_any_call(
            "session123",
            {"type": "partner_typing"},
            exclude_user_id="user123"
        )


@pytest.mark.asyncio
async def test_turn_hold_manager_workflow():
    broker = AsyncMock()
    # Use actual redis connection mock or AsyncMock
    broker.redis = AsyncMock()
    
    # Mock redis setex and exists
    broker.redis.setex = AsyncMock()
    broker.redis.exists = AsyncMock(return_value=1)
    broker.redis.ttl = AsyncMock(return_value=5)
    broker.redis.get = AsyncMock(return_value="queued content")

    manager = TurnHoldManager(broker)
    
    await manager.activate_window("session123", "user123")
    broker.redis.setex.assert_called_once_with("reflection_window:session123:user123", 10, "active")

    active = await manager.is_window_active("session123", "user123")
    assert active is True

    ttl = await manager.get_remaining_seconds("session123", "user123")
    assert ttl == 5
