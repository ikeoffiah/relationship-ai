"""
Asynchronous partner relay (REL-88).

Messages are persisted in the `relay_messages` table (owned by the Django
`relationships` app) rather than in process memory, so relays survive a
restart and are visible across every worker.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import uuid4

import asyncpg
from fastapi import APIRouter, Body, Depends, HTTPException, Path
from pydantic import BaseModel, Field

from app.api.relationships import get_current_user_id, get_db_pool

router = APIRouter()

RELAY_TTL_DAYS = 7
QUALITY_THRESHOLD = 0.6


class RelayCreateRequest(BaseModel):
    content: str = Field(..., description="Original message content")
    consent_to_relay: bool = Field(..., description="User explicit consent to relay")


class RelayDeliverRequest(BaseModel):
    recipient_chose_version: str = Field(..., description="'ai_translated' or 'original'")


class RelayResponse(BaseModel):
    relay_id: str
    status: str


class RelayDetail(BaseModel):
    relay_id: str
    from_user_id: str
    to_user_id: str
    relationship_id: str
    original_content: str
    translated_content: Optional[str] = None
    translation_quality_score: float
    status: str
    created_at: datetime
    delivered_at: Optional[datetime] = None
    recipient_chose_version: Optional[str] = None
    expires_at: datetime


def mock_nvc_translate(content: str) -> tuple[str, float]:
    if "low_quality" in content.lower():
        return "Failed NVC structure rephrase", 0.4
    translated = (
        f"Observation: User shared: '{content}'. Feeling: Valued. "
        "Need: Safety and connection. Request: Let's discuss this together."
    )
    return translated, 0.85


def _row_to_detail(row) -> RelayDetail:
    return RelayDetail(
        relay_id=str(row["relay_id"]),
        from_user_id=str(row["from_user_id"]),
        to_user_id=str(row["to_user_id"]),
        relationship_id=str(row["relationship_id"]),
        original_content=row["original_content"],
        translated_content=row["translated_content"] or None,
        translation_quality_score=row["translation_quality_score"],
        status=row["status"],
        created_at=row["created_at"],
        delivered_at=row["delivered_at"],
        recipient_chose_version=row["recipient_chose_version"],
        expires_at=row["expires_at"],
    )


async def _resolve_partner(conn, user_id: str) -> tuple[str, str]:
    """Return (relationship_id, partner_id) for the caller's active relationship."""
    row = await conn.fetchrow(
        """
        SELECT id, partner_a_id, partner_b_id
        FROM relationships
        WHERE status = 'active' AND (partner_a_id = $1 OR partner_b_id = $1)
        """,
        user_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="No active relationship found")

    partner_id = (
        row["partner_b_id"] if str(row["partner_a_id"]) == str(user_id) else row["partner_a_id"]
    )
    if not partner_id:
        raise HTTPException(status_code=400, detail="Relationship has no partner yet")
    return str(row["id"]), str(partner_id)


@router.post("/api/v1/sessions/{session_id}/relay", response_model=RelayResponse)
async def send_relay(
    session_id: str = Path(...),
    request: RelayCreateRequest = Body(...),
    pool: asyncpg.Pool = Depends(get_db_pool),
    user_id: str = Depends(get_current_user_id),
):
    if not request.consent_to_relay:
        raise HTTPException(status_code=400, detail="Consent to relay is required")

    translated, score = mock_nvc_translate(request.content)
    status = "ready" if score >= QUALITY_THRESHOLD else "quality_review"

    relay_id = str(uuid4())
    created_at = datetime.now(timezone.utc)
    expires_at = created_at + timedelta(days=RELAY_TTL_DAYS)

    async with pool.acquire() as conn:
        relationship_id, to_user_id = await _resolve_partner(conn, user_id)
        await conn.execute(
            """
            INSERT INTO relay_messages (
                relay_id, relationship_id, from_user_id, to_user_id,
                original_content, translated_content, translation_quality_score,
                status, recipient_chose_version, created_at, delivered_at, expires_at
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,NULL,$9,NULL,$10)
            """,
            relay_id, relationship_id, user_id, to_user_id,
            request.content, translated, score, status, created_at, expires_at,
        )

    return RelayResponse(
        relay_id=relay_id,
        status="processing" if status == "quality_review" else status,
    )


@router.get("/api/v1/users/{user_id}/relay/pending", response_model=List[RelayDetail])
async def get_pending_relays(
    user_id: str = Path(...),
    pool: asyncpg.Pool = Depends(get_db_pool),
    caller_id: str = Depends(get_current_user_id),
):
    if str(caller_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Cannot read another user's relay inbox")

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM relay_messages
            WHERE to_user_id = $1 AND status = 'ready' AND expires_at > NOW()
            ORDER BY created_at
            """,
            user_id,
        )
    return [_row_to_detail(r) for r in rows]


@router.post("/api/v1/relay/{relay_id}/deliver", response_model=RelayDetail)
async def deliver_relay(
    relay_id: str = Path(...),
    request: RelayDeliverRequest = Body(...),
    pool: asyncpg.Pool = Depends(get_db_pool),
    user_id: str = Depends(get_current_user_id),
):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM relay_messages WHERE relay_id = $1", relay_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Relay message not found")
        if str(row["to_user_id"]) != str(user_id):
            raise HTTPException(status_code=403, detail="Only the recipient may take delivery")
        if row["expires_at"] <= datetime.now(timezone.utc):
            await conn.execute(
                "UPDATE relay_messages SET status = 'expired' WHERE relay_id = $1", relay_id
            )
            raise HTTPException(status_code=400, detail="Relay message has expired")
        if row["status"] != "ready":
            raise HTTPException(
                status_code=400, detail="Relay message is not ready for delivery"
            )

        updated = await conn.fetchrow(
            """
            UPDATE relay_messages
            SET status = 'delivered', delivered_at = $2, recipient_chose_version = $3
            WHERE relay_id = $1
            RETURNING *
            """,
            relay_id, datetime.now(timezone.utc), request.recipient_chose_version,
        )

    return _row_to_detail(updated)


@router.delete("/api/v1/relay/{relay_id}")
async def withdraw_relay(
    relay_id: str = Path(...),
    pool: asyncpg.Pool = Depends(get_db_pool),
    user_id: str = Depends(get_current_user_id),
):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT from_user_id, status FROM relay_messages WHERE relay_id = $1", relay_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Relay message not found")
        if str(row["from_user_id"]) != str(user_id):
            raise HTTPException(status_code=403, detail="Only the sender may withdraw")
        if row["status"] == "delivered":
            raise HTTPException(
                status_code=400,
                detail="Cannot withdraw a message that has already been delivered",
            )
        await conn.execute(
            "UPDATE relay_messages SET status = 'withdrawn' WHERE relay_id = $1", relay_id
        )

    return {"status": "withdrawn"}
