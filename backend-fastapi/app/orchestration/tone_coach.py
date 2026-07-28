"""
In-chat tone coach: read the emotional tone of a message, help a user judge and
soften their own draft before sending, and suggest attuned things to say next.

Design principles (this feature touches the most sensitive thing in the app —
how two people speak to each other):

* **Self-regulation, not surveillance.** A "mood read" of a partner's message is
  always framed as a *guess to build empathy*, never a verdict, and always paired
  with "check in directly." Nothing is stored.
* **Kindness, not manipulation.** Rewrites aim for the honest, clear, kind
  version of what the user already means (a "soft startup") — never a more
  persuasive, guilt-tripping, or deceptive version. The system prompt forbids
  that explicitly.
* **Safety first.** Before coaching a draft we screen it with the same Layer-1
  rules the counseling path uses. If the draft carries crisis, abusive, coercive,
  or manipulative signals we do NOT "soften" it into something more palatable —
  that would help disguise harm. We surface support instead and decline to
  rewrite.
* **Never crashes, never empty.** Like ``generate_reply``, every path degrades to
  a safe, useful default when the model is unavailable or returns junk.

All model access goes through the provider-agnostic ``generate_reply`` so the
same ``LLM_PROVIDER`` switch applies here as in counseling.
"""

import json
from typing import Dict, List, Optional

from app.orchestration.llm_provider import generate_reply
from app.safety.layer1_rules import SignalCategory, screen_layer1

# Any Layer-1 hit at or above this score gates the coach. Deliberately low: the
# harmful categories below include *medium*-confidence patterns (~0.55), and for
# a safety gate we accept occasionally over-declining a benign draft over ever
# softening an abusive or coercive one into something more palatable.
_GATE_SCORE = 0.5

# Categories in a user's *own draft* that mean we must not offer a "smoother"
# rewrite — softening these would help disguise harm, not improve communication.
_DECLINE_TO_REWRITE = {
    SignalCategory.PERPETRATOR_LANGUAGE,
    SignalCategory.COERCIVE_CONTROL,
    SignalCategory.MANIPULATION_ATTEMPT,
    SignalCategory.PHYSICAL_ABUSE,
    SignalCategory.EMOTIONAL_ABUSE,
}
# Categories that mean the *writer* may be in distress — point to support.
_WRITER_IN_CRISIS = {
    SignalCategory.SUICIDAL_IDEATION,
    SignalCategory.SELF_HARM,
}

_SAFETY_MESSAGE = (
    "This sounds really heavy. Before sending anything, it might help to talk it "
    "through — with each other when it's safe, or with someone who can support "
    "you. You can also reach out to a helpline from the Support section."
)


def _extract_json(text: str) -> Optional[dict]:
    """Best-effort parse of a model reply into a dict, tolerating code fences and
    surrounding prose. Returns None if nothing parseable is found."""
    if not text:
        return None
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, TypeError):
        pass
    # Fall back to the first {...} span.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None
    return None


# ── Mood read ───────────────────────────────────────────────────────────

_MOOD_SYSTEM = (
    "You read the emotional tone of a single chat message between romantic "
    "partners, to help the reader respond with empathy. You are NOT a lie "
    "detector and you never claim certainty about what the person 'really' means. "
    "Respond ONLY with strict JSON of the form: "
    '{"mood": "<one or two words>", "intensity": "low|medium|high", '
    '"summary": "<one warm sentence, at most 20 words>", '
    '"suggestion": "<one gentle sentence on how to respond>"}. '
    "Keep it non-judgmental and tentative. Never diagnose."
)

# Shown when the model is unavailable or returns unparseable output.
_MOOD_FALLBACK = {
    "mood": "unclear",
    "intensity": "medium",
    "summary": "It's hard to be sure of the tone from text alone.",
    "suggestion": "When in doubt, ask them gently how they're feeling.",
    "disclaimer": "This is a guess to help you empathize — check in directly.",
}


async def analyze_mood(text: str) -> dict:
    """Read the emotional tone of one message. Always returns a dict with
    mood/intensity/summary/suggestion/disclaimer keys."""
    text = (text or "").strip()
    if not text:
        return dict(_MOOD_FALLBACK)

    raw = await generate_reply(_MOOD_SYSTEM, [{"role": "user", "content": text}], fast=True)
    parsed = _extract_json(raw) or {}
    return {
        "mood": str(parsed.get("mood") or _MOOD_FALLBACK["mood"])[:40],
        "intensity": _norm_intensity(parsed.get("intensity")),
        "summary": str(parsed.get("summary") or _MOOD_FALLBACK["summary"])[:200],
        "suggestion": str(parsed.get("suggestion") or _MOOD_FALLBACK["suggestion"])[:200],
        # Always attached, model or fallback — the empathy-not-certainty framing.
        "disclaimer": _MOOD_FALLBACK["disclaimer"],
    }


