"""
Tone-coach endpoints backing the in-chat mood/tone assistant.

All routes require authentication and are stateless — nothing about a user's
messages or their partner's is persisted here. They exist to help one person
communicate more kindly in the moment:

* ``POST /api/v1/tone/analyze`` — read the emotional tone of a message
  (e.g. the partner's last message, for "check their mood", or the user's own).
* ``POST /api/v1/tone/coach``   — judge the user's own draft and offer kinder
  rewrites; declines (with a support pointer) if the draft carries harm signals.
* ``POST /api/v1/tone/suggest`` — auto-suggest attuned things to say next.
"""

from typing import List, Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth import get_current_user_id
from app.orchestration import tone_coach

router = APIRouter(prefix="/api/v1/tone", tags=["tone"])


class AnalyzeRequest(BaseModel):
    text: str = Field(..., max_length=4000)


class MoodResponse(BaseModel):
    mood: str
    intensity: str
    summary: str
    suggestion: str
    disclaimer: str


class CoachRequest(BaseModel):
    draft: str = Field(..., max_length=4000)
    partner_mood: Optional[str] = Field(default=None, max_length=60)


class SafetyBlock(BaseModel):
    declined: bool
    reason: str
    message: str


class CoachResponse(BaseModel):
    read: str
    tone: str
    rewrites: List[str]
    disclaimer: str
    safety: Optional[SafetyBlock] = None


class SuggestMessage(BaseModel):
    role: Literal["me", "partner"]
    content: str = Field(..., max_length=4000)


class SuggestRequest(BaseModel):
    messages: List[SuggestMessage] = Field(default_factory=list, max_length=20)


class SuggestResponse(BaseModel):
    suggestions: List[str]


@router.post("/analyze", response_model=MoodResponse)
async def analyze(
    request: AnalyzeRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Read the emotional tone of one message — a guess to build empathy, never
    a verdict (see the always-attached disclaimer)."""
    return await tone_coach.analyze_mood(request.text)


@router.post("/coach", response_model=CoachResponse)
async def coach(
    request: CoachRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Judge the caller's own draft and offer kinder rewrites."""
    return await tone_coach.coach_reply(request.draft, request.partner_mood)


@router.post("/suggest", response_model=SuggestResponse)
async def suggest(
    request: SuggestRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Auto-suggest up to 3 attuned things the caller could say next."""
    suggestions = await tone_coach.suggest_replies(
        [{"role": m.role, "content": m.content} for m in request.messages]
    )
    return SuggestResponse(suggestions=suggestions)
