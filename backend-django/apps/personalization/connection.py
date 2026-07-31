"""One number for how the relationship is going.

Out of 100, updated daily, shown on the home screen — and built from what the
two of them *did*, never from what either of them privately said.

That distinction is the whole design, and it is not a nicety. The daily
check-in asks each partner how connected they feel, privately. Averaging those
two answers into a shared number would publish one partner's answer to the
other by arithmetic: on a 1–5 scale, someone who rated 5 and then sees a couple
score of 3 has learned exactly what their partner put. There is no coarsening
that fixes that and still leaves a number worth watching.

So this reads behaviour instead — showing up, repairing, thanking, doing the
thing you both said you would. Both partners saw all of it happen. Nobody
learns anything private about anybody, and the score ends up measuring effort,
which is the thing a couple can actually change on a bad week.

Three properties it is built to have:

**Mutual, not busy.** The heaviest component is reciprocity. A relationship
where one person does all the reaching should not score well no matter how hard
that person works — that imbalance is the finding, not something to paper over
with a high number.

**Slow.** A behaviour-derived score has maybe eight genuinely distinguishable
states; rendering that as /100 invites people to read a three-point wobble as a
verdict on their Tuesday. It is smoothed, and it will not move at all unless
something real changed.

**Quiet when it is low.** ``presentation`` returns how prominent the number
should be, and the answer on a bad week is "not very". The morning after a
fight, someone opening the app for help should be met with something useful,
not a low number. The score is still there; it is just not the headline.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone

log = logging.getLogger(__name__)

#: The window everything is measured over. Long enough that one quiet weekend
#: does not register, short enough to be about now rather than about March.
WINDOW_DAYS = 14

#: How much of the previous value survives an update. High on purpose: this is
#: what turns a jittery measurement into something worth putting on a home
#: screen, and what stops a single good day reading as a transformation.
SMOOTHING = 0.85

#: A recomputed value must differ by at least this much to be stored. Without a
#: deadband the number would tick by a point most days and teach couples to
#: read noise as signal.
DEADBAND = 2.0

#: Below this many contributing events, there is nothing to say. A couple who
#: joined on Tuesday must not be shown 18/100 because they have not had time to
#: do anything.
MIN_EVENTS = 6

#: How many weekly points to keep for the trend. Bounded so this stays one row
#: per couple rather than becoming a dated record of when they struggled.
SERIES_LENGTH = 12

#: Where the number stops being a reward and starts being a judgement. Below
#: this the home screen leads with help instead.
QUIET_BELOW = 45


def _ratio(part: float, whole: float) -> float:
    return 0.0 if whole <= 0 else max(0.0, min(1.0, part / whole))


def _components(relationship, since) -> tuple[dict[str, float], int]:
    """The parts of the score, each 0..1, and how much evidence there was.

    Everything here is a count of something both partners could see happen.
    Nothing reads a check-in *value*, a private note, or a message body.
    """
    from apps.chat.models import CoupleMessage
    from apps.engagement.models import GratitudeMoment, MicroActionLog, RelationshipCheckIn

    partners = [relationship.partner_a_id, relationship.partner_b_id]
    partners = [p for p in partners if p]
    events = 0

    def by_partner(queryset, field="user_id"):
        counts = {p: 0 for p in partners}
        for row in queryset.values_list(field, flat=True):
            if row in counts:
                counts[row] += 1
        return counts

    # ── Mutual presence ─────────────────────────────────────────────────
    # Both people turning up, measured as the smaller share rather than the
    # total. Two hundred messages from one partner and none from the other is
    # not a connected fortnight.
    messages = by_partner(
        CoupleMessage.objects.filter(
            relationship=relationship, created_at__gte=since, deleted_at__isnull=True
        ),
        "sender_id",
    )
    events += sum(messages.values())
    total_messages = sum(messages.values())
    mutuality = (
        _ratio(min(messages.values()), total_messages / 2.0) if total_messages else 0.0
    )

    # ── Showing up ──────────────────────────────────────────────────────
    # Whether the check-in happened, never what it said.
    check_ins = by_partner(
        RelationshipCheckIn.objects.filter(relationship=relationship, created_at__gte=since)
    )
    events += sum(check_ins.values())
    presence = _ratio(min(check_ins.values()) if check_ins else 0, WINDOW_DAYS * 0.5)

    # ── Warmth ──────────────────────────────────────────────────────────
    gratitude = GratitudeMoment.objects.filter(
        relationship=relationship, created_at__gte=since
    ).count()
    events += gratitude
    warmth = _ratio(gratitude, WINDOW_DAYS / 3.0)

    # ── Shared effort ───────────────────────────────────────────────────
    # Completed only. An action that was assigned and not done is not effort,
    # and counting it would let the score rise for showing up to be told what
    # to do.
    actions = MicroActionLog.objects.filter(
        relationship=relationship, created_at__gte=since, completed=True
    ).count()
    events += actions
    effort = _ratio(actions, WINDOW_DAYS / 2.0)

    # ── Repair ──────────────────────────────────────────────────────────
    # Gottman's strongest single predictor is not whether couples fight, it is
    # whether repair lands. Weighted accordingly, and generously: any repair at
    # all in a fortnight is worth most of this component.
    from .behaviour import REPAIRS, tendencies_for

    repairs = sum(1 for p in partners if REPAIRS in tendencies_for(p))
    repair = _ratio(repairs, 1.0)

    return (
        {
            "mutuality": mutuality,
            "presence": presence,
            "warmth": warmth,
            "effort": effort,
            "repair": repair,
        },
        events,
    )


#: Reciprocity carries the most weight, and repair is next. The rest is
#: participation. Deliberately biased toward the positives — a score that
#: mostly counts friction would find friction, and Gottman's ratio says a
#: healthy relationship is five parts warmth to one part conflict.
WEIGHTS = {
    "mutuality": 0.35,
    "repair": 0.20,
    "presence": 0.20,
    "warmth": 0.15,
    "effort": 0.10,
}


def compute(relationship) -> int | None:
    """Today's raw score, 0–100, or None if there is not enough to say."""
    since = timezone.now() - timedelta(days=WINDOW_DAYS)
    try:
        parts, events = _components(relationship, since)
    except Exception:
        log.warning("connection_compute_failed relationship=%s", relationship.id, exc_info=True)
        return None

    if events < MIN_EVENTS:
        return None
    return round(100 * sum(parts[key] * weight for key, weight in WEIGHTS.items()))


