"""
Layer 3 — contextual safety screen.

Asks a fast LLM to judge crisis / abuse risk given the message *and* the recent
conversation, catching context-dependent risk that neither rules (Layer 1) nor
single-message similarity (Layer 2) can see — e.g. an oblique "I just can't do
this anymore" after a chain of hopeless messages.

Uses the configured provider (OpenAI by default, matching the rest of the app),
and degrades to the original keyword heuristic when no key is set or the call
fails — so this layer is never *less* safe than the mock it replaces.
"""

import json
import os
from dataclasses import dataclass

from app.safety.layer1_rules import SignalCategory

_CLASSIFIER_MODEL_DEFAULT = "gpt-4.1-nano"

_VALID_CATEGORIES = {c.value for c in SignalCategory}

_SYSTEM = (
    "You are a safety classifier for a relationship-support app. Given the latest "
    "user message and recent context, judge the risk of: suicidal_ideation, "
    "self_harm, physical_abuse (the user being physically hurt by a partner), "
    "emotional_abuse, or coercive_control. If none apply, category is 'safe'.\n"
    "Respond ONLY with JSON: {\"category\": <one of the above or 'safe'>, "
    "\"score\": <0.0-1.0 risk>, \"reason\": <short phrase>}. Err toward caution: "
    "if a message plausibly signals someone in danger, score it high."
)


@dataclass
class Layer3Result:
    score: float
    category: SignalCategory
    reason: str


def _keyword_screen(message: str) -> Layer3Result:
    ml = message.lower()
    if "suicide" in ml or "kill" in ml:
        return Layer3Result(0.9, SignalCategory.SUICIDAL_IDEATION, "Context indicates self-harm risk")
    if "hit" in ml or "abuse" in ml:
        return Layer3Result(0.9, SignalCategory.PHYSICAL_ABUSE, "Context indicates domestic violence risk")
    return Layer3Result(0.0, SignalCategory.SAFE, "No risk detected")


def _to_category(value: str) -> SignalCategory:
    value = (value or "").strip().lower()
    return SignalCategory(value) if value in _VALID_CATEGORIES else SignalCategory.SAFE


async def screen_layer3(message: str, session_context: list) -> Layer3Result:
    if not os.environ.get("OPENAI_API_KEY"):
        return _keyword_screen(message)
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
        model = os.environ.get("SAFETY_CLASSIFIER_MODEL", _CLASSIFIER_MODEL_DEFAULT)

        context_lines = "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}"
            for m in (session_context or [])
            if m.get("content")
        )
        user_block = (f"Recent context:\n{context_lines}\n\n" if context_lines else "") + \
            f"Latest message: {message}"

        resp = await client.chat.completions.create(
            model=model,
            max_tokens=120,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user_block},
            ],
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        category = _to_category(data.get("category", "safe"))
        score = float(data.get("score", 0.0) or 0.0)
        reason = str(data.get("reason", ""))[:120]

        # Never let the model downgrade below the keyword floor.
        floor = _keyword_screen(message)
        if floor.score > score:
            return floor
        if category == SignalCategory.SAFE:
            return Layer3Result(score=score, category=category, reason=reason or "No risk detected")
        return Layer3Result(score=max(score, 0.0), category=category, reason=reason or "Contextual risk")
    except Exception:
        return _keyword_screen(message)
