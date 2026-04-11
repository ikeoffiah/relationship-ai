from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
import json
import structlog
from typing import Any

logger = structlog.get_logger(__name__)
router = APIRouter()

@router.websocket("/ws/joint/{session_id}")
async def joint_session_endpoint(websocket: WebSocket, session_id: str):
    # Retrieve the global broker from app state
    broker = websocket.app.state.broker
    
    await broker.connect(session_id, websocket)
    logger.info("joint_session_started", session_id=session_id)
    
    try:
        while True:
            # Receive text data from the client
            data = await websocket.receive_text()
            
            # Parse it just to ensure it's valid JSON before broadcasting, or enrich it
            # For simplicity, we just pass it along
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                logger.warning("invalid_json_received", session_id=session_id, data=data)
                continue
                
            # Broadcast to all connected clients in this session across all instances
            await broker.broadcast(session_id, message)
            
    except WebSocketDisconnect:
        logger.info("joint_session_disconnected", session_id=session_id)
        await broker.disconnect(session_id, websocket)
    except Exception as e:
        logger.error("joint_session_error", session_id=session_id, error=str(e))
        await broker.disconnect(session_id, websocket)
