"""Bliss inside the couple's thread.

Three jobs, in order of how often they should be felt:

1. **Rephrase on demand** — the user asks for help saying something.
2. **A pre-send check** — Bliss notices a message is likely to land badly and
   offers an alternative. Never blocks: the options are always send anyway,
   edit, or send the rephrase.
3. **Unprompted openings** — the end of a day, a moment worth answering warmly,
   a way back in after a rough exchange.

Two rules govern all of it.

**Fail open.** Every function here degrades to "carry on" rather than to an
error. If the model is slow, rate-limited or down, the message sends. Trapping
someone's message behind a broken classifier would be a far worse failure than
missing a warning.

**Stay rare.** An assistant that comments constantly stops being an assistant
and becomes a chaperone, and people stop typing honestly in front of it. The
unprompted paths are budgeted per day and deliberately hard to trigger.
"""

import hashlib
import logging
import os
import re
import threading
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone

from .models import AssistNudge, ChatAssistSettings, CoupleMessage

log = logging.getLogger(__name__)

# The inline model. Matches backend-fastapi's fast path; low latency matters
# more than eloquence for a one-line rewrite.
FAST_MODEL = os.environ.get("OPENAI_FAST_MODEL", "gpt-4.1-nano")

# The user is holding a finished message waiting to send, so this budget is
# tight — past it we let the message go rather than make them wait.
CHECK_TIMEOUT_SECONDS = 2.5
# They explicitly asked for help here, so a little more room is fine.
REPHRASE_TIMEOUT_SECONDS = 6.0

# How much of the thread Bliss reads for context.
CONTEXT_MESSAGES = 12

# At most one unprompted suggestion of each kind per person per day.
NUDGE_COOLDOWN = timedelta(hours=20)

# How long a verdict stays good for. Long enough to cover typing-pause then
# send; short enough that an edited-and-reverted draft is re-judged in context.
VERDICT_CACHE_SECONDS = 300

# "Evening" for the end-of-day suggestion, in the device's local hour.
NIGHT_HOURS = range(20, 24)


_client = None
_client_lock = threading.Lock()


def _get_client():
    """One process-wide client, so calls reuse the connection pool.

    Building a client per call meant a fresh TLS handshake every time.
    Measured on this workload that alone was p95 2.47s -> 1.32s; it is the
    cheapest latency win available and costs nothing.
    """
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                from openai import OpenAI

                _client = OpenAI(
                    api_key=os.environ.get("OPENAI_API_KEY", ""),
                    max_retries=0,  # a retry costs more than the answer is worth
                )
    return _client


