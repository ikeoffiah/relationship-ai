"""What someone actually does, as opposed to what they said about themselves.

The RSQ is a self-report, and self-reports are the weakest evidence we have.
People answer as the partner they mean to be, or the one they were last year,
or the one they think the questionnaire wants. That is not dishonesty, it is
just what self-report measures — and a product that only ever asks is stuck
with it.

So this watches instead. Every signal here comes from something the system was
already computing for another reason: a pre-send caution that fired, a repair
sticker sent, how long a reply took, whether a suggested rewrite was accepted.
No extra model calls, no extra latency, no extra cost per message. That
constraint is deliberate — a learning layer that made every send slower or
dearer would be paid for by the couple in the one place they notice.

Four rules this module exists to enforce:

1. **Tendencies, not diagnoses.** We record "goes quiet after something sharp",
   never "is avoidant". The observable is real; the label is a leap, and it is
   the leap that does damage when it is wrong.
2. **It decays.** A fortnight of withdrawal during a bereavement should not
   define someone six months later. Scores halve every three weeks, so the
   profile describes who a person is being lately.
3. **It never overrides the self-report, only qualifies it.** The RSQ answer
   stays exactly as the person gave it. This sits beside it.
4. **It is never shown to the partner.** Guidance derived from it can shape how
   Bliss phrases something *to* that person, which is the whole point. The
   scores themselves are readable only by the person they describe. There is no
   endpoint that returns anyone else's.
"""

from __future__ import annotations

import math
from datetime import timedelta

from django.utils import timezone

#: Time for an unreinforced signal to lose half its weight. Three weeks is
#: chosen to be shorter than a rough patch and longer than a bad night: one
#: hard week should move the profile and then fade if it is not repeated.
HALF_LIFE_DAYS = 21.0

#: How much evidence before a tendency is allowed to say anything. Below this
#: we have a coincidence, not a pattern, and acting on a coincidence is how a
#: personalisation feature ends up telling someone something untrue about
#: themselves.
MIN_OBSERVATIONS = 4

#: And how strong, on the decayed scale, before it is worth mentioning.
MIN_SCORE = 2.0

# ── The vocabulary ──────────────────────────────────────────────────────────
# Every entry is something observable in the product. If a signal cannot be
# derived from an event we already emit, it does not belong here — the point is
# to describe behaviour, not to infer feelings we have no evidence for.

WITHDRAWS = "withdraws_after_conflict"
PURSUES = "pursues_when_unanswered"
ESCALATES = "escalates_under_stress"
REPAIRS = "reaches_for_repair"
ACCEPTS_HELP = "accepts_rephrasing"

SIGNALS = (WITHDRAWS, PURSUES, ESCALATES, REPAIRS, ACCEPTS_HELP)

#: Guidance shown to *Bliss*, phrased as what to do rather than what someone is.
#: These strings end up inside a prompt describing the person being written to,
#: so they are instructions for tone, not descriptions of character.
GUIDANCE = {
    WITHDRAWS: (
        "tends to go quiet when things get sharp — a message that asks for an "
        "immediate answer will usually get silence; leave them a way back in"
    ),
    PURSUES: (
        "finds silence hard and will often send again rather than wait — a "
        "short 'I've seen this, I need a minute' lands better than nothing"
    ),
    ESCALATES: (
        "tends to get sharper rather than quieter under stress — keep it "
        "concrete and avoid anything that reads as a verdict on them"
    ),
    REPAIRS: (
        "reaches for repair readily — a small opening is usually enough for "
        "them to meet it"
    ),
    ACCEPTS_HELP: "is receptive to a suggested rewrite",
}


def _decayed(score: float, since, now) -> float:
    """Halve the score once per :data:`HALF_LIFE_DAYS` elapsed."""
    if since is None:
        return score
    days = max(0.0, (now - since).total_seconds() / 86400.0)
    return score * math.pow(0.5, days / HALF_LIFE_DAYS)


