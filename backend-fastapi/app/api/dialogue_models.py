from pydantic import BaseModel
from typing import List

class DeEscalationRequest(BaseModel):
    messages: List[str]

class DeEscalationResponse(BaseModel):
    suggestions: List[str]

class NVCReframeRequest(BaseModel):
    message: str

class NVCReframeResponse(BaseModel):
    reframed_message: str

class RepairRequest(BaseModel):
    context: str

class RepairResponse(BaseModel):
    repair_suggestion: str
