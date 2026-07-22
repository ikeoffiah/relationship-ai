from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth import get_current_user_id

router = APIRouter(prefix="/api/v1/sessions", tags=["feedback"])

_feedback_store: dict = {}


class FeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="1–5 star rating")
    feedback_text: str = Field(default='', max_length=200)


class FeedbackResponse(BaseModel):
    session_id: str
    rating: int
    message: str


@router.post("/{session_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    session_id: str,
    request: FeedbackRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Submit post-session feedback.
    Called from Flutter 3 seconds after session ends.
    Shown as aggregate only in clinical dashboard.
    """
    _feedback_store[session_id] = {
        "session_id": session_id,
        "user_id": user_id,
        "rating": request.rating,
        "feedback_text": request.feedback_text,
    }
    return FeedbackResponse(
        session_id=session_id,
        rating=request.rating,
        message="Thank you for your feedback.",
    )
