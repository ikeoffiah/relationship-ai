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


# Every completion this module makes, counted. The scenario suite reads it
# before and after a conversation to report what that conversation cost.
#
# Worth the four lines because the failure it catches is silent: the tiering in
# `_needs_model` is the difference between one call per conversation and one
# call per message, and if a future edit widens the gate nothing breaks, no
# test goes red, and the only symptom is a bill. Counting attempts rather than
# successes on purpose — a call that times out was still made, and the latency
# was still paid by someone holding a finished message.
_CALLS_KEY = "assist:model_calls"


def _count_call() -> None:
    try:
        cache.incr(_CALLS_KEY)
    except ValueError:
        # incr refuses to create a key. A racing worker may have created it in
        # between, which costs this one call off the tally and nothing else.
        cache.set(_CALLS_KEY, 1, None)
    except Exception:
        pass


def model_calls() -> int:
    """How many completions have been attempted since the counter was reset."""
    try:
        return int(cache.get(_CALLS_KEY) or 0)
    except Exception:
        return 0


def reset_model_calls() -> None:
    cache.set(_CALLS_KEY, 0, None)


def _complete(
    system: str, user: str, timeout: float, model: str | None = None, max_tokens: int = 220
) -> str | None:
    """One short completion. Returns None on any failure — never raises."""
    if not os.environ.get("OPENAI_API_KEY"):
        return None
    _count_call()
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

    notes = []

    try:
        from apps.personalization.models import UserProfile

        profile = UserProfile.objects.filter(user_id=partner_id).first()
    except Exception:
        profile = None

    if profile is not None:
        if getattr(profile, "attachment_style", ""):
            notes.append(f"attachment style: {profile.attachment_style}")
        if getattr(profile, "communication_style_preference", ""):
            notes.append(
                f"prefers {profile.communication_style_preference} communication"
            )

    # What they actually do, alongside what they said about themselves. This
    # qualifies the self-report rather than replacing it: the RSQ answer stays
    # exactly as they gave it, and this sits next to it. Phrased as tone
    # instructions, never as a label — "tends to go quiet when things get
    # sharp", not "avoidant", because the observable is evidence and the label
    # is a leap.
    #
    # Gathered whether or not there is a self-report to sit beside. Returning
    # early on a missing UserProfile used to drop the observed tendencies
    # entirely, which inverted the point of watching in the first place: the
    # behaviour layer exists *because* self-report is the weakest evidence, and
    # it was only being consulted for people who had filled in the
    # questionnaire.
    try:
        from apps.personalization import boundary

        notes.extend(boundary.phrasing_guidance_for(partner_id))
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

