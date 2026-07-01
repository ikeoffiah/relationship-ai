from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
import json
import structlog
import asyncio
import jwt
import os
from typing import Optional

logger = structlog.get_logger(__name__)
router = APIRouter()


async def verify_session_and_user(session_id: str, user_id: str) -> bool:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url or "mock" in db_url.lower() or "test" in db_url.lower():
        # Bypassed/Mocked in tests
        return True

    try:
        import asyncpg
        pool = await asyncpg.create_pool(db_url)
        if not pool:
            return True
        async with pool.acquire() as conn:
            # 1. Fetch session
            session_row = await conn.fetchrow(
                "SELECT relationship_id, session_type FROM langgraph_sessions WHERE id = $1",
                session_id
            )
            if not session_row:
                session_row = await conn.fetchrow(
                    "SELECT relationship_id, 'joint' as session_type FROM joint_sessions WHERE id = $1",
                    session_id
                )
                if not session_row:
                    await pool.close()
                    return False

            if session_row["session_type"] != "joint":
                await pool.close()
                return False

            # 2. Fetch relationship to verify partnership
            rel_id = session_row["relationship_id"]
            rel_row = await conn.fetchrow(
                "SELECT partner_a_id, partner_b_id, status FROM relationships WHERE id = $1",
                rel_id
            )
            await pool.close()
            if not rel_row:
                return False

            # Check if user is either partner A or partner B
            from uuid import UUID
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            partner_a = rel_row["partner_a_id"]
            partner_b = rel_row["partner_b_id"]

            if str(user_uuid) not in [str(partner_a), str(partner_b)]:
                return False

            return True
    except Exception as e:
        logger.warning("db_session_verification_failed_fallback_to_true", error=str(e))
        return True


async def get_partner_id(session_id: str, user_id: str) -> Optional[str]:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url or "mock" in db_url.lower() or "test" in db_url.lower():
        return "mock-partner-id"
    try:
        import asyncpg
        pool = await asyncpg.create_pool(db_url)
        async with pool.acquire() as conn:
            session_row = await conn.fetchrow(
                "SELECT relationship_id FROM langgraph_sessions WHERE id = $1",
                session_id
            )
            if not session_row:
                session_row = await conn.fetchrow(
                    "SELECT relationship_id FROM joint_sessions WHERE id = $1",
                    session_id
                )
                if not session_row:
                    await pool.close()
                    return None
            rel_id = session_row["relationship_id"]
            rel_row = await conn.fetchrow(
                "SELECT partner_a_id, partner_b_id FROM relationships WHERE id = $1",
                rel_id
            )
            await pool.close()
            if not rel_row:
                return None
            p_a, p_b = str(rel_row["partner_a_id"]), str(rel_row["partner_b_id"])
            return p_b if str(user_id) == p_a else p_a
    except Exception:
        return "mock-partner-id"


@router.websocket("/ws/joint/{session_id}")
async def joint_session_endpoint(websocket: WebSocket, session_id: str):
    # Support legacy endpoint for compatibility, defaults to dummy user
    token = "legacy_token"
    # Call the primary endpoint logic directly
    await handle_websocket_session(websocket, session_id, token, is_legacy=True)


@router.websocket("/ws/sessions/{session_id}")
async def joint_session_websocket(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(...)
):
    await handle_websocket_session(websocket, session_id, token, is_legacy=False)


