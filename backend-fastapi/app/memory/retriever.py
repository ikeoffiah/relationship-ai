"""
Session Memory Retriever (REL-89)

Vector-search-based retrieval at session start.
Wraps VectorMemoryStore with recency weighting.
Target: < 40ms p50.
"""

from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from typing import Optional

from app.memory.vector_store import VectorMemoryStore, MemoryRecord


# ---------------------------------------------------------------------------
# Access Policy
# ---------------------------------------------------------------------------

@dataclass
class AccessPolicy:
    """Controls which memory namespaces the retriever may query."""

    can_read_private: bool = True
    can_read_shared_context: bool = False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RECENCY_WINDOW_DAYS = 30
RECENCY_BOOST = 0.20   # 20% score boost for memories from last 30 days


def _apply_recency_boost(record: MemoryRecord) -> float:
    """
    Return adjusted similarity score with recency boost applied.

    Boosts memories stored within RECENCY_WINDOW_DAYS by RECENCY_BOOST.
    Falls back to original score if `stored_at` metadata is missing/malformed.
    """
    stored_at_str = record.metadata.get("stored_at") if record.metadata else None
    if stored_at_str:
        try:
            stored_at = datetime.fromisoformat(stored_at_str)
            # Normalize to UTC-aware
            if stored_at.tzinfo is None:
                stored_at = stored_at.replace(tzinfo=timezone.utc)
            cutoff = datetime.now(tz=timezone.utc) - timedelta(days=RECENCY_WINDOW_DAYS)
            if stored_at >= cutoff:
                return record.similarity * (1 + RECENCY_BOOST)
        except (ValueError, TypeError):
            pass
    return record.similarity


# ---------------------------------------------------------------------------
# SessionMemoryRetriever
# ---------------------------------------------------------------------------

class SessionMemoryRetriever:
    """
    Retrieves relevant memories at session start using semantic similarity
    plus recency weighting.

    Usage:
        retriever = SessionMemoryRetriever(db_url=DATABASE_URL)
        memories = await retriever.retrieve_for_session(
            user_id="user-123",
            relationship_id="rel-456",
            opening_message="I've been feeling overwhelmed lately",
            access_policy=AccessPolicy(can_read_private=True, can_read_shared_context=True),
        )
    """

    def __init__(self, db_url: str):
        self._store = VectorMemoryStore(db_url=db_url)

    async def retrieve_for_session(
        self,
        user_id: str,
        relationship_id: str,
        opening_message: str,
        access_policy: Optional[AccessPolicy] = None,
        top_k_private: int = 5,
        top_k_shared: int = 3,
    ) -> list[MemoryRecord]:
        """
        Retrieve semantically relevant memories for a session.

        Steps:
        1. Query private namespace (top_k_private results)
        2. If access_policy.can_read_shared_context: query shared namespace (top_k_shared)
        3. Apply recency weighting: boost memories from last 30 days by 20%
        4. Merge, deduplicate, sort by adjusted score

        Target: <40ms p50.

        Args:
            user_id: User to retrieve memories for.
            relationship_id: Used for shared namespace scoping (passed in metadata filter, future).
            opening_message: The user's first message; used as the embedding query.
            access_policy: Controls namespace access. Defaults to private-only.
            top_k_private: Number of private memories to retrieve (default 5).
            top_k_shared: Number of shared memories to retrieve (default 3).

        Returns:
            Merged, deduplicated list of MemoryRecord sorted by adjusted relevance.
        """
        if access_policy is None:
            access_policy = AccessPolicy()

        results: list[MemoryRecord] = []
        seen_ids: set[str] = set()

        # Query private namespace
        if access_policy.can_read_private:
            private_records = await self._store.query(
                user_id=user_id,
                query_text=opening_message,
                top_k=top_k_private,
                zone="private",
            )
            for record in private_records:
                if record.memory_id not in seen_ids:
                    seen_ids.add(record.memory_id)
                    results.append(record)

        # Query shared namespace
        if access_policy.can_read_shared_context:
            shared_records = await self._store.query(
                user_id=user_id,
                query_text=opening_message,
                top_k=top_k_shared,
                zone="shared",
            )
            for record in shared_records:
                if record.memory_id not in seen_ids:
                    seen_ids.add(record.memory_id)
                    results.append(record)

        # Apply recency boost and sort by adjusted score descending
        results.sort(key=_apply_recency_boost, reverse=True)

        return results