# Three things in here are answers to observed failures rather than general
# good practice, and are worth keeping when this is next edited.
#
# "The normal answer is ok" — the previous version described what to flag and
# left the majority case implicit, and a model with a REASON and a SUGGESTION
# field to fill has an incentive to find something to put in them.
#
# The affection paragraph — the vocabulary had no concept of a couple who tease
# each other, so "you're the worst 😂" was textbook second-person-plus-negative
# -word and nothing said otherwise.
#
# The line about a reason that argues against its own verdict — because that is
# exactly what it did. Twice it returned `VERDICT: caution` alongside "not
# necessarily contemptuous" and "Expresses strong emotion but not outright
# contempt or threats".
_CHECK_SYSTEM = (
    "You review a message one partner is about to send the other and decide "
    "whether it is likely to wound rather than land.\n"
    "\n"
    "Almost every message you see is fine. The normal answer is ok, and "
    "answering ok is the job done, not a failure to be useful.\n"
    "\n"
    "Flag it ONLY for contempt, name-calling, sweeping accusations "
    "('you always', 'you never'), threats, or hitting a known sore spot.\n"
    "\n"
    "Never flags:\n"
    "- Ordinary bluntness, disagreement, frustration and sadness. People are "
    "allowed to be upset with each other.\n"
    "- Affection that sounds sharp. Couples tease, exaggerate and insult each "
    "other fondly — 'you're the worst', 'I hate you so much right now', "
    "'you're ridiculous' — and emoji, laughter, or a running joke in the "
    "conversation above are the sign of it. Flag what someone would still be "
    "hurt by tomorrow, not what they are laughing at now.\n"
    "\n"
    "Judge what will happen, not what could. Almost any sentence *could* be "
    "taken badly by someone. A reason that begins 'could be' or 'might be', or "
    "that concedes the joke and flags it anyway, is a reason to answer ok.\n"
    "\n"
    "Read the conversation above before deciding. A sharp line inside an "
    "exchange that is plainly playful is part of the play. The same words after "
    "a run of cold ones are not.\n"
    "\n"
    "If you find yourself writing a reason that argues against your own "
    "verdict, the verdict is ok.\n"
    "\n"
    "Worked examples. Deliberately not the phrasings you are most likely to "
    "see — the point is the line between them, not the words:\n"
    "  'you are such a menace 😄' -> ok. A fond insult.\n"
    "  'I could genuinely kill you for that lol' -> ok. Hyperbole, not a threat.\n"
    "  'I am furious about this and I want to talk about it tonight' -> ok. "
    "Anger, plainly stated, aimed at the thing rather than the person.\n"
    "  'you never think about anyone but yourself' -> caution. A verdict on "
    "who they are, not what they did.\n"
    "\n"
    "Reply in one of exactly these two formats and nothing else.\n"
    "\n"
    "When it is fine — this line alone, with nothing after it:\n"
    "VERDICT: ok\n"
    "\n"
    "When it is not:\n"
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


# ── Register: what kind of sharpness this is ────────────────────────────────
#
# Sharpness is couple-relative. "You're the worst 😂" between two people who
# talk that way is affection; between others it is contempt. One global
# threshold cannot be right for both, and the couple it is wrong for turns the
# feature off.
#
# So the caution calibrates per *register* rather than per couple as a whole.
# A couple who override the caution on playful messages five times stop being
# cautioned on playful messages — and still get cautioned on a cold sentence
# with an "always" in it, because that is a different bucket.
#
# Deliberately local and free, like everything else the learning layer reads.
# And deliberately coarse: two registers, because every extra dimension divides
# already-thin evidence, and "do not interrupt this couple when they are
# joking" is a lesson worth learning where "do not interrupt them on a Tuesday
# when they have used two emoji" is a coincidence with a long name.

REGISTER_PLAYFUL = "playful"
REGISTER_PLAIN = "plain"

_PLAYFUL_TEXT = (
    "lol", "lmao", "haha", "hehe", "xd", ":)", ":-)", ":d", ";)", "😂", "🤣",
)

# The emoji planes, plus the older symbol blocks most keyboards still emit.
_EMOJI_RE = re.compile("[\U0001f300-\U0001faff☀-➿⬀-⯿]")


def register_of(draft: str) -> str:
    """Whether this draft is playing or not.

    The disqualifiers matter more than the markers. Name-calling, threats and
    sweeping accusations are never playful *whatever is sitting next to them* —
    an emoji after "you always do this" does not make it a joke, and allowing
    it to would let a couple calibrate away the exact patterns the check exists
    for. This is what bounds the blast radius: the worst a couple can teach the
    system is to stop commenting on their banter.
    """
    text = draft.lower()

    if _STRONG_RE.search(text):
        return REGISTER_PLAIN
    if any(marker in text for marker in _THREAT_MARKERS):
        return REGISTER_PLAIN
    if any(marker in text for marker in _ABSOLUTE_MARKERS) and _SECOND_PERSON_RE.search(text):
        return REGISTER_PLAIN

    if _EMOJI_RE.search(draft) or any(marker in text for marker in _PLAYFUL_TEXT):
        return REGISTER_PLAYFUL
    return REGISTER_PLAIN


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


def _caution_is_wanted(relationship, register: str | None = None) -> bool:
    """Whether this couple still reads the pre-send caution, in this register.

    A caution that is overridden every single time is not a caution, it is
    friction with a moral tone — and each override spends a little of the
    credibility the one that matters will need. So it stops, on the same
    one-directional rule as the nudges: it can quieten, never escalate.

    Both buckets are read, and that is not belt-and-braces. Outcomes recorded
    before registers existed live under the bare ``caution`` key, and outcomes
    recorded by a client that does not send the draft still do. Reading only
    the register-specific key would be the write-here/read-there bug that took
    this loop out once already — the calibration would silently never fire for
    anyone who had taught it something before today. Old lessons keep applying;
    new ones apply more narrowly.

    Deliberately about *tone* cautions only. Safety signals are a different
    layer with a different escalation path, and nothing here touches them —
    which is also what stops this being a way to switch off the thing that
    matters: the most a couple can teach it is to stop commenting on banter.
    """
    try:
        from apps.personalization import outcomes

        if outcomes.suppressed(relationship.id, "caution"):
            return False
        if register and outcomes.suppressed(
            relationship.id, "caution", {"register": register}
        ):
            return False
        return True
    except Exception:
        # Not knowing means carry on as before.
        return True


def check_before_send(relationship, user, draft: str) -> dict:
    """Should this message give the sender pause?

    Returns ``{"verdict": "ok"|"caution", "reason": str, "suggestion": str}``.
    Anything unexpected resolves to ``ok`` — see the fail-open rule above.
    """
    blank = {"verdict": "ok", "reason": "", "suggestion": ""}
    if not draft.strip():
        return blank
    if not _caution_is_wanted(relationship, register_of(draft)):
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
    recent = (
        CoupleMessage.objects.filter(
            relationship=relationship,
            created_at__gte=before - window,
            created_at__lte=before,
            deleted_at__isnull=True,
        )
        .select_related("media")
        .order_by("-created_at")[:20]
    )
    # Through `message_text`, not `body`. A voice note's words live on its
    # media row, so reading `body` here made every spoken rupture invisible to
    # this scan: no repair opening after an argument that happened out loud,
    # and no withdrawal signal either, since that is gated on this same
    # function. Voice is exactly where the loaded messages go, so the blind
    # spot sat precisely where it did the most damage — which is the same
    # sentence transcription.py opens with, about the bug this one survived.
    return any(
        any(m in message_text(msg).lower() for m in _SHARP_MARKERS) for msg in recent
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
        nudge = _nudge_for(relationship, user, local_hour)
        if nudge is None:
            return None

        # What this couple has told us by dismissing things. A nudge nobody
        # wants is worse than no nudge: it is how someone learns to swipe past
        # the assist without reading it, and then the one that would have
        # mattered goes past too.
        #
        # Checked after the nudge is built rather than before, so suppression
        # is decided against the kind that would actually have been offered.
        # The row is still written — it is the daily budget's record, and a
        # suppressed offer is itself worth knowing about.
        from apps.personalization import outcomes

        if outcomes.suppressed(
            relationship.id, f"nudge_{nudge.kind}", {"hour": local_hour}
        ):
            log.info(
                "nudge_suppressed relationship=%s kind=%s", relationship.id, nudge.kind
            )
            return None
        return nudge
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
#
# Grouped by the part of the pattern they belong to, because the gaps were in
# whole groups rather than scattered. The list used to be threats, isolation
# and discrediting only — so a message reading "I went through your phone last
# night" produced nothing at all: no referral, and no coaching either, since
# it does not look sharp to the gate below. The right outcome by accident.
#
# What is deliberately NOT here is monitoring pressure — "why did it take you
# two hours to answer me", and the "who were you with" that was already in the
# list. Those are ordinary relationship friction at least as often as they are
# control, and there is no phrasing that separates the two. Everything below
# has few innocent readings.
#
# Matched as substrings against the message someone *received*, so these are
# in the voice of the person who typed it.
_ABUSE_SIGNALS = (
    # threats
    "if you leave", "i'll hurt", "ill hurt", "you'll regret", "youll regret",
    "i'll take the kids", "ill take the kids",
    # isolation and discrediting
    "not allowed to", "won't let me", "wont let me",
    "nobody will believe", "no one will believe",
    "who were you with",
    # surveillance. "check your phone" used to stand here alone and is nobody's
    # sentence — it looked like coverage and caught nothing. These are what
    # people actually write.
    "give me your phone", "let me see your phone", "unlock your phone",
    "through your phone", "read your messages", "see your messages",
    "your location on", "track your location", "where you are at all times",
    # control of movement and appearance
    "not going out dressed", "you're not going out", "youre not going out",
    "not wearing that",
    # financial control
    "control the money", "i decide what we spend", "hand over your wages",
    # enforced secrecy
    "if you tell anyone", "don't tell anyone about this",
    "dont tell anyone about this",
)

# Leads with the decision rather than the assumption. The previous version
# opened "a partner has just received the message below and it may be hard to
# take", which answers the question it was supposed to ask, and left NONE as an
# afterthought in the last line. It duly coached the receiver of "you're the
# worst 😂" on handling being hurt.
_READ_COACH_SYSTEM = (
    "A partner has just received the message below. Decide whether it needs "
    "help being received.\n"
    "\n"
    "It does when the message carries real distance or hurt — someone saying "
    "they are done trying, unsure whether they want to keep going, tired of "
    "having the same argument, or alone in it. Those are the hardest things to "
    "be on the end of and they are the reason this exists. Help with those.\n"
    "\n"
    "It does not when the two of them are joking. Teasing, exaggeration and "
    "fond insults are how many couples talk, and the conversation above will "
    "usually show it. Telling someone their partner may have hurt them, when "
    "their partner was playing, does the harm the message itself did not. "
    "Reply with exactly NONE.\n"
    "\n"
    "When it does need help, give one or two sentences of private, practical "
    "guidance on "
    "how to respond in a way that de-escalates and still lets them say what is "
    "true for them.\n"
    "Rules you must not break:\n"
    "- Coach the reader about their own response. Never diagnose, label or "
    "characterise the partner who sent it, and never take the reader's side.\n"
    "- Do not tell them to ignore it, swallow it, or that they are overreacting.\n"
    "- Plain, warm, specific. No therapy jargon.\n"
    "\n"
    "Reply in one of exactly these two formats and nothing else.\n"
    "\n"
    "When it needs nothing — this line alone:\n"
    "NEEDED: no\n"
    "\n"
    "When it does:\n"
    "NEEDED: yes\n"
    "GUIDANCE: <the one or two sentences>"
)


def _parse_coaching(raw: str | None) -> str | None:
    """The guidance in a reply, or None if it declined to offer any.

    A labelled field rather than a bare sentinel, for the same reason the
    pre-send check uses one. Asking for the word NONE works right up until the
    model declines *in prose* — "This seems playful and teasing, so no help is
    needed here" — at which point a refusal to comment is rendered to somebody
    as comment. That is the exact failure this layer is supposed to avoid, and
    the sentinel could not see it coming.

    The old sentinel is still honoured: a model that answers NONE is
    understood, and so is one that ignores the format and simply answers.
    """
    text = (raw or "").strip()
    if not text or text.upper().startswith("NONE"):
        return None

    needed, parts = None, []
    for line in (line.strip() for line in text.splitlines()):
        if not line:
            continue
        lowered = line.lower()
        if lowered.startswith("needed:"):
            needed = "yes" in lowered
        elif lowered.startswith("guidance:"):
            parts.append(line.split(":", 1)[1].strip())
        elif parts:
            parts.append(line)

    if needed is False:
        return None

    guidance = " ".join(part for part in parts if part).strip()
    # A model that ignored the format and answered anyway is taken at its word,
    # which is what happened before this function existed.
    return (guidance or text) or None


#: Messages that are hard to *receive*, which is a different question from the
#: one `_needs_model` answers.
#:
#: The send-side gate looks for contempt — blame, absolutes, second person —
#: because it asks "will this wound whoever reads it". Reusing it here asked
#: the wrong question: it fired on "you always do this", which is unpleasant
#: but survivable, and stayed silent on "I don't know if I want to keep doing
#: this", which is the hardest thing a partner can open. The two vocabularies
#: barely overlap, so read-coaching was loudest exactly where it mattered least.
#:
#: Distance and withdrawal, not sharpness. Deliberately specific phrases: "I
#: don't know" on its own is someone choosing a restaurant.
_HARD_TO_RECEIVE = (
    "keep doing this",
    "take a break",
    "i'm done", "im done",
    "given up", "give up on",
    "stopped expecting",
    "alone in this",
    "nothing ever changes", "nothing changes",
    "can't do this anymore", "cant do this anymore",
    "tired of trying",
    "not sure this is working",
    "don't know if i want", "dont know if i want",
)


def _needs_read_coaching(incoming: str) -> bool:
    """Whether a received message is worth offering the reader help with.

    Sharpness still counts — being on the end of contempt is hard. But so does
    withdrawal, which the sharpness gate cannot see at all.

    Deliberately excludes hopelessness that reads as being about the person
    rather than the relationship. "What's the point" is not a message to coach
    a warm reply to; that belongs to the safety layer, which has its own path
    and its own escalation.
    """
    lowered = incoming.lower()

    # Withdrawal first, and unconditionally. "I don't know if I want to keep
    # doing this 😞" carries an emoji and is still the hardest thing a partner
    # can open with; nothing below may talk this out of firing.
    if any(marker in lowered for marker in _HARD_TO_RECEIVE):
        return True

    # Playful sharpness is not hard to receive, it is how these two talk. The
    # send-side gate cannot tell the difference — it asks "will this wound
    # whoever reads it", and "you're the worst 😂" is second person plus a
    # negative word either way — so read-coaching inherited that mistake and
    # privately told someone their partner might have hurt them when their
    # partner was joking. Worse than the caution it came from: the caution
    # interrupts you, this one reinterprets your relationship for you.
    #
    # `register_of` refuses to call name-calling, threats or absolutes playful,
    # so this cannot silence coaching on anything the vocabulary knows is
    # sharp. It can be fooled by contempt the vocabulary is missing — but that
    # is the same gap on the send path, and safety does not run through here:
    # `_ABUSE_SIGNALS` is checked before this function is reached.
    if register_of(incoming) == REGISTER_PLAYFUL:
        return False

    return _needs_model(incoming)


def no_coaching() -> dict:
    """The "nothing to say" reply, which is most of what read-coaching returns.

    A fresh dict each call rather than a module constant: it goes out as a
    response body, and a shared one would be a mutable global.
    """
    return {"guidance": None, "defer_to_support": False}


def coach_response(relationship, user, incoming: str) -> dict:
    """Private guidance for the partner who just received a hard message.

    Returns ``{"guidance": str|None, "defer_to_support": bool}``. Only the
    receiver ever sees this; it is never surfaced to the sender. The caller is
    responsible for establishing that ``incoming`` is a message this user
    received — see :func:`apps.chat.views.assist_read_coach`.
    """
    blank = no_coaching()
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

        if not _needs_read_coaching(incoming):
            return blank

        context = _thread_context(relationship, limit=6)
        prompt = (
            f"Recent conversation:\n{context}\n\nThe message they just received:\n{incoming}"
            if context
            else f"The message they just received:\n{incoming}"
        )
        guidance = _parse_coaching(_complete(_READ_COACH_SYSTEM, prompt, CHECK_TIMEOUT_SECONDS))
        if not guidance:
            return blank
        return {"guidance": guidance, "defer_to_support": False}
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
        #
        # Observed once per episode, when the run *reaches* the threshold —
        # not on every message after it. The previous version re-fired on each
        # further message, so a single unbroken run of seven banked four
        # observations inside a minute, against a MIN_OBSERVATIONS of four
        # whose whole purpose is to distinguish a pattern from a coincidence.
        # The threshold was counting messages where it means occasions, and
        # the evening it fired on was the one where somebody was frightened
        # and could not stop typing — after which Bliss would phrase their
        # partner's messages around a pattern that happened once.
        #
        # Counting the consecutive run also settles an off-by-one: the old
        # condition fired on the third message of a run at the start of a
        # thread but the fourth mid-thread, because mid-thread the partner's
        # message was still inside the window it examined. PURSUIT_UNANSWERED_RUN
        # is 3 and its comment says three in a row is the behaviour, so three
        # in a row is what this now means, wherever it happens.
        run = 0
        for earlier in previous:
            if earlier.sender_id != user.id:
                break
            run += 1
        if run >= behaviour.PURSUIT_UNANSWERED_RUN - 1:
            if run == behaviour.PURSUIT_UNANSWERED_RUN - 1:
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
