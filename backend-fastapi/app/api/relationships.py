import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
import asyncpg

router = APIRouter(prefix="/api/v1/relationships", tags=["relationships"])


# Dependency to get DB pool
async def get_db_pool() -> asyncpg.Pool:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL is not set")
    # In a real app, this should be a long-lived app.state.pool
    # Reusing create_pool for simplicity if not in app.state
    pool = await asyncpg.create_pool(db_url)
    try:
        yield pool
    finally:
        await pool.close()


# Mock Encryption/Decryption
def encrypt_context(data: Any, relationship_id: str) -> str:
    # MVP: just dump to string. In prod, use cryptography.fernet or AES with derived key.
    return json.dumps(data)


def decrypt_context(data_str: str, relationship_id: str) -> Any:
    # MVP: just load from string.
    try:
        return json.loads(data_str)
    except Exception:
        return {}


# Dependency to extract User Context (mocking authentication)
async def get_current_user_id(request: Request) -> str:
    # In a real app, we'd verify the JWT
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User-ID header required")
    return user_id


# --- API Models ---

class ConflictPayload(BaseModel):
    conflict_id: str
    label: str
    description: str
    acknowledged_by_both: bool

class GoalPayload(BaseModel):
    goal_id: str
    description: str

class RepairPayload(BaseModel):
    event_id: str
    description: str
    session_id: str

class StructuralPayload(BaseModel):
    relationship_duration_months: int
    cohabiting: bool
    children: int
    cultural_backgrounds: List[str]
    religious_values: List[str]


# --- Consent Gate ---
async def check_shared_context_consent(pool: asyncpg.Pool, relationship_id: str, user_id: str, require_write: bool = False):
    """
    Checks that both partners have consented to shared_relationship_context.
    If require_write is True, both must be 'read_write'.
    If require_write is False, both must be at least 'read_only' (but if one is read_only, the other is downgraded).
    """
    async with pool.acquire() as conn:
        # Get both partners of the relationship
        rel = await conn.fetchrow(
            "SELECT partner_a_id, partner_b_id FROM relationships WHERE id = $1 AND status = 'active'", 
            relationship_id
        )
        if not rel:
            raise HTTPException(status_code=404, detail="Active relationship not found")
            
        partner_a = rel["partner_a_id"]
        partner_b = rel["partner_b_id"]

        if not partner_b:
            raise HTTPException(status_code=403, detail="Relationship not fully formed")

        # Get consent for both partners
        consents = await conn.fetch(
            "SELECT user_id, shared_relationship_context FROM consent_userconsent WHERE user_id IN ($1, $2)",
            partner_a, partner_b
        )

        consent_map = {str(c["user_id"]): c["shared_relationship_context"] for c in consents}
        consent_a = consent_map.get(str(partner_a), "not_participating")
        consent_b = consent_map.get(str(partner_b), "not_participating")

        if consent_a == "not_participating" or consent_b == "not_participating":
            raise HTTPException(status_code=403, detail="Shared context access denied by consent gate")

        if require_write:
            if consent_a != "read_write" or consent_b != "read_write":
                raise HTTPException(status_code=403, detail="Bilateral read_write consent required for writes")


# --- Endpoints ---

@router.get("/{relationship_id}/context")
async def get_shared_context(relationship_id: str, pool: asyncpg.Pool = Depends(get_db_pool), user_id: str = Depends(get_current_user_id)):
    await check_shared_context_consent(pool, relationship_id, user_id, require_write=False)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM shared_relationship_context WHERE relationship_id = $1", 
            relationship_id
        )
        if not row:
            return {
                "named_recurring_conflicts": [],
                "agreed_goals_and_values": [],
                "repair_history": [],
                "structural_facts": {}
            }

        return {
            "named_recurring_conflicts": decrypt_context(row["named_recurring_conflicts"], relationship_id),
            "agreed_goals_and_values": decrypt_context(row["agreed_goals_and_values"], relationship_id),
            "repair_history": decrypt_context(row["repair_history"], relationship_id),
            "structural_facts": decrypt_context(row["structural_facts"], relationship_id)
        }


@router.put("/{relationship_id}/context/conflicts")
async def update_conflict(relationship_id: str, payload: ConflictPayload, pool: asyncpg.Pool = Depends(get_db_pool), user_id: str = Depends(get_current_user_id)):
    await check_shared_context_consent(pool, relationship_id, user_id, require_write=True)

    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT named_recurring_conflicts FROM shared_relationship_context WHERE relationship_id = $1", relationship_id)
        
        conflicts = decrypt_context(row["named_recurring_conflicts"], relationship_id) if row else []
        
        # Update or add
        existing = next((c for c in conflicts if c["conflict_id"] == payload.conflict_id), None)
        if existing:
            existing.update(payload.dict())
        else:
            new_conflict = payload.dict()
            new_conflict["created_at"] = datetime.utcnow().isoformat()
            conflicts.append(new_conflict)

        encrypted = encrypt_context(conflicts, relationship_id)
        
        if row:
            await conn.execute("UPDATE shared_relationship_context SET named_recurring_conflicts = $1, updated_at = NOW() WHERE relationship_id = $2", encrypted, relationship_id)
        else:
            await conn.execute(
                "INSERT INTO shared_relationship_context (relationship_id, named_recurring_conflicts, agreed_goals_and_values, repair_history, structural_facts, created_at, updated_at) VALUES ($1, $2, '[]', '[]', '{}', NOW(), NOW())",
                relationship_id, encrypted
            )

        # Update Vector Store representation
        from app.memory.vector_store import VectorMemoryStore
        vs = VectorMemoryStore(os.environ.get("DATABASE_URL"))
        await vs.upsert(
            user_id=user_id,
            memory_id=f"conflict_{payload.conflict_id}",
            text=f"Conflict: {payload.label} - {payload.description}",
            metadata={"type": "conflict", "relationship_id": relationship_id},
            zone=f"shared_{relationship_id}"
        )
            
    return {"status": "success"}


