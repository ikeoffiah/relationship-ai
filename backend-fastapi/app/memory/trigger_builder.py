"""
Emotional Trigger Inventory Builder (REL-89)

Analyzes message sequences for emotional triggers:
- Explicit distress markers
- Session exit signals (short dismissal followed by end of session)
- Max 20 triggers in inventory (oldest removed when full)
"""

import re
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class TriggerItem:
    """Represents an identified emotional trigger."""

    topic: str           # The topic/phrase that preceded distress
    tone: str            # Tone preceding distress (if identifiable)
    severity: int        # 1 (mild) to 3 (severe, caused session exit)
    confidence: float    # 0.0-1.0
    session_id: str = ""


# ---------------------------------------------------------------------------
# Detection configuration
# ---------------------------------------------------------------------------

CONFIDENCE_THRESHOLD = 0.6
INVENTORY_MAX_SIZE = 20

# Explicit distress markers (case-insensitive)
DISTRESS_MARKERS = [
    r"this is hard to say",
    r"i don't (want|know how) to talk about this",
    r"i don't know where to start",
    r"(this is|it's) (painful|difficult|hard)",
    r"i feel (overwhelmed|scared|anxious|helpless)",
    r"i can't (do this|talk about this)",
    r"please don't (ask|push|press) me",
]

# Session exit signals (short dismissal messages)
EXIT_SIGNALS = [
    "ok", "fine", "whatever", "i'm done", "stop",
    "never mind", "nevermind", "forget it", "goodbye", "bye",
]


def _is_distress_marker(text: str) -> bool:
    text_lower = text.lower().strip()
    for pattern in DISTRESS_MARKERS:
        if re.search(pattern, text_lower):
            return True
    return False


def _is_exit_signal(text: str) -> bool:
    text_lower = text.lower().strip().rstrip("!.")
    return text_lower in EXIT_SIGNALS or len(text_lower.split()) <= 3 and text_lower in EXIT_SIGNALS


# ---------------------------------------------------------------------------
# TriggerInventoryBuilder
# ---------------------------------------------------------------------------

# In-memory store: user_id -> list[TriggerItem]
# Production: persist to PostgreSQL emotional_triggers table.
_trigger_store: dict[str, list[TriggerItem]] = {}


class TriggerInventoryBuilder:
    """
    Builds and maintains an emotional trigger inventory per user.

    Analyzes message sequences for:
    1. Explicit distress markers ("This is hard to say but...")
    2. Session exit signals (short "ok"/"I don't want to talk about this"
       followed by session end within 2 turns)

    Inventory is capped at INVENTORY_MAX_SIZE=20 items (oldest removed first).
    """

    def __init__(self, store: Optional[dict] = None):
        self._store = store if store is not None else _trigger_store

    def get_triggers(self, user_id: str) -> list[TriggerItem]:
        """Return the trigger inventory for a user."""
        return self._store.get(user_id, [])

    def update_triggers(
        self,
        session_messages: list[dict],
        user_id: str,
        session_id: str = "",
    ) -> list[TriggerItem]:
        """
        Analyze session messages and update the trigger inventory.

        Args:
            session_messages: List of {"role": str, "content": str} dicts
            user_id: User whose inventory to update
            session_id: Session reference for provenance

        Returns:
            Updated trigger inventory for the user.
        """
        inventory = self._store.setdefault(user_id, [])
        user_messages = [
            m for m in session_messages if m.get("role") == "user"
        ]

        for i, msg in enumerate(user_messages):
            content = msg.get("content", "")
            new_trigger: Optional[TriggerItem] = None

            # --- Detection 1: Explicit distress markers ---
            if _is_distress_marker(content):
                # The topic is the distress statement itself
                new_trigger = TriggerItem(
                    topic=content[:100],
                    tone="distress_marker",
                    severity=2,
                    confidence=0.75,
                    session_id=session_id,
                )

            # --- Detection 2: Session exit signal ---
            # Short dismissal as the last user message (or second-to-last)
            is_near_end = i >= len(user_messages) - 2
            if is_near_end and _is_exit_signal(content) and not new_trigger:
                # Look at the message just before for the topic that triggered exit
                prev_content = user_messages[i - 1].get("content", "") if i > 0 else ""
                new_trigger = TriggerItem(
                    topic=prev_content[:100] if prev_content else content[:100],
                    tone="withdrawal",
                    severity=3,  # Caused session exit
                    confidence=0.7,
                    session_id=session_id,
                )

            if new_trigger and new_trigger.confidence >= CONFIDENCE_THRESHOLD:
                inventory.append(new_trigger)

                # Enforce cap: remove oldest when over limit
                while len(inventory) > INVENTORY_MAX_SIZE:
                    inventory.pop(0)

        self._store[user_id] = inventory
        return inventory

    def clear_user_data(self, user_id: str) -> None:
        """GDPR: Remove all trigger data for a user."""
        self._store.pop(user_id, None)
