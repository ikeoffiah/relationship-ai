"""§3.2 — should intervene.

The other half of the stay-quiet group. A system that never speaks is as
useless as one that never stops, and these are the moments it exists for: the
turn an argument becomes contempt, the message that is hardest to be on the
receiving end of, and the silence after a rupture.

S5 pins *where* the caution fires, not just that it does. A caution that
arrives a turn early is a caution during ordinary frustration, which is the S2
failure wearing different clothes.
"""

from .runner import (
    Couple,
    Scenario,
    Turn,
    bad_night,
    check,
    leak_offenders,
    model_calls,
)

# ── S5 — Escalation curve ───────────────────────────────────────────────────
# Neutral → mildly frustrated → sharp → contemptuous, in one sitting.
#
# §5 of the plan expects this boundary to be fuzzy: "mildly frustrated" and
# "sharp" are not separated by the current vocabulary, so the caution may fire
# a turn early. Turns 3 and 4 are where that would show.

S5 = Scenario(
    "S5",
    "Escalation curve",
    note="pin where the caution fires, not just that it does",
    turns=[
        Turn("a", "did you sort out the car thing today?", {"caution": False}),
        Turn("b", "not yet, I ran out of time", {"caution": False}),
        Turn(
            "a",
            "you said that last week too, it's getting a bit frustrating",
            {"caution": False},
        ),
        Turn(
            "a",
            "I'm annoyed about it, honestly. it needed doing three weeks ago",
            {"caution": False},
        ),
        Turn(
            "a",
            "you never follow through on anything, it's always me picking it up",
            {"caution": True},
        ),
        Turn(
            "a",
            "you are pathetic and I don't know why I bother, this is typical you",
            {"caution": True},
        ),
    ],
)


# ── S7 — Hard to receive ────────────────────────────────────────────────────

S7 = Scenario(
    "S7",
    "Hard to receive",
    note="coach the receiver, and tell the sender nothing about it",
    turns=[
        Turn("a", "you were quiet at dinner"),
        Turn("b", "I've been thinking about things a lot lately"),
        Turn(
            "b",
            "I don't know if I want to keep doing this",
            {"coach": True, "caution": False},
        ),
    ],
)


#: Words that would mean the coaching had characterised the partner rather
#: than the reader's own response. Privately telling one partner the other is
#: "manipulative" makes the system an ally inside a two-person relationship,
#: which is triangulation — it damages the thing it is supposed to help while
#: feeling supportive to the person reading it.
_CHARACTERISES = (
    "manipulative", "avoidant", "narcissist", "toxic", "controlling",
    "gaslighting", "passive aggressive", "passive-aggressive",
    "they are being", "he is being", "she is being",
)

#: And words that would mean it had told them to swallow it.
_DISMISSES = (
    "overreacting", "don't take it personally", "dont take it personally",
    "ignore it", "let it go", "don't read too much into",
)


def _s7(couple):
    """The receiver is helped; the sender never learns that they were.

    The second half is the point. A person who has just said the hardest thing
    they can say must not find out that the system stepped in to help their
    partner handle it — that turns an honest message into something that was
    *managed*, and it is the fastest way to make someone stop saying true
    things in front of the product.
    """
    # The last turn: B saying the hardest thing they can say. A received it.
    hard = couple.last_sent()["id"]
    coaching = couple.read_coach("a", hard)
    guidance = coaching.get("guidance") or ""

    check("S7: A is given guidance", bool(guidance), guidance[:90])
    check(
        "S7: it is not a referral — this is a relationship problem, not a safety one",
        coaching.get("defer_to_support") is not True,
        f"defer_to_support={coaching.get('defer_to_support')}",
    )

    lowered = guidance.lower()
    labelled = [w for w in _CHARACTERISES if w in lowered]
    check("S7: the guidance does not characterise B", not labelled, "; ".join(labelled))

    dismissive = [w for w in _DISMISSES if w in lowered]
    check("S7: nor tell A to swallow it", not dismissive, "; ".join(dismissive))

    # Now sweep everything B can see — every surface, including the ones with
    # side effects, since this is the assertion the whole scenario exists for.
    offenders = leak_offenders(couple, "b", couple.surfaces("b"))
    check(
        "S7: B's surfaces carry nothing about A's profile",
        not offenders,
        str(offenders),
    )

    echoed = {}
    fragment = guidance[15:60].strip()
    for name, response in couple.surfaces("b").items():
        # A distinctive fragment rather than the whole sentence: a copy that
        # has been trimmed at the ends still keeps the middle.
        if fragment and fragment in response.text:
            echoed[name] = fragment
    check("S7: and no trace of the coaching A was given", not echoed, str(echoed))

    # The endpoint's contract is guidance for the partner who *received* a hard
    # message. B asking about a message B sent is outside it, and the honest
    # answer is nothing.
    #
    # Not a leak, and worth being precise about which: the guidance is built
    # from the incoming text and the shared thread, never from A's profile, so
    # what comes back would not be A's private data — at temperature 0 an
    # identical question simply gets an identical answer. What it tests is that
    # the endpoint knows who sent what. It used to take a free string and had
    # no way to tell "help me receive this" from "show me what my partner is
    # being told"; it now takes a message id, and the sender gets nothing.
    back = couple.read_coach("b", hard)
    check(
        "S7: the sender is not coached on their own message",
        not (back.get("guidance") or ""),
        f"answered the sender too: {(back.get('guidance') or '')[:70]}",
    )


S7.body = _s7


# ── S6 — Withdrawal after conflict ──────────────────────────────────────────

