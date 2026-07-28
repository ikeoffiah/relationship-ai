import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import WebSocketDisconnect, WebSocket
from app.api.websockets import joint_session_endpoint
from tests.conftest import make_token


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
        WebSocketDisconnect(),
    ]

    await joint_session_endpoint(mock_websocket, "session123", token=make_token("user123"))

    mock_broker.connect.assert_called_once_with("session123", "user123", mock_websocket)
    mock_broker.broadcast.assert_any_call("session123", {"message": "hello"})
    mock_broker.disconnect.assert_called_once_with("session123", "user123", mock_websocket)


@pytest.mark.asyncio
async def test_websocket_joint_session_invalid_json(mock_websocket, mock_broker):
    # Setup receive_text to yield invalid JSON then disconnect
    mock_websocket.receive_text.side_effect = ["not json", WebSocketDisconnect()]

    await joint_session_endpoint(mock_websocket, "session321", token=make_token("user123"))

    mock_broker.connect.assert_called_once_with("session321", "user123", mock_websocket)
    mock_broker.broadcast.assert_not_called()
    mock_broker.disconnect.assert_called_once_with("session321", "user123", mock_websocket)


@pytest.mark.asyncio
async def test_websocket_unexpected_error(mock_websocket, mock_broker):
    # Throw a general exception
    mock_websocket.receive_text.side_effect = Exception("Surprise!")

    await joint_session_endpoint(mock_websocket, "session_err", token=make_token("user123"))

    mock_broker.connect.assert_called_once_with("session_err", "user123", mock_websocket)
    mock_broker.disconnect.assert_called_once_with("session_err", "user123", mock_websocket)


@pytest.mark.asyncio
async def test_websocket_joint_session_suspended(mock_websocket, mock_broker):
    from app.safety.sensitive_disclosures import SUSPENDED_JOINT_SESSIONS, BOTH_PARTNERS_ABUSE_RESPONSE
    import json
    
    SUSPENDED_JOINT_SESSIONS.add("session-suspended-123")
    
    try:
        await joint_session_endpoint(mock_websocket, "session-suspended-123", token=make_token("user123"))
        
        mock_websocket.accept.assert_called_once()
        mock_websocket.send_text.assert_called_once_with(json.dumps({
            "type": "error",
            "content": BOTH_PARTNERS_ABUSE_RESPONSE
        }))
        mock_websocket.close.assert_called_once()
        mock_broker.connect.assert_not_called()
    finally:
        SUSPENDED_JOINT_SESSIONS.remove("session-suspended-123")



# ── Couple thread socket ────────────────────────────────────────────────────
# This socket carries a couple's private conversation, so its access check is
# stricter than the session one: it fails closed on any error rather than
# falling back to allowing the connection.


@pytest.mark.asyncio
async def test_couple_membership_allows_either_partner(monkeypatch):
    from app.api import websockets

    monkeypatch.setenv("DATABASE_URL", "postgres://x/y")
    monkeypatch.delenv("WS_SKIP_PARTICIPANT_CHECK", raising=False)

    class _Conn:
        async def fetchrow(self, *a, **k):
            return {"partner_a_id": "alex", "partner_b_id": "sam"}

    import sys
    import types

    fake = types.ModuleType("asyncpg")

    class _Acquire:
        async def __aenter__(self):
            return _Conn()

        async def __aexit__(self, *a):
            return False

    class _Pool:
        def acquire(self):
            return _Acquire()

        async def close(self):
            return None

    async def create_pool(url):
        return _Pool()

    fake.create_pool = create_pool
    monkeypatch.setitem(sys.modules, "asyncpg", fake)

    assert await websockets.verify_couple_membership("rel-1", "alex") is True
    assert await websockets.verify_couple_membership("rel-1", "sam") is True
    assert await websockets.verify_couple_membership("rel-1", "stranger") is False


@pytest.mark.asyncio
async def test_couple_membership_fails_closed_without_a_database(monkeypatch):
    from app.api import websockets

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("WS_SKIP_PARTICIPANT_CHECK", raising=False)

    assert await websockets.verify_couple_membership("rel-1", "alex") is False


@pytest.mark.asyncio
async def test_couple_membership_fails_closed_on_a_database_error(monkeypatch):
    """The session check falls back to True on error; this one must not.

    A couple's private thread is not something to open because a query failed.
    """
    from app.api import websockets
    import sys
    import types

    monkeypatch.setenv("DATABASE_URL", "postgres://x/y")
    monkeypatch.delenv("WS_SKIP_PARTICIPANT_CHECK", raising=False)

    fake = types.ModuleType("asyncpg")

    async def create_pool(url):
        raise RuntimeError("database unreachable")

    fake.create_pool = create_pool
    monkeypatch.setitem(sys.modules, "asyncpg", fake)

    assert await websockets.verify_couple_membership("rel-1", "alex") is False
