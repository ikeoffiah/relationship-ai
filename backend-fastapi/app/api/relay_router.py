from fastapi import APIRouter, HTTPException, Depends, Path
from pydantic import BaseModel, Field
from typing import List, Dict
from uuid import uuid4

router = APIRouter()

# In‑memory store for demo purposes – replace with DB models in production
_relay_store: Dict[str, List[Dict]] = {}

class RelayMessage(BaseModel):
    content: str = Field(..., description="Message text")
    attachments: List[str] = Field(default_factory=list, description="Attachment URLs")

class RelayPreviewResponse(BaseModel):
    preview_html: str

def get_user_store(user_id: str) -> List[Dict]:
    return _relay_store.setdefault(user_id, [])

@router.post("/api/v1/sessions/{session_id}/relay/preview", response_model=RelayPreviewResponse)
async def preview_relay(session_id: str = Path(...), message: RelayMessage = Depends()):
    html = f"<div class='relay-preview'><p>{message.content}</p></div>"
    return RelayPreviewResponse(preview_html=html)

@router.post("/api/v1/sessions/{session_id}/relay")
async def send_relay(session_id: str = Path(...), message: RelayMessage = Depends()):
    user_id = session_id  # placeholder mapping
    store = get_user_store(user_id)
    relay_id = str(uuid4())
    store.append({"id": relay_id, "session_id": session_id, "content": message.content, "attachments": message.attachments, "read": False})
    return {"relay_id": relay_id, "status": "sent"}

@router.get("/api/v1/users/{user_id}/relay/inbox", response_model=List[Dict])
async def get_inbox(user_id: str = Path(...)):
    return [msg for msg in get_user_store(user_id) if not msg.get("read", False)]

@router.get("/api/v1/users/{user_id}/relay/sent", response_model=List[Dict])
async def get_sent(user_id: str = Path(...)):
    return get_user_store(user_id)

@router.post("/api/v1/sessions/{session_id}/relay/{relay_id}/read")
async def mark_relay_read(session_id: str = Path(...), relay_id: str = Path(...)):
    for store in _relay_store.values():
        for msg in store:
            if msg.get("id") == relay_id and msg.get("session_id") == session_id:
                msg["read"] = True
                return {"status": "marked as read"}
    raise HTTPException(status_code=404, detail="Relay message not found")
