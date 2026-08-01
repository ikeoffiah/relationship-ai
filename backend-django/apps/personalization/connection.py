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

Five properties it is built to have:

**Mutual, not busy.** The heaviest component is reciprocity. A relationship
where one person does all the reaching should not score well no matter how hard
that person works — that imbalance is the finding, not something to paper over
with a high number.

**Able to fall.** A number that can only rise or hold while a relationship
deteriorates is reassurance rather than a reading, and nobody believes a
motivator that never goes down. Two things lower it: a partner withdrawing,
through reciprocity, and arguments that go unmended, through repair. Neither is
a penalty for fighting — see below.

**Conflict is subtracted from connection, never added as a penalty.** An
argument is a burst of messages from both partners, which is exactly the shape
reciprocity rewards, so this used to produce a couple's *highest* reading during
their worst week — a number saying the opposite of the truth, which is worse
than one saying nothing. Now a fight simply does not count as connection: it
neither raises the score nor lowers it, and what is left is what the fortnight
looked like apart from the fight. Rupture detection is eight keyword phrases,
and a penalty built on that would be telling couples their relationship got
worse on the strength of a string match. Failing to notice a fight costs
nothing; inventing one is not recoverable.

**Slow.** A behaviour-derived score has maybe eight genuinely distinguishable
states; rendering that as /100 invites people to read a three-point wobble as a
verdict on their Tuesday. It is smoothed in proportion to elapsed time, so its
inertia is a property of the week rather than of how often the job ran.

**Quiet when it is low, and absent when it is unknown.** ``presentation``
returns how prominent the number should be, and the answer on a bad week is
"not very". The morning after a fight, someone opening the app for help should
be met with something useful, not a low number. And a couple who stopped doing
anything at all are shown nothing rather than the last number that was true —
absence lowers what we know, not what they scored.

---

**The attributability rule.** Both partners see the same number, so anything
that moves it is something they can both point at. That is only safe because
of a property the whole design already has: *every input is something both
partners watched happen.* Messages, check-ins happening, gratitude, completed
actions, arguments, repairs.

The rule that follows is not "the score must not be attributable" — it plainly
is; if one partner goes quiet, reciprocity falls and both of them know whose
silence it was. The rule is:

    The score may only move on things both partners already know.