def _complete(
    system: str, user: str, timeout: float, model: str | None = None, max_tokens: int = 220
) -> str | None:
    """One short completion. Returns None on any failure — never raises."""
    if not os.environ.get("OPENAI_API_KEY"):
        return None
    try:
        response = _get_client().with_options(timeout=timeout).chat.completions.create(
            model=model or FAST_MODEL,
            max_tokens=max_tokens,
            # Deterministic: the same draft should not flag on one send and
            # pass on the next. Also makes the verdict cache honest.
            temperature=0,
            messages=[
                # System first and byte-stable across calls, so a growing
                # prefix stays eligible for provider-side prompt caching.
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as exc:
        # Includes timeouts. The caller treats None as "no opinion".
        log.info("chat_assist_unavailable: %s", exc)
        return None


def settings_for(relationship) -> ChatAssistSettings:
    obj, _ = ChatAssistSettings.objects.get_or_create(relationship=relationship)
    return obj


def _thread_context(relationship, limit: int = CONTEXT_MESSAGES) -> str:
    """The tail of the conversation, oldest first, labelled by speaker."""
    recent = list(
        CoupleMessage.objects.filter(
            relationship=relationship, deleted_at__isnull=True, kind=CoupleMessage.KIND_TEXT
        ).order_by("-created_at")[:limit]
    )
    recent.reverse()
    lines = []
    for message in recent:
        body = message.body
        if body:
            lines.append(f"{message.sender_id}: {body}")
    return "\n".join(lines)


def _partner_notes(relationship, user) -> str:
    """What Bliss knows about the person being written *to*.

    This is what separates a generic rewrite from one that fits this couple —
    a message that lands fine with a secure partner can read as abandonment to
    an anxious one.
    """
    partner_id = (
        relationship.partner_b_id
        if relationship.partner_a_id == user.id
        else relationship.partner_a_id
    )
    if not partner_id:
        return ""
    try:
        from apps.personalization.models import UserProfile

        profile = UserProfile.objects.filter(user_id=partner_id).first()
    except Exception:
        profile = None
    if profile is None:
        return ""

    notes = []
    if getattr(profile, "attachment_style", ""):
        notes.append(f"attachment style: {profile.attachment_style}")
    if getattr(profile, "communication_style_preference", ""):
        notes.append(f"prefers {profile.communication_style_preference} communication")
    return "; ".join(notes)


# ── 1. Rephrase on demand ───────────────────────────────────────────────────

_REPHRASE_SYSTEM = (
    "You help one partner say a hard thing to the other so it lands kindly and "
    "still says what they actually mean. Keep their voice — do not make it "
    "formal, therapeutic or longer than needed. Never add affection they did "
    "not express. Reply with the rewritten message only, no preamble, no quotes."
)


def rephrase(relationship, user, draft: str) -> dict:
    """Rewrite a draft. Returns ``{"suggestion": str|None}``."""
    if not draft.strip():
        return {"suggestion": None}
    try:
        if not settings_for(relationship).assist_enabled:
            return {"suggestion": None}

        context = _thread_context(relationship)
        notes = _partner_notes(relationship, user)
        prompt = "\n\n".join(
            part
            for part in [
                f"Recent conversation:\n{context}" if context else "",
                f"About the partner they are writing to: {notes}" if notes else "",
                f"Their draft:\n{draft}",
            ]
            if part
        )
        suggestion = _complete(_REPHRASE_SYSTEM, prompt, REPHRASE_TIMEOUT_SECONDS)
        return {"suggestion": suggestion or None}
    except Exception as exc:
        log.warning("chat_assist_rephrase_failed: %s", exc)
        return {"suggestion": None}


# ── 2. Pre-send check ───────────────────────────────────────────────────────

_CHECK_SYSTEM = (
    "You review a message one partner is about to send the other and decide "
    "whether it is likely to wound rather than land.\n"
    "Flag it ONLY for contempt, name-calling, sweeping accusations "
    "('you always', 'you never'), threats, or hitting a known sore spot. "
    "Ordinary bluntness, disagreement, frustration and sadness are NOT flags — "
    "people are allowed to be upset with each other.\n"
    "Reply in exactly this format and nothing else:\n"
    "VERDICT: ok\n"
    "or\n"
    "VERDICT: caution\n"
    "REASON: <at most 12 words, addressed to the sender, never scolding>\n"
    "SUGGESTION: <the same message, rewritten to say the same thing without the sting>"
)


# ── Tier 0: decide locally whether the model is worth asking ────────────────
#
# The check runs on every send, but the overwhelming majority of messages
# between partners are logistics and warmth. Paying a model call to be told
# "ok" about "grab milk on the way home" is the single biggest waste in this
# feature — it is most of the cost and all of the latency, on messages that
# were never going to flag.
#
# So a local gate runs first. It is deliberately *generous*: it escalates on
# any hint of second-person negativity, because the cost of escalating
# unnecessarily is one cheap call, while the cost of skipping wrongly is a
# missed catch. Only clearly-benign drafts short-circuit.

_CONTEMPT_MARKERS = (
    "pathetic", "stupid", "idiot", "moron", "selfish", "lazy", "useless",
    "ridiculous", "grow up", "shut up", "whatever", "get over it", "childish",
    "immature", "disgusting", "embarrassing",
)

# Sweeping character claims, the Gottman "always/never" pattern.
_ABSOLUTE_MARKERS = ("always", "never", "every single time", "nobody else", "no one else")

_THREAT_MARKERS = ("i'm done", "im done", "i'm gone", "im gone", "watch me", "or else")

# Second-person plus any of these reads as an attack on the person rather than
# a description of a feeling.
#
# Matched on word boundaries, not substrings. An earlier version looked for
# "you " with a trailing space and so missed "nobody else would put up with
# you" — real contempt, silently skipped, because the word ended the sentence.
_SECOND_PERSON_RE = re.compile(r"\b(you|your|you're|youre|yourself|u)\b")

_NEGATIVE_WORDS = (
    "hate", "fault", "blame", "don't care", "dont care", "didn't even",
    "didnt even", "don't even", "dont even", "ruin", "worst", "sick of",
    "fed up", "typical", "put up with",
)


def _needs_model(draft: str) -> bool:
    """Is this draft worth spending a completion on?"""
    text = draft.lower()
    second_person = bool(_SECOND_PERSON_RE.search(text))

    if any(m in text for m in _CONTEMPT_MARKERS):
        return True
    if any(m in text for m in _THREAT_MARKERS):
        return True
    # "always"/"never" only matter when aimed at the partner: "I never sleep
    # well" is not an accusation.
    if any(m in text for m in _ABSOLUTE_MARKERS) and second_person:
        return True
    if second_person and any(n in text for n in _NEGATIVE_WORDS):
        return True
    # Shouting: sustained caps in a message long enough to mean it.
    letters = [c for c in draft if c.isalpha()]
    if len(letters) > 12 and sum(c.isupper() for c in letters) / len(letters) > 0.7:
        return True
    if draft.count("!") >= 3:
        return True
    return False


def _parse_check(raw: str) -> dict:
    verdict, reason, suggestion = "ok", "", ""
    for line in raw.splitlines():
        lowered = line.strip().lower()
        if lowered.startswith("verdict:"):
            verdict = "caution" if "caution" in lowered else "ok"
        elif lowered.startswith("reason:"):
            reason = line.split(":", 1)[1].strip()
        elif lowered.startswith("suggestion:"):
            suggestion = line.split(":", 1)[1].strip()
    # A caution with nothing to offer is just a scolding, so downgrade it.
    if verdict == "caution" and not suggestion:
        return {"verdict": "ok", "reason": "", "suggestion": ""}
    return {"verdict": verdict, "reason": reason, "suggestion": suggestion}


def check_before_send(relationship, user, draft: str) -> dict:
    """Should this message give the sender pause?

    Returns ``{"verdict": "ok"|"caution", "reason": str, "suggestion": str}``.
    Anything unexpected resolves to ``ok`` — see the fail-open rule above.
    """
    blank = {"verdict": "ok", "reason": "", "suggestion": ""}
    if not draft.strip():
        return blank

    # Belt and braces. _complete already swallows provider errors, but this is
    # the one call standing between a person and their own message: if anything
    # at all goes wrong here — building context, reading settings, a future
    # refactor — the message goes.
    try:
        config = settings_for(relationship)
        if not (config.assist_enabled and config.interception_enabled):
            return blank

        # Tier 0 — local. Most sends stop here: no call, no cost, no wait.
        if not _needs_model(draft):
            return blank

        # Tier 1 — cached verdict. The client checks on a typing pause and
        # again on send; the second call must not pay for the first's answer.
        # Keyed per relationship so one couple's drafts never resolve another's.
        cache_key = "assist:check:{}:{}".format(
            relationship.id, hashlib.sha256(draft.encode()).hexdigest()[:32]
        )
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # Tier 2 — ask the model.
        context = _thread_context(relationship, limit=6)
        notes = _partner_notes(relationship, user)
        prompt = "\n\n".join(
            part
            for part in [
                f"Recent conversation:\n{context}" if context else "",
                f"About the partner receiving it: {notes}" if notes else "",
                f"Message about to be sent:\n{draft}",
            ]
            if part
        )
        raw = _complete(_CHECK_SYSTEM, prompt, CHECK_TIMEOUT_SECONDS)
        if not raw:
            return blank
        verdict = _parse_check(raw)
        cache.set(cache_key, verdict, VERDICT_CACHE_SECONDS)
        return verdict
    except Exception as exc:
        log.warning("chat_assist_check_failed_open: %s", exc)
        return blank


# ── 3. Unprompted openings ──────────────────────────────────────────────────

_NIGHT_SYSTEM = (
    "It is the end of the day. Suggest one short, warm message this person "
    "could send their partner right now — specific to what actually happened "
    "between them today if the conversation shows it, otherwise simply tender. "
    "One or two sentences, their own everyday voice, no greeting card language, "
    "no emoji unless it genuinely fits. Reply with the message only."
)

_OPPORTUNITY_SYSTEM = (
    "Read this conversation and decide whether the partner has just opened a "
    "door worth walking through — named a need, admitted something hard, "
    "mentioned something they are dreading or looking forward to.\n"
    "If they have, reply with one short message the user could send in "
    "response, in their own voice.\n"
    "If they have not — and most of the time they have not — reply with exactly "
    "NONE. Do not invent an opening to be helpful."
)

_REPAIR_SYSTEM = (
    "This couple had a sharp exchange a little while ago and it has gone quiet. "
    "Suggest one short message that offers a way back in: not an apology for "
    "something they may not have done, not a rehash of the argument — just an "
    "opening that makes it easy for the other person to come back. "
    "Reply with the message only."
)


def _recent_nudge(relationship, user, kind: str) -> bool:
    since = timezone.now() - NUDGE_COOLDOWN
    return AssistNudge.objects.filter(
        relationship=relationship, user=user, kind=kind, created_at__gte=since
    ).exists()


def _had_sharp_exchange(relationship) -> bool:
    """Cheap, local check for a rupture in the last few hours.

    Deliberately keyword-based rather than a model call: this runs on an open,
    and paying for a completion to discover that nothing happened is the wrong
    trade.
    """
    since = timezone.now() - timedelta(hours=6)
    recent = CoupleMessage.objects.filter(
        relationship=relationship, created_at__gte=since, deleted_at__isnull=True
    ).order_by("-created_at")[:20]
    markers = (
        "you always",
        "you never",
        "whatever",
        "forget it",
        "i'm done",
        "im done",
        "don't care",
        "dont care",
    )
    return any(any(m in (msg.body or "").lower() for m in markers) for msg in recent)


def nudge_for(relationship, user, local_hour: int | None = None) -> AssistNudge | None:
    """The one suggestion worth offering right now, or None.

    Order matters: a repair opening outranks an end-of-day message, because a
    warm goodnight on top of an unresolved row reads as tone-deaf.
    """
    try:
        return _nudge_for(relationship, user, local_hour)
    except Exception as exc:
        # An unprompted extra must never break opening the thread.
        log.warning("chat_assist_nudge_failed: %s", exc)
        return None


def _nudge_for(relationship, user, local_hour: int | None) -> AssistNudge | None:
    config = settings_for(relationship)
    if not config.assist_enabled:
        return None

    context = _thread_context(relationship)
    if not context:
        return None

    notes = _partner_notes(relationship, user)
    base = f"Conversation:\n{context}" + (f"\n\nAbout their partner: {notes}" if notes else "")

    # 1. Repair first.
    if _had_sharp_exchange(relationship) and not _recent_nudge(
        relationship, user, AssistNudge.KIND_REPAIR
    ):
        suggestion = _complete(_REPAIR_SYSTEM, base, REPHRASE_TIMEOUT_SECONDS)
        if suggestion:
            return AssistNudge.objects.create(
                relationship=relationship,
                user=user,
                kind=AssistNudge.KIND_REPAIR,
                suggestion=suggestion,
            )
        return None

    # 2. End of day.
    if (
        config.night_nudge_enabled
        and local_hour is not None
        and local_hour in NIGHT_HOURS
        and not _recent_nudge(relationship, user, AssistNudge.KIND_NIGHT)
    ):
        suggestion = _complete(_NIGHT_SYSTEM, base, REPHRASE_TIMEOUT_SECONDS)
        if suggestion:
            return AssistNudge.objects.create(
                relationship=relationship,
                user=user,
                kind=AssistNudge.KIND_NIGHT,
                suggestion=suggestion,
            )
        return None

    # 3. An opening in what the partner just said.
    if not _recent_nudge(relationship, user, AssistNudge.KIND_OPPORTUNITY):
        suggestion = _complete(_OPPORTUNITY_SYSTEM, base, REPHRASE_TIMEOUT_SECONDS)
        if suggestion and suggestion.strip().upper() != "NONE":
            return AssistNudge.objects.create(
                relationship=relationship,
                user=user,
                kind=AssistNudge.KIND_OPPORTUNITY,
                suggestion=suggestion,
            )

    return None