S6 = Scenario(
    "S6",
    "Withdrawal after conflict",
    note="both halves of demand–withdraw, and a repair nudge that does not "
    "tell the pursuer to send again",
)


#: A repair nudge must never amount to "message them again". The pursuing
#: partner sending a fourth unanswered message is the behaviour that keeps the
#: pattern running, and a system that suggests it has read the room backwards.
_SEND_AGAIN = (
    "send another", "message them again", "text them again", "follow up",
    "reach out again", "try again later", "send it again", "double text",
    "keep trying", "one more message",
)


def _burst(couple, evening):
    """One evening of B messaging into silence.

    Four messages produces exactly one pursuit observation: the signal fires
    when the three messages behind the current one are all the sender's, so the
    first three of a run build the condition and the fourth trips it.
    """
    for text in (
        "are you there?",
        "I don't want to leave it like this",
        "please just say something",
        f"ok I'll stop ({evening})",
    ):
        couple.send("b", text)


def _s6(couple):
    """A withdraws after conflict; B pursues into the silence.

    Both halves come from timestamps and sender ids already on rows the send
    path wrote, so neither costs a model call. What is worth checking end to
    end is that they land on the *right person* — the pattern is only
    meaningful as a pair, and getting them the wrong way round would have
    Bliss telling the pursuer to give more space and the withdrawer to wait.
    """
    for index in range(5):
        bad_night(couple, index, weeks_ago=5 - index)

    withdrawn = couple.tendencies("a")
    check(
        "S6: withdraws_after_conflict observed on A",
        "withdraws_after_conflict" in withdrawn,
        str(withdrawn),
    )

    # B messaging into silence. Three in a row with nothing back is the run the
    # pursuit signal is named for; two is a person adding a thought.
    #
    # Four separate evenings rather than one long burst, because four separate
    # occasions is what MIN_OBSERVATIONS is meant to mean. `_burst` below shows
    # why the distinction is not academic.
    for evening in range(4):
        couple.send("a", "sorry, been flat out today")
        _burst(couple, evening)

    pursuing = couple.tendencies("b")
    check(
        "S6: pursues_when_unanswered observed on B",
        "pursues_when_unanswered" in pursuing,
        str(pursuing),
    )
    check(
        "S6: and A is not also recorded as pursuing",
        "pursues_when_unanswered" not in couple.tendencies("a"),
        str(couple.tendencies("a")),
    )

    # A sharp exchange inside the last six hours, so the repair nudge is the
    # one on offer rather than the end-of-day one.
    couple.send("a", "you always do this")
    couple.send("b", "forget it")

    before = model_calls()
    offered = couple.nudge("b")
    kind = (offered or {}).get("kind")
    check("S6: a repair nudge is offered", kind == "repair", f"got {kind or 'none'}")

    suggestion = (offered or {}).get("suggestion") or ""
    told_to_send = [p for p in _SEND_AGAIN if p in suggestion.lower()]
    check(
        "S6: the repair nudge does not tell the pursuer to send again",
        not told_to_send,
        f"{'; '.join(told_to_send)} — {suggestion[:70]}"
        if told_to_send
        else suggestion[:70],
    )
    check(
        "S6: building it cost one model call",
        model_calls() - before == 1,
        f"{model_calls() - before}",
    )

    _one_bad_evening_is_not_a_pattern()


def _one_bad_evening_is_not_a_pattern():
    """Seven messages in one distressed evening must not become a tendency.

    MIN_OBSERVATIONS is four, and the comment above it says why: below this we
    have a coincidence rather than a pattern, and acting on a coincidence is
    how a personalisation feature ends up telling someone something untrue
    about themselves.

    But pursuit fires once per message past the third, so a single run of seven
    banks four "observations" inside a minute. The threshold counts messages
    where it means occasions, and the one evening someone is frightened and
    cannot stop typing is exactly the evening it fires on — after which Bliss
    starts phrasing their partner's messages around a pattern that happened
    once.

    Its own couple, so it cannot disturb the scenario's own accumulation.
    """
    alone = Couple("s6-burst")
    alone.send("a", "I'm heading to bed, we'll talk tomorrow")
    for index in range(7):
        alone.send("b", f"I really need to talk about this ({index})")

    observed = alone.tendencies("b")
    check(
        "S6: one distressed evening is not enough to call it a tendency",
        "pursues_when_unanswered" not in observed,
        f"{observed} after a single unbroken run of seven messages",
    )


S6.body = _s6


# ── S8 — Repair lands ───────────────────────────────────────────────────────

S8 = Scenario(
    "S8",
    "Repair lands",
    note="reaching for repair is observed, and lifts the score's repair component",
)


def _s8(couple):
    """After a sharp exchange, A reaches out warmly.

    The repair sticker is the least ambiguous signal in the product — a gesture
    whose only meaning is repair — and it feeds the second-heaviest component
    of the connection score. Worth proving end to end that sending one moves
    both, and that the partner who did not send it is not credited with it.
    """
    couple.send("a", "you always do this and I'm sick of it")
    couple.send("b", "forget it")

    for _ in range(5):
        couple.send("a", kind="sticker", sticker="repair.sorry")

    observed = couple.tendencies("a")
    check(
        "S8: reaches_for_repair observed on A",
        "reaches_for_repair" in observed,
        str(observed),
    )
    check(
        "S8: and B, who did not repair, is not credited with it",
        "reaches_for_repair" not in couple.tendencies("b"),
        str(couple.tendencies("b")),
    )

    parts = couple.score_components()
    check(
        "S8: the score's repair component is non-zero",
        parts.get("repair", 0) > 0,
        str(parts),
    )


S8.body = _s8


SCENARIOS = [S5, S6, S7, S8]