It tells them nothing they could not have observed. That is why a private
check-in value can never be a component — it would move the number on something
only one of them knows, which is the same leak by arithmetic that
``boundary.py`` prevents by rule. It is also why an inferred tendency is not a
component: a tendency is the system's opinion, not an event either of them saw.
"""

from __future__ import annotations

import logging
import math
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


#: Sharp messages closer together than this belong to the same argument. One
#: row on a Tuesday evening is one rupture, not nine.
RUPTURE_GAP = timedelta(hours=6)

#: How long after a rupture a repair still counts as belonging to it. Three
#: days because couples sleep on things, and a repair on Thursday for a fight
#: on Tuesday is still a repair.
REPAIR_WINDOW = timedelta(days=3)

#: The exchange around a sharp message that is part of the argument rather
#: than part of the relationship.
RUPTURE_PAD = timedelta(hours=1)

#: Below this many ruptures in a fortnight, the repair balance stays at 1.0.
#:
#: This is the whole confidence story, and it is structural rather than a knob.
#: Rupture detection is eight keyword phrases; a single false positive must not
#: be able to move anybody's score, so it takes two independent detections
#: *and* an absence of any repair before the component falls at all. Failing to
#: notice a fight costs nothing; inventing one and telling a couple their
#: relationship got worse is not recoverable.
MIN_RUPTURES = 2


def _ratio(part: float, whole: float) -> float:
    return 0.0 if whole <= 0 else max(0.0, min(1.0, part / whole))


def _ruptures(messages) -> list[tuple]:
    """The arguments in this window, as (start, end) spans.

    Sharp messages are clustered rather than counted: a row is one rupture
    however many times somebody said "forget it" during it, and counting each
    utterance would make a long argument look like a failing fortnight.
    """
    from apps.chat.assist import is_sharp, message_text

    spans: list[list] = []
    for message in messages:
        if not is_sharp(message_text(message)):
            continue
        if spans and message.created_at - spans[-1][1] <= RUPTURE_GAP:
            spans[-1][1] = message.created_at
        else:
            spans.append([message.created_at, message.created_at])
    return [(start, end) for start, end in spans]


def _was_repaired(rupture, next_rupture, messages, gestures) -> bool:
    """Whether this argument was mended before the window closed.

    Two ways, and the second matters more than it looks. An explicit gesture —
    a repair sticker, a repair moment — is unambiguous but rare; most couples
    repair by talking normally again. So a rupture also counts as repaired when
    both partners came back to the thread and nothing sharp was said. That is
    what "it blew over" looks like in data, and Gottman's repair attempts are
    mostly mundane bids rather than ceremonies.

    Deliberately generous. Everything here fails toward *repaired*, because a
    missed repair means telling a couple who did mend it that they did not.
    """
    from apps.chat.assist import is_sharp, message_text

    _, end = rupture
    deadline = end + REPAIR_WINDOW
    # Only up to the next argument. If they fought again on Thursday, Thursday
    # is not evidence about Tuesday, and letting it be would mark a run of
    # patched-up rows as one long unrepaired one.
    if next_rupture is not None:
        deadline = min(deadline, next_rupture[0])

    if any(end < when <= deadline for when in gestures):
        return True

    after = [m for m in messages if end < m.created_at <= deadline]
    if not after:
        return False
    if any(is_sharp(message_text(m)) for m in after):
        return False
    return len({m.sender_id for m in after if m.sender_id}) >= 2


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
    #
    # An argument does not count toward it. It used to: a fight is a burst of
    # messages from both partners, which is exactly the shape reciprocity
    # rewards, so a couple's worst week produced their highest reading of the
    # month. That is not a number failing to notice something — it is a number
    # saying the opposite of the truth, which is worse than saying nothing.
    #
    # So conflict is subtracted from *connection*, not added to a penalty. A
    # fight neither raises the score nor lowers it; what is left is what the
    # fortnight looked like apart from the fight.
    rows = list(
        CoupleMessage.objects.filter(
            relationship=relationship, created_at__gte=since, deleted_at__isnull=True
        )
        .select_related("media")
        .order_by("created_at")
    )
    ruptures = _ruptures(rows)

    def in_conflict(message):
        return any(
            start - RUPTURE_PAD <= message.created_at <= end + RUPTURE_PAD
            for start, end in ruptures
        )

    # Counted toward the evidence even so. "Were they fighting" is something we
    # know about them, and dropping it from `events` would let a couple who did
    # nothing but argue fall under MIN_EVENTS and be shown *nothing* — quietly
    # hiding the one reading that mattered.
    events += len(rows)

    calm = [m for m in rows if not in_conflict(m)]
    counts = {p: 0 for p in partners}
    for message in calm:
        if message.sender_id in counts:
            counts[message.sender_id] += 1
    total_messages = sum(counts.values())
    mutuality = (
        _ratio(min(counts.values()), total_messages / 2.0) if total_messages else 0.0
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
    # whether repair lands. This used to score 1.0 for any repair at all —
    # which meant it scored identically whether or not there had been anything
    # to repair, and a fortnight with three unmended rows read exactly like a
    # calm one. The predictor was cited and then not implemented.
    #
    # It is a balance now: of the arguments they had, how many did they mend.
    # No arguments detected means nothing to answer, so it stays at 1.0 — the
    # component only falls on evidence of rupture *and* absence of repair, and
    # that conjunction is what makes it safe to build on a thin detector.
    #
    # It is also the one component that can fall for a reason other than
    # absence, which is what stops the number being unable to say a
    # relationship is going badly. It is not attributable to either partner: a
    # rupture is between them and repair can come from either.
    from .behaviour import MIN_OBSERVATIONS, REPAIRS, tendencies_for

    reaches_for_repair = sum(1 for p in partners if REPAIRS in tendencies_for(p))

    repair = None
    if len(ruptures) >= MIN_RUPTURES:
        gestures = [
            m.created_at
            for m in rows
            if m.kind == CoupleMessage.KIND_STICKER
            and (m.sticker or "").startswith("repair.")
        ]
        gestures += list(
            GratitudeMoment.objects.filter(
                relationship=relationship, created_at__gte=since, kind="repair"
            ).values_list("created_at", flat=True)
        )
        mended = sum(
            1
            for index, rupture in enumerate(ruptures)
            if _was_repaired(
                rupture,
                ruptures[index + 1] if index + 1 < len(ruptures) else None,
                rows,
                gestures,
            )
        )
        repair = _ratio(mended, len(ruptures))

    # Repair counts toward the evidence as well as toward the score. A
    # tendency has already cleared its own threshold to be reported at all, so
    # there are at least MIN_OBSERVATIONS behind each one — and a component
    # that can move the number while contributing nothing to "do we know
    # enough to show a number" was an inconsistency waiting to produce a
    # confident score from almost nothing, or refuse one from plenty.
    events += reaches_for_repair * MIN_OBSERVATIONS

    parts = {
        "mutuality": mutuality,
        "presence": presence,
        "warmth": warmth,
        "effort": effort,
    }
    # Omitted rather than defaulted when there is nothing to judge. Scoring it
    # 1.0 would hand every calm couple a fifth of the score for never having
    # had a row, and scoring it 0.0 would mark them down for it. Neither is a
    # statement about them, so `compute` renormalises over what is left and the
    # question simply is not asked.
    if repair is not None:
        parts["repair"] = repair

    return parts, events


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

    applicable = {key: weight for key, weight in WEIGHTS.items() if key in parts}
    total = sum(applicable.values())
    if not total:
        return None
    return round(
        100 * sum(parts[key] * weight for key, weight in applicable.items()) / total
    )


def update(relationship) -> int | None:
    """Fold today's reading into the stored score. Returns the stored value.

    Smoothed and deadbanded, so the number on the home screen moves when
    something changed and sits still when it did not.
    """
    from .models import ConnectionScore

    raw = compute(relationship)

    if raw is None:
        # Not enough happened in a fortnight to say anything — so say nothing,
        # rather than keeping the last number that was true.
        #
        # This used to return here and leave the stored value alone, which
        # meant a couple who stopped using the product entirely did not score
        # low; they froze at their best reading and kept it indefinitely.
        # Measured: an active fortnight scored 68, ten days of total silence
        # still showed 68. That is the single most flattering thing this
        # number could do, in exactly the case where flattery is least
        # affordable.
        #
        # `hidden` already means "not enough to say", and a couple who stopped
        # are in the same position as a couple who never started. Absence
        # lowers what we know, not what they scored — the distinction the
        # whole design rests on.
        #
        # The series is kept. It is their history, and it is what lets the
        # trend still read honestly if they come back.
        try:
            row = ConnectionScore.objects.filter(relationship=relationship).first()
            if row is not None and row.value is not None:
                row.value = None
                row.save(update_fields=["value", "updated_at"])
                log.info("connection_gone_quiet relationship=%s", relationship.id)
        except Exception:
            log.warning(
                "connection_clear_failed relationship=%s", relationship.id, exc_info=True
            )
        return None

    try:
        row, _ = ConnectionScore.objects.get_or_create(relationship=relationship)
        if row.value is None:
            smoothed = float(raw)
        else:
            # Smoothed in proportion to the time that has passed, not to the
            # number of times this has run.
            #
            # SMOOTHING is what turns a jittery measurement into something
            # worth putting on a home screen, and that only holds if the steps
            # are days. Folded in twice in an afternoon the old form moved the
            # number twice as far, so its inertia was a property of scheduler
            # behaviour rather than of the relationship. One nightly job made
            # that invisible; a manual refresh, a retry, or a second worker
            # would have made it visible in the worst way — as a number that
            # lurched for no reason the couple could see.
            #
            # Exactly equivalent at one day (0.85 and 0.15, as before), does
            # nothing at all when no time has passed, and catches up correctly
            # after a missed run instead of pretending the gap did not happen.
            elapsed_days = 0.0
            if row.updated_at:
                elapsed_days = max(
                    0.0, (timezone.now() - row.updated_at).total_seconds() / 86400.0
                )
            weight = 1.0 - math.pow(SMOOTHING, elapsed_days)
            smoothed = row.value + weight * (raw - row.value)
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
