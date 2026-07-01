from fastapi import APIRouter, HTTPException, Depends, Path, Body
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from uuid import uuid4
from datetime import datetime, timedelta

router = APIRouter()

# In‑memory store for demo purposes
# relay_id -> Dict
_relay_store: Dict[str, Dict] = {}

# Audit trail log (list of string event logs)
_audit_trail: List[str] = []

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
    translated = f"Observation: User shared: '{content}'. Feeling: Valued. Need: Safety and connection. Request: Let's discuss this together."
    return translated, 0.85

@router.post("/api/v1/sessions/{session_id}/relay", response_model=RelayResponse)
async def send_relay(session_id: str = Path(...), request: RelayCreateRequest = Body(...)):
    if not request.consent_to_relay:
        raise HTTPException(status_code=400, detail="Consent to relay is required")
        
    relay_id = str(uuid4())
    
    # Run mock translation and quality check
    translated, score = mock_nvc_translate(request.content)
    
    # Determine status based on quality score
    status = "ready" if score >= 0.6 else "quality_review"
    
    # Store record
    created_at = datetime.utcnow()
    expires_at = created_at + timedelta(days=7)
    
    # Encrypt simulations: we just store them (simulating encryption)
    _relay_store[relay_id] = {
        "relay_id": relay_id,
        "from_user_id": "user-A",  # Mock user mapping
        "to_user_id": "user-B",
        "relationship_id": session_id,
        "original_content": request.content,
        "translated_content": translated,
        "translation_quality_score": score,
        "status": status,
        "created_at": created_at,
        "delivered_at": None,
        "recipient_chose_version": None,
        "expires_at": expires_at
    }
    
    _audit_trail.append(f"[{datetime.utcnow().isoformat()}] Relay message {relay_id} created with status {status}")
    
    return RelayResponse(relay_id=relay_id, status="processing" if status == "quality_review" else status)

@router.get("/api/v1/users/{user_id}/relay/pending", response_model=List[RelayDetail])
async def get_pending_relays(user_id: str = Path(...)):
    now = datetime.utcnow()
    pending = []
    
    for relay_id, msg in _relay_store.items():
        # Clean up / skip expired messages
        if msg["expires_at"] < now:
            msg["status"] = "expired"
            continue
            
        if msg["to_user_id"] == user_id and msg["status"] in ["ready", "processing"]:
            # Note: quality_review messages are held and NOT delivered
            if msg["status"] == "ready":
                pending.append(RelayDetail(**msg))
                
    return pending

@router.post("/api/v1/relay/{relay_id}/deliver", response_model=RelayDetail)
async def deliver_relay(relay_id: str = Path(...), request: RelayDeliverRequest = Body(...)):
    if relay_id not in _relay_store:
        raise HTTPException(status_code=404, detail="Relay message not found")
        
    msg = _relay_store[relay_id]
    
    if msg["expires_at"] < datetime.utcnow():
        msg["status"] = "expired"
        raise HTTPException(status_code=400, detail="Relay message has expired")
        
    if msg["status"] != "ready":
        raise HTTPException(status_code=400, detail="Relay message is not ready for delivery")
        
    msg["status"] = "delivered"
    msg["delivered_at"] = datetime.utcnow()
    msg["recipient_chose_version"] = request.recipient_chose_version
    
    # Audit log (WITHOUT content)
    _audit_trail.append(
        f"[{datetime.utcnow().isoformat()}] Relay message {relay_id} delivered. Recipient chose: {request.recipient_chose_version}"
    )
    
    return RelayDetail(**msg)

@router.delete("/api/v1/relay/{relay_id}")
async def withdraw_relay(relay_id: str = Path(...)):
    if relay_id not in _relay_store:
        raise HTTPException(status_code=404, detail="Relay message not found")
        
    msg = _relay_store[relay_id]
    
    if msg["status"] == "delivered":
        raise HTTPException(status_code=400, detail="Cannot withdraw a message that has already been delivered")
        
    msg["status"] = "withdrawn"
    
    _audit_trail.append(f"[{datetime.utcnow().isoformat()}] Relay message {relay_id} withdrawn by sender")
    
    return {"status": "withdrawn"}
