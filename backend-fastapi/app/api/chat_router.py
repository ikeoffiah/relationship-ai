"""
Chat streaming endpoint (REL-90).

Drives the LangGraph counseling orchestration and streams its progress to the
client as Server-Sent Events. The event names and payload keys are fixed by
the Flutter client's parser in
mobile/lib/features/chat/services/session_service.dart.
"""

import json
import os
from typing import AsyncIterator, Optional

import asyncpg
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

# Longest excerpt stored for the history list's preview.
SUMMARY_PREVIEW_MAX = 200


async def get_optional_pool() -> AsyncIterator[Optional[asyncpg.Pool]]:
    """
    A DB pool for best-effort session persistence, or None if unavailable.

    Persisting the session must never break the user's live chat, so a missing
    or unreachable database yields None and the turn simply isn't recorded.
    """
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        yield None
        return
    try:
        pool = await asyncpg.create_pool(db_url)
    except Exception:
        yield None
        return
    try:
        yield pool
    finally:
        await pool.close()


async def persist_turn(
    pool: Optional[asyncpg.Pool],
    session_id: str,
    user_id: str,
    assistant_output: str,
) -> None:
    """
    Upsert the session row so it appears in history, incrementing the turn
    count and refreshing the preview. Best-effort: any failure (no pool, a
    non-UUID session id, a missing table) is swallowed.
    """
    if pool is None:
        return
    preview = assistant_output.strip()[:SUMMARY_PREVIEW_MAX]
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO langgraph_sessions
                    (id, user_id, session_type, state_payload,
                     turn_count, summary_preview, created_at, updated_at)
                VALUES ($1, $2, 'individual', '{}', 1, $3, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET
                    turn_count = langgraph_sessions.turn_count + 1,
                    summary_preview = EXCLUDED.summary_preview,
                    updated_at = NOW()
                """,
                session_id, user_id, preview,
            )
    except Exception:
        # History is a convenience; never let it interrupt counseling.
        return


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


async def fetch_personalization(
    pool: Optional[asyncpg.Pool], user_id: str
) -> dict:
    """The user's attachment/communication style, used to personalize the
    counseling system prompt. Best-effort: any failure yields no modifiers."""
    if pool is None:
        return {}
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT attachment_style, communication_style_self_report
                FROM personalization_profiles
                WHERE user_id = $1
                """,
                user_id,
            )
    except Exception:
        return {}
    if not row:
        return {}
    return {
        "attachment_style": row["attachment_style"] or "",
        "communication_style": row["communication_style_self_report"] or "",
    }


