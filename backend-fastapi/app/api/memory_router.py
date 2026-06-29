from uuid import uuid4
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status


# Pydantic schemas
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

    class Config:
        orm_mode = True

from ..dependencies import get_current_user

router = APIRouter()

@router.post("/", response_model=MemoryOut, status_code=status.HTTP_201_CREATED)
async def create_memory(payload: MemoryCreate, current_user=Depends(get_current_user)):
    mem_id = uuid4()
    now = datetime.utcnow()
    mem = MemoryOut(
        id=mem_id,
        user_id=current_user.id,
        content=payload.content,
        metadata=payload.metadata or {},
        created_at=now,
        updated_at=now,
    )
    _memory_store[mem_id] = mem
    return mem

_memory_store: dict[UUID, MemoryOut] = {}

@router.get("/", response_model=List[MemoryOut])
async def list_memories(limit: int = 20, offset: int = 0, type: Optional[str] = None, current_user=Depends(get_current_user)):
    # Filter by user_id and optional type (metadata['type'])
    results = [m for m in _memory_store.values() if m.user_id == current_user.id]
    if type:
        results = [m for m in results if m.metadata.get('type') == type]
    return results[offset : offset + limit]

@router.get("/{memory_id}", response_model=MemoryOut)
async def get_memory(memory_id: UUID, current_user=Depends(get_current_user)):
    mem = _memory_store.get(memory_id)
    if not mem or mem.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return mem

@router.put("/{memory_id}", response_model=MemoryOut)
async def update_memory(memory_id: UUID, payload: MemoryUpdate, current_user=Depends(get_current_user)):
    mem = _memory_store.get(memory_id)
    if not mem or mem.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    updated = mem.copy(update=payload.dict(exclude_unset=True))
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
