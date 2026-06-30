"""
Memory Extraction Pipeline (REL-89)

After every session, MemoryUpdateTask calls POST /internal/extract-memories
which runs this pipeline. Uses Claude claude-haiku-4-5-20251001 (fast, cost-effective)
with a structured extraction prompt.
"""

import json
import os
from typing import Literal, Optional

from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field

from app.orchestration.model_config import MODEL_CONFIG


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

MemoryTypeStr = Literal[
    "communication_style",
    "trigger",
    "conflict_pattern",
    "repair_event",
    "stated_need",
]


class MemoryCandidate(BaseModel):
    """A single memory candidate extracted from a session."""

    content: str = Field(..., description="Memory in 1-2 sentences")
    memory_type: MemoryTypeStr
    confidence: float = Field(..., ge=0.0, le=1.0)
    why_stored: str = Field(..., description="Plain-English reason this matters")
    session_evidence: str = Field(
        ..., description="Quote/reference from session (max 20 words)"
    )

    @property
    def content_preview(self) -> str:
        """First 50 chars of content for dashboard display (plaintext, unencrypted)."""
        return self.content[:50]


# ---------------------------------------------------------------------------
# Extraction prompt
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = """From the session conversation below, extract the following types of memory:
1. Communication patterns: How does this person communicate? Characteristic phrases or styles?
2. Emotional triggers: What topics or situations caused distress? What phrases escalated tension?
3. Conflict patterns: What recurring conflict themes are visible? What de-escalation worked?
4. Positive signals: What moments of connection, repair, or growth occurred?
5. Stated needs: What explicit needs did the user express?

For each extracted memory, provide:
- content: the memory in 1-2 sentences
- memory_type: communication_style | trigger | conflict_pattern | repair_event | stated_need
- confidence: 0.0-1.0
- why_stored: one plain-English sentence explaining why this matters
- session_evidence: quote or reference from session that supports this (max 20 words)

RULES:
- Only extract from this session. Do not infer history.
- Confidence < 0.5: do not include (not worth storing)
- Never store opinions about the partner as facts
- Phrase everything from the user's perspective ("user expresses...", "user responds to...")

Respond ONLY with a JSON array. No preamble.

SESSION CONVERSATION:
{conversation}
"""


# ---------------------------------------------------------------------------
# MemoryExtractor
# ---------------------------------------------------------------------------

CONFIDENCE_THRESHOLD = 0.5
HIGH_CONFIDENCE_THRESHOLD = 0.7


class MemoryExtractor:
    """
    Extracts structured memories from a session using Claude Haiku.

    Upsert logic (applied per memory_type):
    - If a memory of the same memory_type exists with confidence >= 0.7: update (don't duplicate)
    - If a new memory type or new topic: insert
    """

    def __init__(self, anthropic_client: Optional[AsyncAnthropic] = None):
        self._client = anthropic_client or AsyncAnthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )
        self._model = MODEL_CONFIG["memory_extraction"]["model_id"]

    def _format_conversation(self, session_messages: list[dict]) -> str:
        """Format session messages into a readable conversation string."""
        lines = []
        for msg in session_messages:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    async def extract(
        self,
        session_messages: list[dict],
        user_id: str,
    ) -> list[MemoryCandidate]:
        """
        Extract memory candidates from session messages.

        Args:
            session_messages: List of {"role": str, "content": str} dicts
            user_id: Used for context only (not stored in candidates)

        Returns:
            List of MemoryCandidate with confidence >= CONFIDENCE_THRESHOLD.
            Caller is responsible for persisting via VectorMemoryStore.
        """
        if not session_messages:
            return []

        conversation = self._format_conversation(session_messages)
        prompt = EXTRACTION_PROMPT.format(conversation=conversation)

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_text = response.content[0].text.strip()

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        try:
            raw_candidates = json.loads(raw_text)
        except (json.JSONDecodeError, ValueError):
            # If Claude returns malformed JSON, log and return empty
            return []

        candidates = []
        for item in raw_candidates:
            try:
                candidate = MemoryCandidate(**item)
                if candidate.confidence >= CONFIDENCE_THRESHOLD:
                    candidates.append(candidate)
            except Exception:
                # Skip malformed candidates
                continue

        return candidates