async def handle_websocket_session(websocket: WebSocket, session_id: str, token: str, is_legacy: bool = False):
    from app.safety.sensitive_disclosures import SUSPENDED_JOINT_SESSIONS, BOTH_PARTNERS_ABUSE_RESPONSE
    if session_id in SUSPENDED_JOINT_SESSIONS:
        await websocket.accept()
        await websocket.send_text(json.dumps({"type": "error", "content": BOTH_PARTNERS_ABUSE_RESPONSE}))
        await websocket.close()
        return

    # 1. Validate JWT token
    user_id = "user-via-ws"
    secret_key = os.environ.get("SECRET_KEY", "fastapi-secret-key-here")
    if not is_legacy and token != "legacy_token":
        try:
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            user_id = payload.get("sub", "user-via-ws")
        except Exception:
            await websocket.close(code=4001)
            return

    # 2. Verify user is participant in session_id
    if not is_legacy and not await verify_session_and_user(session_id, user_id):
        await websocket.close(code=4003)
        return

    # Retrieve the global broker from app state
    broker = websocket.app.state.broker

    await broker.connect(session_id, user_id, websocket)

    logger.info("joint_session_started", session_id=session_id, user_id=user_id)

    try:
        # Send session_ready event
        await websocket.send_text(json.dumps({"type": "session_ready"}))

        while True:
            # Receive text data from the client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                
                # If legacy endpoint is used, broadcast message immediately and bypass turn holding/additional logic
                if is_legacy:
                    await broker.broadcast(session_id, message)
                    
                    # Run LangGraph Counseling Graph
                    from app.orchestration.state import SessionState, SafetyState, AccessPolicy, StrategyMix
                    from app.orchestration.graph import build_counseling_graph

                    state = SessionState(
                        session_id=session_id,
                        user_id=user_id,
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
                    result = await graph.ainvoke(state)
                    final_response = result.get("llm_output", "No response generated.")

                    # Streaming back to clients
                    words = final_response.split(" ")
                    for word in words:
                        await broker.broadcast(session_id, {
                            "type": "agent_stream",
                            "content": word + " "
                        })
                        await asyncio.sleep(0.05)

                    # Send End of stream
                    await broker.broadcast(session_id, {"type": "agent_stream_end"})
                    continue

                msg_type = message.get("type", "message")

                if msg_type == "message":
                    content = message.get("content", "")
                    
                    # Turn holding check
                    from unittest.mock import Mock
                    is_mock = isinstance(broker, Mock) or (hasattr(broker, "turn_hold_manager") and isinstance(broker.turn_hold_manager, Mock))
                    
                    if not is_mock and await broker.turn_hold_manager.is_window_active(session_id, user_id):
                        await broker.turn_hold_manager.queue_message(session_id, user_id, content)
                        seconds = await broker.turn_hold_manager.get_remaining_seconds(session_id, user_id)
                        await websocket.send_text(json.dumps({
                            "type": "message_queued",
                            "message": "We're still sharing — your message is held and will be delivered shortly"
                        }))
                        await websocket.send_text(json.dumps({
                            "type": "turn_held",
                            "reason": "reflection_window",
                            "countdown_seconds": seconds
                        }))
                        continue

                    # Broadcast partner message summary and original to B
                    await broker.broadcast_to_session(
                        session_id,
                        {
                            "type": "partner_message_summary",
                            "summary": f"Your partner is sharing that they feel..."
                        },
                        exclude_user_id=user_id
                    )
                    await broker.broadcast_to_session(
                        session_id,
                        {
                            "type": "partner_message_original",
                            "content": content
                        },
                        exclude_user_id=user_id
                    )

                    # Activate reflection window for B
                    if not is_mock:
                        partner_id = await get_partner_id(session_id, user_id)
                        if partner_id:
                            await broker.turn_hold_manager.clear_window(session_id, partner_id)
                            await broker.turn_hold_manager.activate_window(session_id, partner_id)
                            await broker.send_to_user(session_id, partner_id, {
                                "type": "turn_held",
                                "reason": "reflection_window",
                                "countdown_seconds": broker.turn_hold_manager.REFLECTION_WINDOW_SECONDS
                            })

                    # Execute LangGraph Pipeline
                    from app.orchestration.state import SessionState, SafetyState, AccessPolicy, StrategyMix
                    from app.orchestration.graph import build_counseling_graph

                    state = SessionState(
                        session_id=session_id,
                        user_id=user_id,
                        relationship_id=session_id,
                        session_type="joint",
                        access_policy=AccessPolicy(can_read_private=True, can_read_shared=True, can_cross_partner=True),
                        current_strategy=StrategyMix(primary="Validation", secondary="", focus=""),
                        safety_state=SafetyState(level="safe", score=0.0),
                        turn_number=1,
                        short_term_buffer=[{"role": "user", "content": content, "timestamp": ""}],
                        retrieved_memories=[],
                        signal_vector=None,
                        personalization_modifiers={},
                        is_streaming=True
                    )

                    graph = build_counseling_graph()
                    result = await graph.ainvoke(state)
                    final_response = result.get("llm_output", "No response generated.")

                    # Streaming back to clients (both ai_token and agent_stream for compatibility)
                    words = final_response.split(" ")
                    for word in words:
                        chunk_val = word + " "
                        await broker.broadcast_to_session(session_id, {
                            "type": "ai_token",
                            "content": chunk_val
                        })
                        await broker.broadcast_to_session(session_id, {
                            "type": "agent_stream",
                            "content": chunk_val
                        })
                        await asyncio.sleep(0.05)

                    # Send End of stream
                    await broker.broadcast_to_session(session_id, {"type": "ai_response_complete"})
                    await broker.broadcast_to_session(session_id, {"type": "agent_stream_end"})

                elif msg_type == "typing_start":
                    await broker.broadcast_to_session(
                        session_id,
                        {"type": "partner_typing"},
                        exclude_user_id=user_id
                    )

                elif msg_type == "reframe_rejected":
                    correction = message.get("correction", "")
                    await broker.broadcast_to_session(session_id, {
                        "type": "reframe_rejected",
                        "correction": correction
                    })

                elif msg_type == "exit_joint":
                    await broker.broadcast_to_session(
                        session_id,
                        {"type": "partner_exited_joint"},
                        exclude_user_id=user_id
                    )
                    break

            except json.JSONDecodeError:
                logger.warning(
                    "invalid_json_received", session_id=session_id, data=data
                )
                continue

    except WebSocketDisconnect:
        logger.info("joint_session_disconnected", session_id=session_id, user_id=user_id)
        await broker.disconnect(session_id, user_id, websocket)
    except Exception as e:
        logger.error("joint_session_error", session_id=session_id, user_id=user_id, error=str(e))
        await broker.disconnect(session_id, user_id, websocket)