def update(relationship) -> int | None:
    """Fold today's reading into the stored score. Returns the stored value.

    Smoothed and deadbanded, so the number on the home screen moves when
    something changed and sits still when it did not.
    """
    from .models import ConnectionScore

    raw = compute(relationship)
    if raw is None:
        return None

    try:
        row, _ = ConnectionScore.objects.get_or_create(relationship=relationship)
        if row.value is None:
            smoothed = float(raw)
        else:
            smoothed = SMOOTHING * row.value + (1 - SMOOTHING) * raw
            if abs(smoothed - row.value) < DEADBAND:
                return int(round(row.value))

        row.value = smoothed
        # One point per week, bounded. Enough for a trend line, not enough to
        # be a dated record of a couple's bad month.
        week = timezone.now().strftime("%Y-W%W")
        series = [p for p in (row.series or []) if p.get("week") != week]
        series.append({"week": week, "value": int(round(smoothed))})
        row.series = series[-SERIES_LENGTH:]
        row.save(update_fields=["value", "series", "updated_at"])
        return int(round(smoothed))
    except Exception:
        log.warning("connection_update_failed relationship=%s", relationship.id, exc_info=True)
        return None


def presentation(relationship_id) -> dict:
    """The score and how loudly to say it.

    ``emphasis`` is the part that matters. The home screen leads with the
    number when things are going well, and leads with something useful when
    they are not — the morning after a fight, a low number is the least helpful
    thing that could be on the screen, and the app is supposed to be coaching
    rather than grading.

    ``direction`` is weekly, never daily. A daily delta is noise carrying
    emotional weight.
    """
    from .models import ConnectionScore

    row = ConnectionScore.objects.filter(relationship_id=relationship_id).first()
    if row is None or row.value is None:
        # Nothing to show yet, and no placeholder either: "—/100" reads as a
        # zero to anyone who is already anxious about it.
        return {"score": None, "emphasis": "hidden", "direction": None, "series": []}

    value = int(round(row.value))
    series = row.series or []
    direction = None
    if len(series) >= 2:
        change = series[-1]["value"] - series[-2]["value"]
        direction = "up" if change >= DEADBAND else "down" if change <= -DEADBAND else "steady"

    return {
        "score": value,
        "emphasis": "quiet" if value < QUIET_BELOW else "feature",
        "direction": direction,
        "series": series,
    }
