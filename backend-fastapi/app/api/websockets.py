from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import structlog
import asyncio

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.websocket("/ws/joint/{session_id}")
async def joint_session_endpoint(websocket: WebSocket, session_id: str):
    from app.safety.sensitive_disclosures import SUSPENDED_JOINT_SESSIONS, BOTH_PARTNERS_ABUSE_RESPONSE
    if session_id in SUSPENDED_JOINT_SESSIONS:
        await websocket.accept()
        await websocket.send_text(json.dumps({"type": "error", "content": BOTH_PARTNERS_ABUSE_RESPONSE}))
        await websocket.close()
        return

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
                
                # Broadcast user's message immediately
                await broker.broadcast(session_id, message)
                
                # Execute LangGraph Pipeline
                # In production, we would instantiate or load SessionState from LangGraphSession DB model
                from app.orchestration.state import SessionState, SafetyState, AccessPolicy, StrategyMix
                from app.orchestration.graph import build_counseling_graph
                
                state = SessionState(
                    session_id=session_id,
                    user_id="user-via-ws", # Real app extracts from token
                    relationship_id=session_id,
                    session_type="joint",
                    access_policy=AccessPolicy(can_read_private=True, can_read_shared=True, can_cross_partner=True),
                    current_strategy=StrategyMix(primary="Validation", secondary="", focus=""),
                    safety_state=SafetyState(level="safe", score=0.0),
                    turn_number=1,
                    short_term_buffer=[{"role": "user", "content": message.get("content", ""), "timestamp": ""}],
                    retrieved_memories=[],
                    signal_vector=None,
                    personalization_modifiers={},
                    is_streaming=True
                )
                
                graph = build_counseling_graph()
                
                # We can stream output by iterating over events (or mocking streaming if LLM call is blocked)
                # For this implementation we'll just mock the stream of the final response
                result = await graph.ainvoke(state)
                final_response = result.get("llm_output", "No response generated.")
                
                # Mock Streaming back to clients
                words = final_response.split(" ")
                for word in words:
                    chunk = {
                        "type": "agent_stream",
                        "content": word + " "
                    }
                    await broker.broadcast(session_id, chunk)
                    await asyncio.sleep(0.05) # Simulate streaming delay
                
                # Send End of stream
                await broker.broadcast(session_id, {"type": "agent_stream_end"})
                
            except json.JSONDecodeError:
                logger.warning(
                    "invalid_json_received", session_id=session_id, data=data
                )
                continue

    except WebSocketDisconnect:
        logger.info("joint_session_disconnected", session_id=session_id)
        await broker.disconnect(session_id, websocket)
    except Exception as e:
        logger.error("joint_session_error", session_id=session_id, error=str(e))
        await broker.disconnect(session_id, websocket)
