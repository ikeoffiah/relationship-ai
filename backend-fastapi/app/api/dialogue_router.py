from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID

from .dialogue_models import DeEscalationRequest, DeEscalationResponse, NVCReframeRequest, NVCReframeResponse, RepairRequest, RepairResponse
from ..dependencies import get_current_user  # placeholder, adjust import as needed
from app.dialogue.tasks.dialogue_tasks import deescalate_task, nvc_reframe_task, repair_task

router = APIRouter(prefix="/dialogue", tags=["Dialogue Management"])

@router.post("/deescalate", response_model=DeEscalationResponse)
async def deescalate(request: DeEscalationRequest, current_user=Depends(get_current_user)):
    # Call async Celery task (simulated with await for now)
    result = await deescalate_task(request.messages, user_id=current_user.id)
    return DeEscalationResponse(suggestions=result)

@router.post("/nvc_reframe", response_model=NVCReframeResponse)
async def nvc_reframe(request: NVCReframeRequest, current_user=Depends(get_current_user)):
    result = await nvc_reframe_task(request.message, user_id=current_user.id)
    return NVCReframeResponse(reframed_message=result)

@router.post("/repair", response_model=RepairResponse)
async def repair(request: RepairRequest, current_user=Depends(get_current_user)):
    result = await repair_task(request.context, user_id=current_user.id)
    return RepairResponse(repair_suggestion=result)
