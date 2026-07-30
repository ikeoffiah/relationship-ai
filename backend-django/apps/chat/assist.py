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

from .models import AssistNudge, ChatAssistSettings, CoupleMessage, ThreadSummary

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


def _rolling_summary(relationship) -> str:
    """The précis of everything older than the verbatim window.

    A plain database read — the summary is written by a background task, never
    generated here, so this adds no latency to a send.
    """
    row = ThreadSummary.objects.filter(relationship=relationship).only("summary").first()
    return row.summary if row and row.summary else ""


def message_text(message) -> str:
    """What this message contributes to Bliss's reading of the thread.

    A voice note's text lives on its media row, not in ``body``. Without this
    fallback a spoken message is not just unreadable here — it is invisible,
    because the loop below skips anything with an empty body. Voice is where
    the loaded messages go, so that blind spot lands exactly where it hurts.

    An image contributes its caption if it has one, and otherwise nothing:
    there is no point telling a text model that a photo happened.
    """
    body = message.body
    if body:
        return body
    if message.kind == CoupleMessage.KIND_VOICE and message.media_id:
        return message.media.transcript
    return ""


def _thread_context(relationship, limit: int = CONTEXT_MESSAGES) -> str:
    """The tail of the conversation, oldest first, labelled by speaker."""
    recent = list(
        CoupleMessage.objects.filter(
            relationship=relationship,
            deleted_at__isnull=True,
            kind__in=(CoupleMessage.KIND_TEXT, CoupleMessage.KIND_VOICE, CoupleMessage.KIND_IMAGE),
        )
        .select_related("media")
        .order_by("-created_at")[:limit]
    )
    recent.reverse()
    lines = []
    for message in recent:
        text = message_text(message)
        if text:
            lines.append(f"{message.sender_id}: {text}")
    verbatim = "\n".join(lines)

    # Summary first, then the verbatim tail. Longer-arc awareness at a fixed
    # token cost: the summary does not grow as the relationship does.
    summary = _rolling_summary(relationship)
    if summary and verbatim:
        return f"Background on this couple:\n{summary}\n\nMost recent messages:\n{verbatim}"
    return verbatim or summary


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

    # What they actually do, alongside what they said about themselves. This
    # qualifies the self-report rather than replacing it: the RSQ answer stays
    # exactly as they gave it, and this sits next to it. Phrased as tone
    # instructions, never as a label — "tends to go quiet when things get
    # sharp", not "avoidant", because the observable is evidence and the label
    # is a leap.
    try:
        from apps.personalization.behaviour import guidance_for

        notes.extend(guidance_for(partner_id))
    except Exception:
        pass
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

# Contempt is the single strongest predictor of a relationship failing, and it
# is also the thing a keyword list can actually catch — so this list is
# deliberately long. Recall matters far more than precision here: a term that
# over-triggers costs one cheap call the model then clears, while a term that
# is missing means the model never sees that message at all.
#
# What is deliberately NOT here: words that are both extremely common and
# usually benign ("obviously", "seriously", "actually"). Those would push the
# escalation rate toward 100% and cost the tiering its whole purpose without
# catching anything.

# Split in two, because these words behave differently.
#
# Strong terms are contempt wherever they appear — nobody calls the traffic a
# "worthless bastard" and means it kindly. Contextual terms are only contempt
# when aimed at a person: "that show was ridiculous" and "this traffic is
# disgusting" are ordinary sentences, and firing on them was pure waste.
#
# Matched on word boundaries, so "pig" does not fire on "pigment".
_CONTEMPT_WORDS_STRONG = (
    # name-calling
    "pathetic", "idiot", "moron", "loser", "jerk", "asshole", "arsehole",
    "bitch", "bastard", "prick", "twat", "psycho", "brat", "slob",
    # character attacks
    "worthless", "spineless", "narcissist", "insufferable",
    # disgust aimed at a person
    "revolting", "repulsive", "vile", "sickening",
    # dismissal of a person's mind
    "delusional", "unhinged", "hysterical",
)

# Contempt only when there is a "you" to attach them to.
_CONTEMPT_WORDS_CONTEXTUAL = (
    "stupid", "dumb", "selfish", "lazy", "useless", "childish", "immature",
    "manipulative", "toxic", "controlling", "disgusting", "gross", "ridiculous",
    "absurd", "laughable", "dramatic", "embarrassing", "humiliating", "freak",
    "weirdo", "pig", "clown", "joke",
)

