"""§3.1 — should stay quiet.

The highest-value group and the easiest to get wrong. An assistant that
comments during ordinary chat makes people stop typing honestly in front of
it, and nothing anywhere else asserts on silence: every existing test asks
whether something fired, none asks whether nothing did.

If this group fails, everything else in the suite is noise.
"""

from .runner import (
    Scenario,
    Turn,
    backdate_behaviour,
    bad_night,
    check,
    model_calls,
)

# The whole group asserts the same two absences on every turn, so they are
# scenario defaults rather than repeated on thirty turns.
#
# "No nudge" is deliberately *not* here. Asking /assist/nudge is not a passive
# read — it builds one, and on an ordinary thread that costs a model call every
# single time it is asked (see `stayed_quiet`). Asserting it per turn would
# have this suite paying twelve calls to prove a silence that is one question:
# after all of this, is there anything worth offering? No.
QUIET = {"caution": False, "coach": False}


def stayed_quiet(key):
    """End-of-conversation assertions shared by the whole group.

    Three things, in the order they would hurt: nothing was offered, nothing
    was inferred, and the whole exchange was cheap.
    """

    def body(couple):
        before = model_calls()
        offered = couple.nudge("a")
        check(
            f"{key}: nothing to offer after the whole conversation",
            offered is None,
            f"got {(offered or {}).get('kind')}: {(offered or {}).get('suggestion', '')[:60]}",
        )

        for who in ("a", "b"):
            observed = couple.tendencies(who)
            check(f"{key}: nothing inferred about {who}", not observed, str(observed))

        # The tiering in `_needs_model` exists so that ordinary chat costs
        # nothing. A conversation with no sharpness in it anywhere should not
        # be able to reach the model on the send path at all — and opening the
        # thread should not be able to either, more than once.
        check(
            f"{key}: opening a quiet thread costs at most one model call",
            model_calls() - before <= 1,
            f"{model_calls() - before} calls for one nudge fetch",
        )

    return body


# ── S1 — Logistics ──────────────────────────────────────────────────────────
# Twelve turns of ordinary life. This is the false-positive suite.

S1 = Scenario(
    "S1",
    "Logistics",
    note="twelve turns of ordinary life — nothing should happen at all",
    defaults=QUIET,
    turns=[
        Turn("a", "running 10 late"),
        Turn("b", "no worries, I'll put the oven on"),
        Turn("a", "can you grab milk on the way home"),
        Turn("b", "which one did you want, the blue top or the green"),
        Turn("a", "blue please"),
        Turn("b", "they only had the green so I got that"),
        Turn("a", "that's fine"),
        Turn("b", "do we need anything else while I'm here"),
        Turn("a", "bread if they have the seeded one"),
        Turn("b", "got it. bin day tomorrow?"),
        Turn("a", "yeah I'll put them out tonight"),
        Turn("b", "ok see you at 7"),
    ],
)


S1.body = stayed_quiet("S1")


# ── S2 — Warm banter ────────────────────────────────────────────────────────
# Affectionate sharpness between people who talk that way. §5 of the plan
# predicts this fails: the contempt heuristic has no concept of affection, and
# "you're the worst" is textbook second-person-plus-negative-word.

S2 = Scenario(
    "S2",
    "Warm banter",
    note="affectionate sharpness — predicted to fail on the contempt heuristic",
    defaults=QUIET,
    turns=[
        Turn("a", "I ate the last of your birthday cake"),
        Turn("b", "you're the worst 😂"),
        Turn("a", "I cannot believe you did that to me last night"),
        Turn("b", "stop it 😭"),
        Turn("a", "you're ridiculous and I'm telling everyone"),
        Turn("b", "I hate you so much right now 😂😂"),
    ],
)


# ── S3 — Disagreement without contempt ──────────────────────────────────────
# Real conflict, no contempt. The product is not there to stop people
# disagreeing, and a system that flags "I still think we should wait" has
# decided that having a different view is a communication defect.

S3 = Scenario(
    "S3",
    "Disagreement without contempt",
    note="real conflict, no contempt — disagreeing is not a defect",
    defaults=QUIET,
    turns=[
        Turn("a", "I don't think we should book the flights yet"),
        Turn("b", "I see it differently — the prices only go up from here"),
        Turn("a", "that is not how I remember it going last year"),
        Turn("b", "we waited and it cost us an extra three hundred"),
        Turn("a", "I still think we should wait until your rota is confirmed"),
        Turn("b", "I'd rather commit now and move things around if we have to"),
        Turn("a", "I'm not comfortable with that and I want to say so plainly"),
        Turn("b", "understood. let's talk about it properly at the weekend"),
    ],
)

S2.body = stayed_quiet("S2")
S3.body = stayed_quiet("S3")


# ── S4 — One bad night that resolves ────────────────────────────────────────

S4 = Scenario(
    "S4",
    "One bad night that resolves",
    note="a fortnight of distance during a bereavement must not define someone",
)


def _s4(couple):
    """A hard fortnight, then two normal weeks.

    The property under test is decay. Behaviour scores halve every three weeks
    specifically so that a rough patch moves the profile and then fades if it
    is not repeated. Without that, the system would carry a verdict on someone
    formed during the worst week of their life — and go on phrasing things to
    their partner around it long after it stopped being true.
    """
    # Five bad nights across five weeks — a genuinely hard patch, and enough
    # observations to clear the reporting threshold.
    for index in range(5):
        bad_night(couple, index, weeks_ago=5 - index)

    during = couple.tendencies("a")
    check(
        "S4: a hard fortnight does show up while it is happening",
        "withdraws_after_conflict" in during,
        str(during),
    )

    backdate_behaviour(couple, "a", days=180)
    faded = couple.tendencies("a")
    check(
        "S4: and has decayed below the reporting threshold six months on",
        "withdraws_after_conflict" not in faded,
        str(faded),
    )


S4.body = _s4


SCENARIOS = [S1, S2, S3, S4]
