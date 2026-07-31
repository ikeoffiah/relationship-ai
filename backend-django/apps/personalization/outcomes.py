"""Whether the help helped.

The system already offers things — a pre-send caution, a rewrite, a nudge — and
until now had no way of finding out whether any of it landed. This is that
loop, and it is deliberately not the other thing it could have been.

**The unit of learning is the intervention, not the person.** Inferring harder
about who someone is makes a system more confident rather than more correct:
once it decides somebody is avoidant, every silence confirms it, and there is
no ground truth to arrest the drift. Whether a nudge was acted on is
supervised, per-couple, and cannot turn into a diagnosis because it never makes
one.

Two disciplines carried over from ``behaviour.py``, for the same reasons:

*Nothing here costs a model call.* Every signal comes from something the
product was already computing. A learning layer that made a send slower or
dearer would be paid for by the couple in the one place they notice.

*The policy is one row per couple, not a log.* ``InterventionEvent`` records
that a kind of help was offered in a kind of moment — never what was said. A
per-message record of two people's conversation is a much larger promise than
this feature is worth, and it would then exist, and be subpoenable.

See ``docs/outcome-loop.md``.
"""

from __future__ import annotations

import logging
import math

from django.utils import timezone

from .behaviour import HALF_LIFE_DAYS, MIN_OBSERVATIONS

log = logging.getLogger(__name__)

#: Below this, a couple has told us something. Above it, they have told us
#: nothing yet and the defaults stand. Shared with `behaviour` on purpose: the
#: threshold for "this is a pattern rather than a coincidence" is the same
#: question in both places.
MIN_SIGNALS = MIN_OBSERVATIONS

#: How negative a weight has to get before an intervention is suppressed.
#: Roughly four dismissals with no acceptances, allowing for decay.
SUPPRESS_BELOW = -3.0

#: What each response is worth. Declining is weighted harder than accepting is
#: rewarded: an unwanted nudge costs more than a wanted one gains, because it
#: teaches people to ignore the thing that will one day matter.
WEIGHTS = {
    "accepted": 1.0,
    "modified": 0.5,
    "declined": -1.5,
    "ignored": -0.5,
}


def _decayed(score: float, since, now) -> float:
    """Halve the score once per :data:`HALF_LIFE_DAYS` elapsed."""
    if since is None:
        return score
    days = max(0.0, (now - since).total_seconds() / 86400.0)
    return score * math.pow(0.5, days / HALF_LIFE_DAYS)


def bucket(kind: str, context: dict | None) -> str:
    """The key a lesson is stored under.

    Coarse on purpose. "Do not send the night nudge at 23:00 to this couple" is
    a lesson worth learning; "do not send it at 23:04 on a Tuesday when they
    have exchanged eleven messages" is a coincidence with a long name. Every
    extra dimension divides the evidence, and there is not much of it.
    """
    hour = (context or {}).get("hour")
    if hour is None:
        return kind
    if 5 <= hour < 12:
        window = "morning"
    elif 12 <= hour < 18:
        window = "afternoon"
    elif 18 <= hour < 23:
        window = "evening"
    else:
        window = "night"
    return f"{kind}@{window}"


def record(relationship, kind: str, context: dict | None, response: str) -> None:
    """Fold one outcome into the couple's policy.

    Never raises. This is bookkeeping about help that has already been given or
    withheld; a failure here must not be why anything else breaks.
    """
    if response not in WEIGHTS:
        return
    try:
        from .models import CouplePolicy

        policy, _ = CouplePolicy.objects.get_or_create(relationship=relationship)
        now = timezone.now()
        key = bucket(kind, context)

        entry = policy.weights.get(key) or {}
        previous = float(entry.get("score", 0.0))
        since = entry.get("updated_at")
        if isinstance(since, str):
            from django.utils.dateparse import parse_datetime

            since = parse_datetime(since)

        policy.weights[key] = {
            "score": _decayed(previous, since, now) + WEIGHTS[response],
            "count": int(entry.get("count", 0)) + 1,
            "updated_at": now.isoformat(),
        }
        policy.save(update_fields=["weights", "updated_at"])
    except Exception:
        log.warning("outcome_record_failed relationship=%s", relationship, exc_info=True)


def score_for(relationship_id, kind: str, context: dict | None = None) -> float:
    """How this couple has received this kind of help, lately. 0.0 if unknown."""
    try:
        from .models import CouplePolicy
        from django.utils.dateparse import parse_datetime

        policy = CouplePolicy.objects.filter(relationship_id=relationship_id).first()
        if policy is None:
            return 0.0
        entry = policy.weights.get(bucket(kind, context))
        if not entry or int(entry.get("count", 0)) < MIN_SIGNALS:
            return 0.0
        since = entry.get("updated_at")
        if isinstance(since, str):
            since = parse_datetime(since)
        return _decayed(float(entry.get("score", 0.0)), since, timezone.now())
    except Exception:
        log.warning("outcome_score_failed relationship=%s", relationship_id, exc_info=True)
        return 0.0


def suppressed(relationship_id, kind: str, context: dict | None = None) -> bool:
    """Whether to hold this one back.

    The first thing the loop is allowed to change, and on its own probably
    worth the build. A nudge nobody wants is worse than no nudge: it is how a
    couple learns to swipe past the assist without reading it, and then the one
    that would have mattered goes past too.

    Deliberately one-directional. A couple who ignore the night nudge stop
    getting it; nothing here makes the system *more* insistent with anyone,
    because "they keep dismissing it, try harder" is the behaviour of a nag.
    """
    return score_for(relationship_id, kind, context) <= SUPPRESS_BELOW