# Phrases — matched as substrings, since word boundaries do not help here.
_CONTEMPT_PHRASES = (
    # mockery
    "grow up", "shut up", "get over it", "get a grip", "give me a break",
    "oh please", "boo hoo", "poor you", "cry me a river", "wow just wow",
    "spare me", "you're kidding me", "youre kidding me",
    # minimising / gaslighting-adjacent
    "you're overreacting", "youre overreacting", "calm down", "you're too sensitive",
    "youre too sensitive", "stop being so", "drama queen", "it's not that deep",
    "its not that deep", "you're imagining", "youre imagining", "that never happened",
    "no one would believe", "nobody would believe",
    # condescension
    "as usual", "typical you", "here we go again", "why am i not surprised",
    "of course you", "should have known", "figures",
    # character verdicts
    "just like your mother", "just like your father", "you'll never change",
    "youll never change", "that's who you are", "thats who you are",
    "this is why", "no wonder",
    # profanity aimed at the partner
    "fuck you", "screw you", "go to hell", "piss off", "sod off",
    # stonewalling / withdrawal
    "forget it", "don't talk to me", "dont talk to me",
    "leave me alone", "done talking", "not doing this",
    # relationship threats thrown in anger
    "maybe we should break up", "i want a divorce", "we're done", "were done",
)

_STRONG_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in _CONTEMPT_WORDS_STRONG) + r")\b"
)
_CONTEXTUAL_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in _CONTEMPT_WORDS_CONTEXTUAL) + r")\b"
)

# Sweeping character claims, the Gottman "always/never" pattern.
_ABSOLUTE_MARKERS = (
    "always", "never", "every single time", "every time", "nobody else",
    "no one else", "not once", "constantly",
)

_THREAT_MARKERS = (
    "i'm done", "im done", "i'm gone", "im gone", "watch me", "or else",
    "you'll regret", "youll regret", "don't push me", "dont push me",
)

# Second-person plus any of these reads as an attack on the person rather than
# a description of a feeling.
#
# Matched on word boundaries, not substrings. An earlier version looked for
# "you " with a trailing space and so missed "nobody else would put up with
# you" — real contempt, silently skipped, because the word ended the sentence.
_SECOND_PERSON_RE = re.compile(r"\b(you|your|you're|youre|yourself|u|ur)\b")

_NEGATIVE_WORDS = (
    "hate", "fault", "blame", "don't care", "dont care", "didn't even",
    "didnt even", "don't even", "dont even", "ruin", "ruined", "worst",
    "sick of", "fed up", "typical", "put up with", "can't stand", "cant stand",
    "problem is", "issue is", "always do", "never do",
)


def _needs_model(draft: str) -> bool:
    """Is this draft worth spending a completion on?"""
    text = draft.lower()
    second_person = bool(_SECOND_PERSON_RE.search(text))

    if _STRONG_RE.search(text):
        return True
    if second_person and _CONTEXTUAL_RE.search(text):
        return True
    if any(m in text for m in _CONTEMPT_PHRASES):
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
    # Exclamation marks alone are a poor signal — "I got the job!!!" is the
    # commonest form by far. Anger that reaches three of them almost always
    # also has a target or is shouting, both of which are caught above, so
    # require one of those rather than firing on punctuation by itself.
    if draft.count("!") >= 3 and second_person:
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
        if verdict.get("verdict") == "caution":
            # An observation, not a judgement, and free: the model call already
            # happened for another reason. Nothing about this may affect
            # whether the message goes.
            from apps.personalization import behaviour

            behaviour.note_caution(user)
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


_SHARP_MARKERS = (
    "you always",
    "you never",
    "whatever",
    "forget it",
    "i'm done",
    "im done",
    "don't care",
    "dont care",
)


def _sharp_before(relationship, before, window: timedelta) -> bool:
    """Was the exchange ending at `before` a sharp one?

    Cheap and keyword-based rather than a model call: this runs on an open and
    on every send, and paying for a completion to discover that nothing
    happened is the wrong trade.

    Anchored on a timestamp rather than on "now" because the two callers ask
    different questions. The nudge asks whether things went badly *recently*;
    the withdrawal signal asks whether the thing someone went quiet after was
    sharp, and that exchange is by definition older than the silence being
    measured. An implementation anchored only on now made the withdrawal check
    unsatisfiable — the gap had to exceed six hours and the sharpness had to
    fall inside the last six, so it could never fire.
    """
    recent = CoupleMessage.objects.filter(
        relationship=relationship,
        created_at__gte=before - window,
        created_at__lte=before,
        deleted_at__isnull=True,
    ).order_by("-created_at")[:20]
    return any(
        any(m in (msg.body or "").lower() for m in _SHARP_MARKERS) for msg in recent
    )


def _had_sharp_exchange(relationship) -> bool:
    """Was there a rupture in the last few hours?"""
    return _sharp_before(relationship, timezone.now(), timedelta(hours=6))


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


# ── 4. Reading something hard ───────────────────────────────────────────────
#
# The assist so far only helps you *send*. But escalation usually happens in the
# reaction, not the opening message — what turns a sharp start into a fight is
# how the other person answers. So this coaches the receiver, privately.
#
# Two rules make the difference between help and harm.
#
# It coaches you about *your own response* and never characterises your partner.
# An assistant that privately tells one partner the other is "being
# manipulative" has made itself an ally inside a two-person system — that is
# triangulation, and it damages the relationship while feeling supportive.
#
# It defers to safety. If the incoming message carries genuine abuse signals,
# "here is how to respond better" is the wrong answer entirely: it coaches
# someone into accommodating abuse. That case routes to support instead.