def _norm_intensity(value) -> str:
    v = str(value or "").strip().lower()
    return v if v in ("low", "medium", "high") else "medium"


# ── Coach a draft (judge + rewrite) ─────────────────────────────────────

_COACH_SYSTEM = (
    "You are a kind communication coach for someone about to send a message to "
    "their romantic partner. Your goal is the honest, clear, KIND version of what "
    "they already mean — a 'soft startup': owning their feelings, no blame, no "
    "contempt. You must NEVER make a message more manipulative, guilt-tripping, "
    "coercive, threatening, or deceptive, and never help them 'win' an argument. "
    "If the draft is already kind, say so and offer only light polish. "
    "Respond ONLY with strict JSON: "
    '{"read": "<one sentence on how this may land for the partner>", '
    '"tone": "<one or two words>", '
    '"rewrites": ["<kinder version 1>", "<kinder version 2>"]}. '
    "Give at most 3 rewrites, each preserving the real meaning."
)

_COACH_FALLBACK = {
    "read": "Take a breath and read it once more as if you were receiving it.",
    "tone": "unclear",
    "rewrites": [],
    "disclaimer": "Suggestions only — your words are yours to choose.",
}


async def coach_reply(draft: str, partner_mood: Optional[str] = None) -> dict:
    """Judge a user's own draft and offer kinder rewrites.

    If the draft carries harmful signals, declines to rewrite and returns a
    ``safety`` block instead. Always returns a dict.
    """
    draft = (draft or "").strip()
    if not draft:
        return {**_COACH_FALLBACK, "safety": None}

    # Safety gate on the user's OWN words before any softening.
    res = screen_layer1(draft)
    if res.score >= _GATE_SCORE and res.category in _DECLINE_TO_REWRITE:
        return {
            "read": "",
            "tone": "",
            "rewrites": [],
            "disclaimer": _COACH_FALLBACK["disclaimer"],
            "safety": {
                "declined": True,
                "reason": "harm_signals",
                "message": (
                    "I can't help rephrase this one. If things feel unsafe or "
                    "controlling in either direction, that's worth talking to "
                    "someone about — see the Support section."
                ),
            },
        }
    if res.score >= _GATE_SCORE and res.category in _WRITER_IN_CRISIS:
        return {
            "read": "",
            "tone": "",
            "rewrites": [],
            "disclaimer": _COACH_FALLBACK["disclaimer"],
            "safety": {"declined": True, "reason": "writer_distress", "message": _SAFETY_MESSAGE},
        }

    context = draft
    if partner_mood:
        context = f"My partner seems to be feeling: {partner_mood}.\nMy draft: {draft}"

    raw = await generate_reply(_COACH_SYSTEM, [{"role": "user", "content": context}], fast=True)
    parsed = _extract_json(raw) or {}
    rewrites = parsed.get("rewrites")
    rewrites = [str(r)[:500] for r in rewrites][:3] if isinstance(rewrites, list) else []
    return {
        "read": str(parsed.get("read") or _COACH_FALLBACK["read"])[:200],
        "tone": str(parsed.get("tone") or _COACH_FALLBACK["tone"])[:40],
        "rewrites": rewrites,
        "disclaimer": _COACH_FALLBACK["disclaimer"],
        "safety": None,
    }


# ── Auto-suggestions ────────────────────────────────────────────────────

_SUGGEST_SYSTEM = (
    "Given the recent messages between romantic partners, suggest up to 3 short, "
    "warm things the reader could say next to keep the conversation caring and "
    "constructive. Favor curiosity, validation, and repair over problem-solving. "
    "Never suggest anything manipulative, dismissive, or contemptuous. "
    'Respond ONLY with strict JSON: {"suggestions": ["...", "...", "..."]}. '
    "Each suggestion is one sentence the reader could send as-is."
)


async def suggest_replies(messages: List[Dict[str, str]]) -> List[str]:
    """Suggest up to 3 attuned things to say next, given recent messages
    (each {"role": "me"|"partner", "content": str}). Returns [] on failure."""
    cleaned = [m for m in (messages or []) if (m.get("content") or "").strip()]
    if not cleaned:
        return []
    transcript = "\n".join(
        f"{'Me' if m.get('role') == 'me' else 'Partner'}: {m['content'].strip()}"
        for m in cleaned[-8:]  # only the recent tail matters
    )
    raw = await generate_reply(_SUGGEST_SYSTEM, [{"role": "user", "content": transcript}], fast=True)
    parsed = _extract_json(raw) or {}
    suggestions = parsed.get("suggestions")
    if not isinstance(suggestions, list):
        return []
    return [str(s).strip()[:300] for s in suggestions if str(s).strip()][:3]


# ── Daily conversation "vibe" ────────────────────────────────────────────
#
# A playful, one-word read of the day's conversation ("Playful", "Intimate",
# "Reconnecting", "Quiet"…). The vocabulary is CURATED and constrained on
# purpose: the model may only pick from this list, so the label is always
# on-brand and — importantly — a hard day maps to a gentle, honest label
# (Tense / Distant / Supportive / Reconnecting) rather than something flippant.