def _clean_list(raw) -> list:
    """Keep only plain, non-empty string items; drop anything that looks
    encrypted (a future ``ENC:`` prefix) so we never surface ciphertext.
    Accepts a Python list or a JSONB string (asyncpg returns JSONB as text)."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return []
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        s = item if isinstance(item, str) else None
        if s and s.strip() and not s.startswith("ENC:"):
            out.append(s.strip())
    return out


async def fetch_shared_context(pool: Optional[asyncpg.Pool], user_id: str) -> dict:
    """The couple's PLAINTEXT, shared-by-design context — what they're working on
    together and themes/values they've named — so the counselor can hold the
    relationship in mind, not just the individual. Never reads one partner's
    private words (e.g. repair-note text) or any encrypted field. Best-effort:
    any failure yields an empty dict and counseling proceeds unchanged.
    """
    if pool is None:
        return {}
    try:
        async with pool.acquire() as conn:
            rel = await conn.fetchrow(
                """
                SELECT id FROM relationships
                WHERE status = 'active' AND (partner_a_id = $1 OR partner_b_id = $1)
                LIMIT 1
                """,
                user_id,
            )
            if not rel:
                return {}
            rel_id = rel["id"]

            goal_rows = await conn.fetch(
                """
                SELECT title, category, target_value, current_value, unit
                FROM shared_goals
                WHERE relationship_id = $1 AND status = 'active'
                ORDER BY created_at DESC
                LIMIT 5
                """,
                rel_id,
            )
            ctx_row = await conn.fetchrow(
                """
                SELECT named_recurring_conflicts, agreed_goals_and_values
                FROM shared_relationship_context
                WHERE relationship_id = $1
                """,
                rel_id,
            )
    except Exception:
        return {}

    goals = []
    for g in goal_rows:
        progress = ""
        if g["target_value"]:
            pct = round((g["current_value"] or 0) / g["target_value"] * 100)
            progress = f"{pct}%"
        goals.append({"title": g["title"], "category": g["category"], "progress": progress})

    result = {"shared_goals": goals}
    if ctx_row:
        result["recurring_conflicts"] = _clean_list(ctx_row["named_recurring_conflicts"])
        result["agreed_values"] = _clean_list(ctx_row["agreed_goals_and_values"])
    return result


async def fetch_memories(user_id: str, content: str) -> list:
    """Relevant memories from past sessions, so the counselor can remember.

    Uses the existing vector retriever over the (plaintext) memory metadata —
    never the encrypted memory content. Best-effort: no embeddings key, no DB,
    or any error yields no memories, so counseling still runs.
    """
    if not os.environ.get("DATABASE_URL") or not os.environ.get("OPENAI_API_KEY"):
        return []
    try:
        from app.memory.retriever import AccessPolicy as MemAccessPolicy
        from app.memory.retriever import SessionMemoryRetriever

        retriever = SessionMemoryRetriever(db_url=os.environ["DATABASE_URL"])
        records = await retriever.retrieve_for_session(
            user_id=user_id,
            relationship_id="",
            opening_message=content,
            access_policy=MemAccessPolicy(can_read_private=True, can_read_shared_context=False),
            top_k_private=5,
        )
    except Exception:
        return []

    memories = []
    for r in records:
        md = getattr(r, "metadata", None) or {}
        # Inject the plain-English reason/preview — never decrypt content here.
        note = md.get("why_stored") or md.get("content_preview")
        if note:
            memories.append({"memory_type": md.get("memory_type", ""), "note": note})
    return memories


def _initial_state(
    session_id: str,
    user_id: str,
    content: str,
    modifiers: Optional[dict] = None,
    memories: Optional[list] = None,
    shared_context: Optional[dict] = None,
) -> SessionState:
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
        retrieved_memories=memories or [],
        signal_vector=None,
        personalization_modifiers=modifiers or {},
        is_streaming=True,
        shared_context=shared_context or {},
    )


async def stream_counseling_turn(
    session_id: str,
    user_id: str,
    content: str,
    pool: Optional[asyncpg.Pool] = None,
) -> AsyncIterator[str]:
    """
    Run one counseling turn, emitting SSE frames as the graph progresses.

    `done` is always emitted last, including on failure, because the client
    treats it as the end-of-turn signal and will otherwise wait indefinitely.
    """
    graph = build_counseling_graph()
    modifiers = await fetch_personalization(pool, user_id)
    memories = await fetch_memories(user_id, content)
    shared_context = await fetch_shared_context(pool, user_id)
    state = _initial_state(session_id, user_id, content, modifiers, memories, shared_context)

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
        # Record the turn once it has been fully produced, so the session
        # shows up in history with an up-to-date preview.
        await persist_turn(pool, session_id, user_id, final_output)
    finally:
        yield _sse({"type": "done"})


@router.post("/api/v1/sessions/{session_id}/messages")
async def send_message(
    session_id: str = Path(...),
    request: ChatMessageRequest = Body(...),
    user_id: str = Depends(get_current_user_id),
    pool: Optional[asyncpg.Pool] = Depends(get_optional_pool),
):
    return StreamingResponse(
        stream_counseling_turn(session_id, user_id, request.content, pool=pool),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Prevent proxy buffering, which would otherwise defeat streaming.
            "X-Accel-Buffering": "no",
        },
    )