# Signals that this is not a communication problem to be smoothed over.
_ABUSE_SIGNALS = (
    "not allowed to", "won't let me", "wont let me", "if you leave",
    "i'll hurt", "ill hurt", "you'll regret", "youll regret", "nobody will believe",
    "no one will believe", "i'll take the kids", "ill take the kids",
    "check your phone", "who were you with",
)

_READ_COACH_SYSTEM = (
    "A partner has just received the message below and it may be hard to take. "
    "Give them one or two sentences of private, practical guidance on how to "
    "respond in a way that de-escalates and still lets them say what is true "
    "for them.\n"
    "Rules you must not break:\n"
    "- Coach the reader about their own response. Never diagnose, label or "
    "characterise the partner who sent it, and never take the reader's side.\n"
    "- Do not tell them to ignore it, swallow it, or that they are overreacting.\n"
    "- Plain, warm, specific. No therapy jargon.\n"
    "If the message does not actually need any of this, reply with exactly NONE."
)


def coach_response(relationship, user, incoming: str) -> dict:
    """Private guidance for the partner who just received a hard message.

    Returns ``{"guidance": str|None, "defer_to_support": bool}``. Only the
    receiver ever sees this; it is never surfaced to the sender.
    """
    blank = {"guidance": None, "defer_to_support": False}
    if not incoming.strip():
        return blank

    try:
        config = settings_for(relationship)
        if not config.assist_enabled:
            return blank

        lowered = incoming.lower()
        if any(signal in lowered for signal in _ABUSE_SIGNALS):
            # Not a communication problem. Do not coach accommodation.
            return {"guidance": None, "defer_to_support": True}

        # Same local gate as the send path: if the message is not actually
        # hard, there is nothing to coach and no call worth paying for.
        if not _needs_model(incoming):
            return blank

        context = _thread_context(relationship, limit=6)
        prompt = (
            f"Recent conversation:\n{context}\n\nThe message they just received:\n{incoming}"
            if context
            else f"The message they just received:\n{incoming}"
        )
        raw = _complete(_READ_COACH_SYSTEM, prompt, CHECK_TIMEOUT_SECONDS)
        if not raw or raw.strip().upper() == "NONE":
            return blank
        return {"guidance": raw.strip(), "defer_to_support": False}
    except Exception as exc:
        log.warning("chat_assist_read_coach_failed: %s", exc)
        return blank


# ── 4. Learning from what actually happens ──────────────────────────────────


def note_send_pattern(relationship, user, message) -> None:
    """Read one send for the two halves of the demand–withdraw pattern.

    Both signals come from timestamps and sender ids that are already in the
    row we just wrote — no model call, no extra latency, nothing the couple
    pays for. Called after the message is persisted and wrapped so it can never
    be the reason a send fails.

    The thresholds are deliberately generous. Calling a busy afternoon
    "withdrawal" produces guidance telling someone to tiptoe around a partner
    who was only in a meeting, and that is a worse error than noticing nothing.
    """
    try:
        from apps.personalization import behaviour

        previous = list(
            CoupleMessage.objects.filter(
                relationship=relationship, deleted_at__isnull=True
            )
            .exclude(id=message.id)
            .exclude(kind=CoupleMessage.KIND_SYSTEM)
            .order_by("-created_at")[: behaviour.PURSUIT_UNANSWERED_RUN]
        )

        # A repair sticker is the least ambiguous signal in the product: it is a
        # gesture whose only meaning is repair.
        if message.kind == CoupleMessage.KIND_STICKER and message.sticker.startswith(
            "repair."
        ):
            behaviour.note_repair(user)

        if not previous:
            return

        # Pursuit: a run of messages with nothing back in between. Two is a
        # person adding a thought; a run is the protest behaviour the pattern
        # is named for.
        if len(previous) >= behaviour.PURSUIT_UNANSWERED_RUN - 1 and all(
            m.sender_id == user.id for m in previous
        ):
            behaviour.observe(user, behaviour.PURSUES)
            return

        # Withdrawal: coming back to the thread long after the partner spoke,
        # and only when the exchange before it was actually sharp. Without that
        # second condition this would fire on every good night's sleep.
        last = previous[0]
        if last.sender_id and last.sender_id != user.id:
            gap = message.created_at - last.created_at
            # Sharpness is judged around the partner's last message, not
            # around now — that exchange is necessarily older than the silence.
            if gap >= behaviour.WITHDRAWAL_SILENCE and _sharp_before(
                relationship, last.created_at, timedelta(hours=6)
            ):
                behaviour.observe(user, behaviour.WITHDRAWS)
    except Exception:  # pragma: no cover - exercised by the failure test
        log.warning("behaviour_note_send_pattern_failed", exc_info=True)