@router.put("/{relationship_id}/context/goals")
async def update_goal(relationship_id: str, payload: GoalPayload, pool: asyncpg.Pool = Depends(get_db_pool), user_id: str = Depends(get_current_user_id)):
    await check_shared_context_consent(pool, relationship_id, user_id, require_write=True)

    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT agreed_goals_and_values FROM shared_relationship_context WHERE relationship_id = $1", relationship_id)
        
        goals = decrypt_context(row["agreed_goals_and_values"], relationship_id) if row else []
        
        # Update or add
        existing = next((g for g in goals if g["goal_id"] == payload.goal_id), None)
        if existing:
            existing.update(payload.dict())
        else:
            new_goal = payload.dict()
            new_goal["added_by"] = user_id
            new_goal["created_at"] = datetime.utcnow().isoformat()
            goals.append(new_goal)

        encrypted = encrypt_context(goals, relationship_id)
        
        if row:
            await conn.execute("UPDATE shared_relationship_context SET agreed_goals_and_values = $1, updated_at = NOW() WHERE relationship_id = $2", encrypted, relationship_id)
        else:
            await conn.execute(
                "INSERT INTO shared_relationship_context (relationship_id, named_recurring_conflicts, agreed_goals_and_values, repair_history, structural_facts, created_at, updated_at) VALUES ($1, '[]', $2, '[]', '{}', NOW(), NOW())",
                relationship_id, encrypted
            )

        # Update Vector Store representation
        from app.memory.vector_store import VectorMemoryStore
        vs = VectorMemoryStore(os.environ.get("DATABASE_URL"))
        await vs.upsert(
            user_id=user_id,
            memory_id=f"goal_{payload.goal_id}",
            text=f"Shared Goal: {payload.description}",
            metadata={"type": "goal", "relationship_id": relationship_id},
            zone=f"shared_{relationship_id}"
        )

    return {"status": "success"}


@router.put("/{relationship_id}/context/repairs")
async def update_repair(relationship_id: str, payload: RepairPayload, pool: asyncpg.Pool = Depends(get_db_pool), user_id: str = Depends(get_current_user_id)):
    await check_shared_context_consent(pool, relationship_id, user_id, require_write=True)

    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT repair_history FROM shared_relationship_context WHERE relationship_id = $1", relationship_id)
        
        repairs = decrypt_context(row["repair_history"], relationship_id) if row else []
        
        new_repair = payload.dict()
        new_repair["added_by"] = user_id
        new_repair["timestamp"] = datetime.utcnow().isoformat()
        repairs.append(new_repair)

        encrypted = encrypt_context(repairs, relationship_id)
        
        if row:
            await conn.execute("UPDATE shared_relationship_context SET repair_history = $1, updated_at = NOW() WHERE relationship_id = $2", encrypted, relationship_id)
        else:
            await conn.execute(
                "INSERT INTO shared_relationship_context (relationship_id, named_recurring_conflicts, agreed_goals_and_values, repair_history, structural_facts, created_at, updated_at) VALUES ($1, '[]', '[]', $2, '{}', NOW(), NOW())",
                relationship_id, encrypted
            )

        # Update Vector Store representation
        from app.memory.vector_store import VectorMemoryStore
        vs = VectorMemoryStore(os.environ.get("DATABASE_URL"))
        await vs.upsert(
            user_id=user_id,
            memory_id=f"repair_{payload.event_id}",
            text=f"Repair Event: {payload.description}",
            metadata={"type": "repair", "relationship_id": relationship_id, "session_id": payload.session_id},
            zone=f"shared_{relationship_id}"
        )

    return {"status": "success"}


@router.put("/{relationship_id}/context/structural")
async def update_structural(relationship_id: str, payload: StructuralPayload, pool: asyncpg.Pool = Depends(get_db_pool), user_id: str = Depends(get_current_user_id)):
    await check_shared_context_consent(pool, relationship_id, user_id, require_write=True)

    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT structural_facts FROM shared_relationship_context WHERE relationship_id = $1", relationship_id)
        
        encrypted = encrypt_context(payload.dict(), relationship_id)
        
        if row:
            await conn.execute("UPDATE shared_relationship_context SET structural_facts = $1, updated_at = NOW() WHERE relationship_id = $2", encrypted, relationship_id)
        else:
            await conn.execute(
                "INSERT INTO shared_relationship_context (relationship_id, named_recurring_conflicts, agreed_goals_and_values, repair_history, structural_facts, created_at, updated_at) VALUES ($1, '[]', '[]', '[]', $2, NOW(), NOW())",
                relationship_id, encrypted
            )

    return {"status": "success"}
