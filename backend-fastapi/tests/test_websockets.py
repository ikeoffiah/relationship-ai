import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from fastapi import WebSocketDisconnect, WebSocket
from app.api.websockets import joint_session_endpoint

@pytest.fixture
def mock_broker():
    broker = AsyncMock()
    return broker

@pytest.fixture
def mock_websocket(mock_broker):
    ws = AsyncMock(spec=WebSocket)
    app_mock = MagicMock()
    app_mock.state.broker = mock_broker
    ws.app = app_mock
    return ws

@pytest.mark.asyncio
async def test_websocket_joint_session_success(mock_websocket, mock_broker):
    # Setup the receive_text to yield one valid message then raise disconnect
    mock_websocket.receive_text.side_effect = [
        '{"message": "hello"}',
        WebSocketDisconnect()
    ]
    
    await joint_session_endpoint(mock_websocket, "session123")
    
    mock_broker.connect.assert_called_once_with("session123", mock_websocket)
    mock_broker.broadcast.assert_called_once_with("session123", {"message": "hello"})
    mock_broker.disconnect.assert_called_once_with("session123", mock_websocket)

@pytest.mark.asyncio
async def test_websocket_joint_session_invalid_json(mock_websocket, mock_broker):
    # Setup receive_text to yield invalid JSON then disconnect
    mock_websocket.receive_text.side_effect = [
        'not json',
        WebSocketDisconnect()
    ]
    
    await joint_session_endpoint(mock_websocket, "session321")
    
    mock_broker.connect.assert_called_once_with("session321", mock_websocket)
    mock_broker.broadcast.assert_not_called()
    mock_broker.disconnect.assert_called_once_with("session321", mock_websocket)

@pytest.mark.asyncio
async def test_websocket_unexpected_error(mock_websocket, mock_broker):
    # Throw a general exception
    mock_websocket.receive_text.side_effect = Exception("Surprise!")
    
    await joint_session_endpoint(mock_websocket, "session_err")
    
    mock_broker.connect.assert_called_once_with("session_err", mock_websocket)
    mock_broker.disconnect.assert_called_once_with("session_err", mock_websocket)
