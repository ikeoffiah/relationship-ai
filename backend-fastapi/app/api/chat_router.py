"""
Chat streaming endpoint (REL-90).

Drives the LangGraph counseling orchestration and streams its progress to the
client as Server-Sent Events. The event names and payload keys are fixed by
the Flutter client's parser in
mobile/lib/features/chat/services/session_service.dart.
"""

import json
import os
from typing import AsyncIterator

from fastapi import APIRouter, Body, Depends, Path
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.relationships import get_current_user_id
from app.orchestration.graph import build_counseling_graph
from app.orchestration.state import (
    AccessPolicy,
    SafetyState,
    SessionState,
    StrategyMix,
)

router = APIRouter()

# Number of characters emitted per `token` frame. The orchestration graph
# returns a complete string rather than a real token stream, so the response is
# chunked here to keep the client's incremental rendering meaningful.
TOKEN_CHUNK_SIZE = 24


class ChatMessageRequest(BaseModel):
    content: str = Field(..., description="The user's message")


def _sse(payload: dict) -> str:
    """Encode one SSE frame. The client splits on newlines, so payloads must
    be single-line JSON."""
    return f"data: {json.dumps(payload)}\n\n"


def crisis_resources() -> list[dict]:
    """
    Crisis resources surfaced alongside a safety event.

    Deliberately empty unless configured: these are region-specific and must be
    verified before display. Publishing an incorrect or invented hotline number
    to someone in crisis is worse than publishing none, so there is no default.
    Set CRISIS_RESOURCES to a JSON array of
    {"name": ..., "phone": ..., "url": ...} objects.
    """
    raw = os.environ.get("CRISIS_RESOURCES")
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return []
    return parsed if isinstance(parsed, list) else []


def _initial_state(session_id: str, user_id: str, content: str) -> SessionState:
    return SessionState(
        session_id=session_id,
        user_id=user_id,
        relationship_id=None,
        session_type="individual",
        access_policy=AccessPolicy(
            can_read_private=False, can_read_shared=False, can_cross_partner=False
        ),
        current_strategy=StrategyMix(primary="", secondary="", focus=""),
        safety_state=SafetyState(level="safe", score=0.0),
        turn_number=1,
        short_term_buffer=[{"role": "user", "content": content, "timestamp": ""}],
        retrieved_memories=[],
        signal_vector=None,
        personalization_modifiers={},
        is_streaming=True,
    )


async def stream_counseling_turn(
    session_id: str, user_id: str, content: str
) -> AsyncIterator[str]:
    """
    Run one counseling turn, emitting SSE frames as the graph progresses.

    `done` is always emitted last, including on failure, because the client
    treats it as the end-of-turn signal and will otherwise wait indefinitely.
    """
    graph = build_counseling_graph()
    state = _initial_state(session_id, user_id, content)

    final_output = ""
    safety_emitted = False

    try:
        async for update in graph.astream(state, stream_mode="updates"):
            for node_name, node_update in update.items():
                if not isinstance(node_update, dict):
                    continue

                safety = node_update.get("safety_state")
                if safety and safety.get("level") != "safe" and not safety_emitted:
                    safety_emitted = True
                    yield _sse(
                        {
                            "type": "safety_triggered",
                            "level": safety["level"],
                            "resources": crisis_resources(),
                        }
                    )

                strategy = node_update.get("current_strategy")
                if strategy and strategy.get("primary"):
                    yield _sse(
                        {"type": "strategy_change", "strategy": strategy["primary"]}
                    )

                if node_update.get("llm_output"):
                    final_output = node_update["llm_output"]

        for i in range(0, len(final_output), TOKEN_CHUNK_SIZE):
            yield _sse(
                {"type": "token", "content": final_output[i : i + TOKEN_CHUNK_SIZE]}
            )
    finally:
        yield _sse({"type": "done"})


@router.post("/api/v1/sessions/{session_id}/messages")
async def send_message(
    session_id: str = Path(...),
    request: ChatMessageRequest = Body(...),
    user_id: str = Depends(get_current_user_id),
):
    return StreamingResponse(
        stream_counseling_turn(session_id, user_id, request.content),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Prevent proxy buffering, which would otherwise defeat streaming.
            "X-Accel-Buffering": "no",
        },
    )
