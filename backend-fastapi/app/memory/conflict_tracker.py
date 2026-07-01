"""
Conflict Pattern Tracker (REL-89)

Tracks recurring conflict themes extracted from session memories.
After >= 3 occurrences, a pattern is flagged as "named recurring conflict"
and marked for consent-gated promotion to shared context.
"""

import uuid
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ConflictPattern:
    """Represents a recurring conflict pattern for a user."""

    pattern_id: str
    user_id: str
    label: str  # Natural language, not clinical
    occurrence_count: int = 1
    first_seen_session: str = ""
    last_seen_session: str = ""
    escalation_sequence: str = ""
    successful_deescalations: list = field(default_factory=list)
    evidence_sessions: list = field(default_factory=list)
    is_recurring: bool = False  # True when occurrence_count >= 3


# ---------------------------------------------------------------------------
# Similarity helpers
# ---------------------------------------------------------------------------

RECURRING_THRESHOLD = 3
SIMILARITY_THRESHOLD = 0.85  # token-overlap similarity for MVP


def _token_overlap_similarity(label_a: str, label_b: str) -> float:
    """
    MVP similarity: Jaccard similarity of word tokens.

    Production implementation should use embedding cosine similarity (>= 0.85).
    """
    tokens_a = set(label_a.lower().split())
    tokens_b = set(label_b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# ConflictPatternTracker
# ---------------------------------------------------------------------------

# In-memory store: user_id -> list[ConflictPattern]
# Production: persist to PostgreSQL conflict_patterns table.
_conflict_store: dict[str, list[ConflictPattern]] = {}


class ConflictPatternTracker:
    """
    Analyzes extracted memories for conflict patterns and maintains
    a history of recurring conflicts per user.
    """

    def __init__(self, store: Optional[dict] = None):
        self._store = store if store is not None else _conflict_store

    def get_patterns(self, user_id: str) -> list[ConflictPattern]:
        """Return all conflict patterns for a user."""
        return self._store.get(user_id, [])

    def update_conflict_history(
        self,
        session_id: str,
        user_id: str,
        extracted_memories: list,
    ) -> list[ConflictPattern]:
        """
        Process extracted memories for conflict patterns.

        For each conflict_pattern memory:
        1. Check if an existing pattern matches (token similarity >= SIMILARITY_THRESHOLD)
        2. If match: increment occurrence_count, update last_seen_at, append session to evidence list
        3. If new: create new conflict_pattern entry
        4. If occurrence_count >= 3: flag as "named recurring conflict"

        Args:
            session_id: ID of the current session.
            user_id: ID of the user.
            extracted_memories: list of MemoryCandidate objects.

        Returns:
            Updated list of ConflictPattern for the user.
        """
        # Filter to conflict-related memories only
        conflict_memories = [
            m for m in extracted_memories
            if getattr(m, "memory_type", None) == "conflict_pattern"
        ]

        if not conflict_memories:
            return self.get_patterns(user_id)

        user_patterns = self._store.setdefault(user_id, [])

        for memory in conflict_memories:
            label = memory.content
            matched = False

            for pattern in user_patterns:
                sim = _token_overlap_similarity(label, pattern.label)
                if sim >= SIMILARITY_THRESHOLD:
                    # Update existing pattern
                    pattern.occurrence_count += 1
                    pattern.last_seen_session = session_id
                    if session_id not in pattern.evidence_sessions:
                        pattern.evidence_sessions.append(session_id)
                    if pattern.occurrence_count >= RECURRING_THRESHOLD:
                        pattern.is_recurring = True
                    matched = True
                    break

            if not matched:
                # Create new conflict pattern
                new_pattern = ConflictPattern(
                    pattern_id=str(uuid.uuid4()),
                    user_id=user_id,
                    label=label,
                    occurrence_count=1,
                    first_seen_session=session_id,
                    last_seen_session=session_id,
                    evidence_sessions=[session_id],
                )
                user_patterns.append(new_pattern)

        return user_patterns

    def clear_user_data(self, user_id: str) -> None:
        """GDPR: Remove all conflict patterns for a user."""
        self._store.pop(user_id, None)