# (label, emoji, blurb) — order matters only for the deterministic fallback,
# which scans for the first matching signal below.
VIBES = [
    ("Intimate", "🔥", "Close and emotionally open."),
    ("Romantic", "💕", "Affectionate and full of love."),
    ("Sexy", "😏", "Flirty and a little charged."),
    ("Playful", "😄", "Teasing, light, and fun."),
    ("Silly", "🤪", "Goofy and lighthearted."),
    ("Deep", "🌊", "Reflective and meaningful."),
    ("Cozy", "☕", "Warm and easy."),
    ("Supportive", "🤝", "One of you leaning on the other."),
    ("Reconnecting", "🌱", "Finding your way back to each other."),
    ("Adventurous", "🧭", "Dreaming and planning together."),
    ("Logistical", "🗓️", "Mostly plans and to-dos today."),
    ("Tense", "⛅", "A little friction in the air."),
    ("Distant", "🌫️", "A bit far apart today."),
    ("Quiet", "🌙", "Only a few words today."),
    ("Everyday", "🌼", "Ordinary and steady."),
]
_VIBE_BY_LABEL = {label.lower(): (label, emoji, blurb) for label, emoji, blurb in VIBES}
_VIBE_DISCLAIMER = "A playful read of today — just for fun."

_VIBE_SYSTEM = (
    "You give a single playful label describing the overall vibe of a couple's "
    "conversation today. Choose EXACTLY ONE label from this list and no other: "
    + ", ".join(label for label, _, _ in VIBES) + ". "
    "Pick the most fitting one. If the day was hard, pick an honest, gentle label "
    "(Tense, Distant, Supportive, or Reconnecting) rather than a flippant one. "
    'Respond ONLY with strict JSON: {"label": "<one label from the list>", '
    '"blurb": "<one short, warm sentence, at most 15 words>"}.'
)


def _heuristic_vibe(text: str, count: int) -> tuple:
    """Deterministic fallback label from simple signals — used when the model is
    unavailable, so the feature still works (and CI can assert it)."""
    t = f" {text.lower()} "
    if count < 4:
        return _VIBE_BY_LABEL["quiet"]

    def has(*words: str) -> bool:
        return any(w in t for w in words)

    if has("sorry", "forgive", "make up", "made up", "my fault"):
        return _VIBE_BY_LABEL["reconnecting"]
    if has("angry", "annoyed", "upset", "frustrated", "argue", "fight", "whatever."):
        return _VIBE_BY_LABEL["tense"]
    if has("sexy", "want you", "in bed", "turn me on", "😏", "😈", "tonight 😉"):
        return _VIBE_BY_LABEL["sexy"]
    if has("love you", "miss you", "❤️", "😘", "my love", "babe", "gorgeous"):
        return _VIBE_BY_LABEL["romantic"]
    if has("haha", "lol", "lmao", "😂", "🤣", "😄", "so funny"):
        return _VIBE_BY_LABEL["playful"]
    if has("remind", "schedule", "appointment", "groceries", "bill", "pick up", "pay ", "book "):
        return _VIBE_BY_LABEL["logistical"]
    if has("scared", "worried", "hard time", "struggling", "here for you", "you okay"):
        return _VIBE_BY_LABEL["supportive"]
    return _VIBE_BY_LABEL["everyday"]


async def daily_vibe(messages: List[Dict[str, str]]) -> dict:
    """A playful one-word read of the day's conversation. Always returns
    {"label", "emoji", "blurb", "disclaimer"}."""
    cleaned = [m for m in (messages or []) if (m.get("content") or "").strip()]
    joined = " ".join(m["content"].strip() for m in cleaned)

    if not cleaned:
        label, emoji, blurb = _VIBE_BY_LABEL["quiet"]
        return {"label": label, "emoji": emoji, "blurb": blurb, "disclaimer": _VIBE_DISCLAIMER}

    transcript = "\n".join(
        f"{'Me' if m.get('role') == 'me' else 'Partner'}: {m['content'].strip()}"
        for m in cleaned[-40:]
    )
    raw = await generate_reply(_VIBE_SYSTEM, [{"role": "user", "content": transcript}], fast=True)
    parsed = _extract_json(raw) or {}
    chosen = _VIBE_BY_LABEL.get(str(parsed.get("label", "")).strip().lower())
    if chosen:
        label, emoji, default_blurb = chosen
        blurb = str(parsed.get("blurb") or default_blurb)[:120]
    else:
        # Model unavailable or off-vocab → deterministic fallback.
        label, emoji, blurb = _heuristic_vibe(joined, len(cleaned))
    return {"label": label, "emoji": emoji, "blurb": blurb, "disclaimer": _VIBE_DISCLAIMER}
