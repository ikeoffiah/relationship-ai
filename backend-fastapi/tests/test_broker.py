import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.counseling.broker import JointSessionBroker
from fastapi import WebSocket

@pytest.fixture
def mock_redis():
    redis_mock = AsyncMock()
    pubsub_mock = AsyncMock()
    
    # pubsub() is a sync call
    redis_mock.pubsub = MagicMock(return_value=pubsub_mock)
    
    # Setup pubsub listen to return one message then cancel itself to exit the async generator
    async def mock_listen():
        yield {"type": "message", "data": '{"test": "data"}'}
        raise asyncio.CancelledError()
        
    pubsub_mock.listen = mock_listen
    return redis_mock

@pytest.fixture
def mock_websocket():
    ws = AsyncMock(spec=WebSocket)
    return ws

@pytest.mark.asyncio
async def test_broker_connect_disconnect(mocker, mock_redis, mock_websocket):
    mocker.patch("app.counseling.broker.redis.from_url", return_value=mock_redis)
    
    broker = JointSessionBroker("redis://mock")
    
    # Test connect
    session_id = "session1"
    await broker.connect(session_id, mock_websocket)
    
    mock_websocket.accept.assert_called_once()
    assert session_id in broker.active_sessions
    assert mock_websocket in broker.active_sessions[session_id]
    mock_redis.pubsub.assert_called_once()
    
    # Wait for the listen task to finish execution (it raises CancelledError and exits gracefully)
    await asyncio.sleep(0.01)
    
    # Test disconnect
    await broker.disconnect(session_id, mock_websocket)
    
    assert session_id not in broker.active_sessions
    assert session_id not in broker.pubsub_tasks

@pytest.mark.asyncio
async def test_broker_broadcast(mocker, mock_redis):
    mocker.patch("app.counseling.broker.redis.from_url", return_value=mock_redis)
    
    broker = JointSessionBroker("redis://mock")
    session_id = "session1"
    message = {"hello": "world"}
    
    await broker.broadcast(session_id, message)
    
    mock_redis.publish.assert_called_once_with(f"session:{session_id}", json.dumps(message))

@pytest.mark.asyncio
async def test_broker_listen_forwarding(mocker, mock_redis, mock_websocket):
    mocker.patch("app.counseling.broker.redis.from_url", return_value=mock_redis)
    broker = JointSessionBroker("redis://mock")
    
    # We add the websocket manually to simulate an active session
    broker.active_sessions["session_listen"] = [mock_websocket]
    
    # Call listen__to_redis directly to test forwarding logic
    await broker._listen_to_redis("session_listen", mock_redis.pubsub())
    
    mock_websocket.send_text.assert_called_once_with('{"test": "data"}')

@pytest.mark.asyncio
async def test_disconnect_nonexistent_or_already_removed(mocker, mock_redis, mock_websocket):
    mocker.patch("app.counseling.broker.redis.from_url", return_value=mock_redis)
    broker = JointSessionBroker("redis://mock")
    
    # Disconnect when no session
    await broker.disconnect("none", mock_websocket)
    
    # Disconnect when websocket not in list
    broker.active_sessions["session1"] = []
    await broker.disconnect("session1", mock_websocket)
    
    assert "session1" not in broker.active_sessions

@pytest.mark.asyncio
async def test_listen_to_redis_exception(mocker, mock_redis, mock_websocket):
    mocker.patch("app.counseling.broker.redis.from_url", return_value=mock_redis)
    broker = JointSessionBroker("redis://mock")
    
    pubsub_mock = mock_redis.pubsub()
    
    async def mock_listen_error():
        yield {"type": "message", "data": "bad"}
        raise Exception("Fatal Error")
        
    pubsub_mock.listen = mock_listen_error
    
    # Shouldn't crash
    await broker._listen_to_redis("session1", pubsub_mock)
