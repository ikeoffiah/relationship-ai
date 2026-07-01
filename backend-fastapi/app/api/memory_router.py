import os
from uuid import uuid4
from typing import List, Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status


# ---------------------------------------------------------------------------
# Memory type enum (REL-89)
# ---------------------------------------------------------------------------

MemoryTypeStr = Literal[
    "communication_style",
    "trigger",
    "conflict_pattern",
    "repair_event",
    "stated_need",
]


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class MemoryBase(BaseModel):
    content: str = Field(..., description="Memory content text")
    metadata: Optional[dict] = Field(default_factory=dict, description="Arbitrary metadata")


class MemoryCreate(MemoryBase):
    pass


class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    metadata: Optional[dict] = None


class MemoryOut(MemoryBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    # REL-89: memory lifecycle fields
    memory_type: Optional[MemoryTypeStr] = Field(
        None, description="Structured memory type for display and filtering"
    )
    content_preview: Optional[str] = Field(
        None, description="First 50 chars of content (plaintext) for dashboard display"
    )

    class Config:
        orm_mode = True


# ---------------------------------------------------------------------------
# Internal extract-memories request/response schemas (REL-89)
# ---------------------------------------------------------------------------

class ExtractionRequest(BaseModel):
    session_id: str = Field(..., description="Session ID to extract memories from")
    user_id: str = Field(..., description="User whose memories to update")
    messages: List[dict] = Field(..., description="Session messages as list of {role, content}")


class ExtractionResponse(BaseModel):
    extracted_count: int
    conflict_patterns_updated: int
    trigger_inventory_size: int


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

from ..dependencies import get_current_user

router = APIRouter()

_memory_store: dict[UUID, MemoryOut] = {}


@router.post("/", response_model=MemoryOut, status_code=status.HTTP_201_CREATED)
async def create_memory(payload: MemoryCreate, current_user=Depends(get_current_user)):
    mem_id = uuid4()
    now = datetime.utcnow()
    content_preview = payload.content[:50] if payload.content else None
    mem = MemoryOut(
        id=mem_id,
        user_id=current_user.id,
        content=payload.content,
        metadata=payload.metadata or {},
        created_at=now,
        updated_at=now,
        memory_type=payload.metadata.get("memory_type") if payload.metadata else None,
        content_preview=content_preview,
    )
    _memory_store[mem_id] = mem
    return mem


@router.get("/", response_model=List[MemoryOut])
async def list_memories(
    limit: int = 20,
    offset: int = 0,
    type: Optional[str] = None,
    current_user=Depends(get_current_user),
):
    # Filter by user_id and optional type (memory_type or metadata['type'])
    results = [m for m in _memory_store.values() if m.user_id == current_user.id]
    if type:
        results = [
            m for m in results
            if m.memory_type == type or (m.metadata and m.metadata.get("type") == type)
        ]
    return results[offset: offset + limit]


@router.get("/{memory_id}", response_model=MemoryOut)
async def get_memory(memory_id: UUID, current_user=Depends(get_current_user)):
    mem = _memory_store.get(memory_id)
    if not mem or mem.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return mem


@router.put("/{memory_id}", response_model=MemoryOut)
async def update_memory(
    memory_id: UUID,
    payload: MemoryUpdate,
    current_user=Depends(get_current_user),
):
    mem = _memory_store.get(memory_id)
    if not mem or mem.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    update_data = payload.dict(exclude_unset=True)
    # Recompute preview if content changes
    if "content" in update_data and update_data["content"]:
        update_data["content_preview"] = update_data["content"][:50]
    updated = mem.copy(update=update_data)
    updated.updated_at = datetime.utcnow()
    _memory_store[memory_id] = updated
    return updated


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(memory_id: UUID, current_user=Depends(get_current_user)):
    mem = _memory_store.get(memory_id)
    if not mem or mem.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    del _memory_store[memory_id]
    return


class BulkDeleteRequest(BaseModel):
    memory_ids: List[UUID]


@router.post("/bulk-delete/", status_code=status.HTTP_202_ACCEPTED)
async def bulk_delete(request: BulkDeleteRequest, current_user=Depends(get_current_user)):
    # In production, enqueue a Celery job. Here we simulate immediate processing.
    deleted = []
    for mid in request.memory_ids:
        mem = _memory_store.get(mid)
        if mem and mem.user_id == current_user.id:
            del _memory_store[mid]
            deleted.append(mid)
    return {"deleted": deleted, "requested": len(request.memory_ids)}


@router.get("/count/", response_model=int)
async def count_memories(current_user=Depends(get_current_user)):
    return sum(1 for m in _memory_store.values() if m.user_id == current_user.id)


# ---------------------------------------------------------------------------
# Internal endpoint: POST /internal/extract-memories (REL-89)
# ---------------------------------------------------------------------------

@router.post(
    "/internal/extract-memories",
    response_model=ExtractionResponse,
    tags=["internal"],
    summary="Post-session memory extraction pipeline",
    description=(
        "Called by MemoryUpdateTask (Celery) after each session. "
        "Runs MemoryExtractor, ConflictPatternTracker, and TriggerInventoryBuilder."
    ),
)
async def extract_memories(payload: ExtractionRequest):
    """
    Async post-session memory extraction pipeline.

    1. Calls MemoryExtractor (Claude Haiku) to extract MemoryCandidates
    2. Upserts candidates into VectorMemoryStore
    3. Updates ConflictPatternTracker
    4. Updates TriggerInventoryBuilder

    Note: Anthropic API key required for real extraction.
    In test/staging environments, mock the MemoryExtractor.
    """
    from app.memory.extractor import MemoryExtractor
    from app.memory.conflict_tracker import ConflictPatternTracker
    from app.memory.trigger_builder import TriggerInventoryBuilder

    db_url = os.environ.get("DATABASE_URL", "")

    # Skip vector store calls if using test/mock DB
    is_test_db = not db_url or "mock" in db_url or "test" in db_url

    # --- Step 1: Extract memories ---
    extractor = MemoryExtractor()
    candidates = await extractor.extract(
        session_messages=payload.messages,
        user_id=payload.user_id,
    )

    # --- Step 2: Upsert into vector store (skip in test mode) ---
    if not is_test_db and candidates:
        from app.memory.vector_store import VectorMemoryStore
        from datetime import timezone

        store = VectorMemoryStore(db_url=db_url)
        for candidate in candidates:
            memory_id = f"{payload.user_id}:{candidate.memory_type}"  # type-scoped ID for upsert
            await store.upsert(
                user_id=payload.user_id,
                memory_id=memory_id,
                text=candidate.content,
                metadata={
                    "memory_type": candidate.memory_type,
                    "why_stored": candidate.why_stored,
                    "confidence": candidate.confidence,
                    "session_evidence": candidate.session_evidence,
                    "content_preview": candidate.content_preview,
                    "stored_at": datetime.now(tz=timezone.utc).isoformat(),
                    "session_id": payload.session_id,
                },
                zone="private",
            )

    # --- Step 3: Update conflict pattern history ---
    conflict_tracker = ConflictPatternTracker()
    updated_patterns = conflict_tracker.update_conflict_history(
        session_id=payload.session_id,
        user_id=payload.user_id,
        extracted_memories=candidates,
    )

    # --- Step 4: Update trigger inventory ---
    trigger_builder = TriggerInventoryBuilder()
    updated_triggers = trigger_builder.update_triggers(
        session_messages=payload.messages,
        user_id=payload.user_id,
        session_id=payload.session_id,
    )

    return ExtractionResponse(
        extracted_count=len(candidates),
        conflict_patterns_updated=len(updated_patterns),
        trigger_inventory_size=len(updated_triggers),
    )
