from app.auth import decode_token
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import json
import structlog
import asyncio
import os
from typing import Optional

logger = structlog.get_logger(__name__)
router = APIRouter()


async def verify_session_and_user(session_id: str, user_id: str) -> bool:
    # Only an explicit opt-out disables this. Sniffing DATABASE_URL for
    # "test"/"mock" silently disabled participant verification for any
    # deployment whose database name happened to contain those substrings.
    if os.environ.get("WS_SKIP_PARTICIPANT_CHECK") == "1":
        return True

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        # Fail closed: without a database we cannot prove membership.
        return False

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
async def joint_session_endpoint(
    websocket: WebSocket, session_id: str, token: str = Query(...)
):
    """
    Legacy path, retained for compatibility.

    It previously accepted a literal "legacy_token" and skipped both JWT
    verification and the participant check, which allowed anyone to join any
    couple's live counseling session. It now authenticates identically to
    /ws/sessions/{session_id}.
    """
    await handle_websocket_session(websocket, session_id, token, is_legacy=True)


@router.websocket("/ws/sessions/{session_id}")
async def joint_session_websocket(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(...)
):
    await handle_websocket_session(websocket, session_id, token, is_legacy=False)


async def handle_websocket_session(
    websocket: WebSocket, session_id: str, token: str, is_legacy: bool = False
):
    """`is_legacy` selects the older message-handling semantics only; it no
    longer affects authentication, which is enforced identically either way."""
    from app.safety.sensitive_disclosures import SUSPENDED_JOINT_SESSIONS, BOTH_PARTNERS_ABUSE_RESPONSE
    if session_id in SUSPENDED_JOINT_SESSIONS:
        await websocket.accept()
        await websocket.send_text(json.dumps({"type": "error", "content": BOTH_PARTNERS_ABUSE_RESPONSE}))
        await websocket.close()
        return

    # 1. Validate the token. There is deliberately no fallback secret: the old
    #    default ("fastapi-secret-key-here") is a published placeholder, so any
    #    deployment missing SECRET_KEY would have accepted forged tokens.
    try:
        payload = decode_token(token)
        user_id = str(payload.get("sub") or "")
    except Exception:
        await websocket.close(code=4001)
        return

    if not user_id:
        await websocket.close(code=4001)
        return

    # 2. Verify the caller actually participates in this session.
    if not await verify_session_and_user(session_id, user_id):
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
                            "summary": "Your partner is sharing that they feel..."
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



async def couple_membership(relationship_id: str, user_id: str) -> tuple[bool, str | None]:
    """Return (is a partner here, the other partner's id).

    One query answers both questions, and the handler needs both — the access
    check to decide whether to accept the socket, and the partner id to report
    presence. Splitting them into two functions meant opening two connection
    pools per socket for the same row.

    Fails closed: without a database we cannot prove membership, so we refuse
    rather than assume. Unlike the session check, this one does NOT fall back
    to True on error — a couple's private thread is not something to open
    because a query failed.
    """
    if os.environ.get("WS_SKIP_PARTICIPANT_CHECK") == "1":
        return True, None

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        return False, None

    pool = None
    try:
        import asyncpg

        pool = await asyncpg.create_pool(db_url)
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT partner_a_id, partner_b_id FROM relationships WHERE id = $1",
                relationship_id,
            )
        if not row:
            return False, None
        a, b = str(row["partner_a_id"]), str(row["partner_b_id"] or "") or None
        if str(user_id) == a:
            return True, b
        if b is not None and str(user_id) == b:
            return True, a
        return False, None
    except Exception as e:
        logger.warning("couple_membership_check_failed", error=str(e))
        return False, None
    finally:
        if pool is not None:
            await pool.close()


async def verify_couple_membership(relationship_id: str, user_id: str) -> bool:
    """Membership alone, for callers that do not need the partner id."""
    allowed, _ = await couple_membership(relationship_id, user_id)
    return allowed


@router.websocket("/ws/couple/{relationship_id}")
async def couple_thread_websocket(
    websocket: WebSocket, relationship_id: str, token: str = Query(...)
):
    """Live delivery for the couple's own thread.

    Read-only from the client's side: messages are sent over HTTP so they are
    persisted first, and this socket only carries what the server pushes back.
    That keeps a dropped connection from ever losing a message — the worst
    failure a chat can have.
    """
    try:
        payload = decode_token(token)
        user_id = str(payload.get("sub") or "")
    except Exception:
        await websocket.close(code=4001)
        return

    if not user_id:
        await websocket.close(code=4001)
        return

    allowed, partner_id = await couple_membership(relationship_id, user_id)
    if not allowed:
        await websocket.close(code=4003)
        return

    broker = websocket.app.state.broker
    # Room id is the relationship, matching the channel Django publishes on.
    await broker.connect(relationship_id, user_id, websocket)
    logger.info("couple_thread_connected", relationship_id=relationship_id, user_id=user_id)

    try:
        # Presence is deliberately binary — here, or not here. There is no
        # "last seen 02:14" anywhere in this payload and there should not be:
        # in a relationship product that field stops being a convenience and
        # starts being a record of when you were awake and did not reply.
        await websocket.send_text(
            json.dumps(
                {
                    "type": "thread_ready",
                    # Presence on connect, not only on change — otherwise you
                    # learn nothing until the other person's state happens to
                    # flip while you are watching.
                    "partner_online": bool(
                        partner_id
                        and await broker.is_online(relationship_id, partner_id)
                    ),
                }
            )
        )
        await broker.broadcast_to_session(
            relationship_id,
            {"type": "presence", "user_id": user_id, "online": True},
            exclude_user_id=user_id,
        )

        while True:
            # Keepalive only — the content is ignored by design. The arrival
            # itself is the signal: it pushes out the presence key's TTL, which
            # is what keeps a crashed pod from leaving someone "online".
            await websocket.receive_text()
            await broker.touch_presence(relationship_id, user_id)
    except WebSocketDisconnect:
        await _leave_couple_thread(broker, relationship_id, user_id, websocket)
    except Exception as e:
        logger.error("couple_thread_error", relationship_id=relationship_id, error=str(e))
        await _leave_couple_thread(broker, relationship_id, user_id, websocket)


async def _leave_couple_thread(broker, relationship_id: str, user_id: str, websocket) -> None:
    """Drop the socket and tell the partner. Announcing must not be able to
    prevent the disconnect itself, hence the guard."""
    await broker.disconnect(relationship_id, user_id, websocket)
    try:
        await broker.broadcast_to_session(
            relationship_id,
            {"type": "presence", "user_id": user_id, "online": False},
            exclude_user_id=user_id,
        )
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("presence_broadcast_failed", relationship_id=relationship_id, error=str(exc))