def observe(user, signal: str, weight: float = 1.0) -> None:
    """Record one observation. Never raises.

    Called from the chat path, so it is on the same request as somebody's
    message. Nothing here is allowed to be the reason a message fails to send —
    a lost observation costs a slightly staler profile, and that is not a price
    worth a failed send.
    """
    if signal not in SIGNALS:
        return
    try:
        from .models import BehaviourProfile

        now = timezone.now()
        profile, _ = BehaviourProfile.objects.get_or_create(user=user)
        entry = (profile.signals or {}).get(signal) or {}

        seen_at = entry.get("updated_at")
        if seen_at:
            seen_at = timezone.datetime.fromisoformat(seen_at)

        score = _decayed(float(entry.get("score", 0.0)), seen_at, now) + weight
        signals = dict(profile.signals or {})
        signals[signal] = {
            "score": round(score, 4),
            "count": int(entry.get("count", 0)) + 1,
            "updated_at": now.isoformat(),
        }
        profile.signals = signals
        profile.save(update_fields=["signals", "updated_at"])
    except Exception:  # pragma: no cover - exercised by the failure test
        import logging

        logging.getLogger(__name__).warning(
            "behaviour_observe_failed signal=%s", signal, exc_info=True
        )


def tendencies_for(user_id) -> list[str]:
    """The signals currently strong enough to be worth acting on.

    Returns signal keys, decayed to now. An empty list is the normal state for
    a new user and for anyone whose patterns have faded, and callers must treat
    it as "we do not know" rather than "nothing applies".
    """
    try:
        from .models import BehaviourProfile

        profile = BehaviourProfile.objects.filter(user_id=user_id).first()
    except Exception:
        return []
    if profile is None:
        return []

    now = timezone.now()
    strong = []
    for signal, entry in (profile.signals or {}).items():
        if signal not in SIGNALS:
            continue
        if int(entry.get("count", 0)) < MIN_OBSERVATIONS:
            continue
        seen_at = entry.get("updated_at")
        if seen_at:
            seen_at = timezone.datetime.fromisoformat(seen_at)
        if _decayed(float(entry.get("score", 0.0)), seen_at, now) >= MIN_SCORE:
            strong.append(signal)

    # WITHDRAWS and PURSUES are the two halves of the demand-withdraw pattern.
    # One person can genuinely do both in different moods, but reporting both
    # at once gives Bliss contradictory instructions ("leave them space" and
    # "answer them quickly"), so the stronger one wins.
    if WITHDRAWS in strong and PURSUES in strong:
        signals = profile.signals
        loser = (
            PURSUES
            if float(signals[WITHDRAWS].get("score", 0))
            >= float(signals[PURSUES].get("score", 0))
            else WITHDRAWS
        )
        strong.remove(loser)
    return strong


def guidance_for(user_id) -> list[str]:
    """Tendencies rendered as instructions about tone."""
    return [GUIDANCE[signal] for signal in tendencies_for(user_id) if signal in GUIDANCE]


#: The same tendencies, said back to the person they are about. Separate
#: strings from :data:`GUIDANCE` because the audience is different: GUIDANCE
#: instructs Bliss on tone, this is a person reading about themselves, and it
#: has to be recognisable rather than clinical. "Lately" is load-bearing in
#: every one of them — the scores decay, so a claim about someone's character
#: would be a claim the data does not support.
SELF_DESCRIPTION = {
    WITHDRAWS: "Lately, when things get sharp, you have tended to step back before coming back to it.",
    PURSUES: "Lately, when a message goes unanswered, you have tended to follow it up rather than wait.",
    ESCALATES: "Lately, Bliss has paused a few of your messages before you sent them.",
    REPAIRS: "Lately, you have been the one reaching for repair.",
    ACCEPTS_HELP: "You have been open to a suggested rewrite when Bliss offered one.",
}


# ── Deriving signals from events the product already emits ──────────────────

#: A reply this long after something sharp reads as withdrawal rather than as
#: someone simply being at work. Deliberately generous — the cost of calling a
#: busy afternoon "withdrawal" is guidance that tells a partner to tiptoe around
#: someone who was only in a meeting.
WITHDRAWAL_SILENCE = timedelta(hours=6)

#: Several messages in a row with no reply in between. Two is a person adding a
#: thought; this many is the protest behaviour the pattern is named for.
PURSUIT_UNANSWERED_RUN = 3


def note_caution(user) -> None:
    """A pre-send check asked them to reconsider, and it was about sharpness."""
    observe(user, ESCALATES)


def note_rephrase_accepted(user) -> None:
    observe(user, ACCEPTS_HELP)


def note_repair(user) -> None:
    """A repair sticker, or an apology the check recognised."""
    observe(user, REPAIRS, weight=1.5)
