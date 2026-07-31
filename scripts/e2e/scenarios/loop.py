"""§3.4 — the outcome loop.

Whether feedback given through one endpoint changes what a different endpoint
decides to offer. Unit tests can prove each half; only this can prove they
agree about the key they are stored under, which is precisely the bug found
this week — the caution calibration wrote `caution@morning` and read `caution`,
so it could never fire, and a hundred per cent of the unit suite was green.

S13 is the one that should pass trivially, and that is the point of it: there
is no escalation path by construction, and asserting it is how one does not get
added later.
"""

from .runner import (
    Scenario,
    backdate_policy,
    check,
    model_calls,
    repo_root,
    shell,
    shell_json,
)

# ── S11 — Caution overridden ────────────────────────────────────────────────

S11 = Scenario(
    "S11",
    "Caution overridden, then wanted again",
    note="regression cover for the write-here/read-there bucket mismatch",
)

SHARP = "you are pathetic and I don't know why I bother, this is typical you"


def _s11(couple):
    """A caution that is always overridden should stop, and then come back.

    Five overrides is roughly where the weights put the suppression threshold.
    The important part is not the number — it is that the number is reachable
    at all from the endpoint the client actually calls, which is what the
    bucket mismatch made false.

    Reports outcomes *without* a draft on purpose, which is the shape a client
    that has not shipped register reporting still sends. That path writes to
    the bare ``caution`` key and has to keep working: the mobile app does not
    call this endpoint at all yet, so it is the only shape in production.
    S19 covers the register-aware path.
    """
    first = couple.check_draft("a", SHARP, expect_caution=True)
    check(
        "S11: the draft cautions to begin with",
        first.get("verdict") == "caution",
        first.get("reason", ""),
    )

    for _ in range(5):
        code = couple.caution_outcome("a", "sent_anyway")
        if code != 200:
            check("S11: overrides record", False, f"status {code}")
            return

    check(
        "S11: five overrides suppress the caution",
        couple.suppressed("caution"),
        f"weights={couple.policy_weights()}",
    )

    # The same draft, through the endpoint the client calls. A different draft
    # would prove nothing: the verdict cache is keyed on the text, so this also
    # confirms suppression is checked before the cache rather than after.
    again = couple.check_draft("a", SHARP)
    check(
        "S11: and the same draft now goes through uncautioned",
        again.get("verdict") == "ok",
        f"verdict={again.get('verdict')}",
    )

    # Now they start taking the suggestion. The loop is allowed to quieten and
    # then to stop quietening; what it may never do is get louder than it
    # started, which S13 covers.
    for _ in range(8):
        couple.caution_outcome("a", "used_suggestion")

    check(
        "S11: eight acceptances bring it back",
        not couple.suppressed("caution"),
        f"weights={couple.policy_weights()}",
    )
    restored = couple.check_draft("a", SHARP, expect_caution=True)
    check(
        "S11: and the draft cautions again",
        restored.get("verdict") == "caution",
        f"verdict={restored.get('verdict')}",
    )

    # The other half of the same event, which was defined and never called
    # until the caution-outcome endpoint existed.
    check(
        "S11: accepting a rewrite is observed as a tendency",
        "accepts_rephrasing" in couple.tendencies("a"),
        str(couple.tendencies("a")),
    )


S11.body = _s11


# ── S12 — Nudge dismissed ───────────────────────────────────────────────────

S12 = Scenario(
    "S12",
    "Nudge dismissed at one hour",
    note="suppression is scoped to the kind and the window, and it expires",
)


def _stage_nudges(couple, kind, hour, count):
    """Create nudges as if they had been offered at ``hour``, and return ids.

    Written directly because the point under test is the feedback loop, not the
    conditions that produce a nudge — driving four real night nudges would need
    four separate days and the 20h cooldown makes that impossible in one run.
    The rows are identical to the ones ``nudge_for`` writes.
    """
    return shell_json(
        "import json;"
        "from datetime import timedelta;"
        "from django.utils import timezone;"
        "from apps.chat.models import AssistNudge;"
        "from apps.relationships.models import Relationship;"
        f"r=Relationship.objects.get(id='{couple.rel}');"
        f"u={couple.user_expr('a')};"
        "ids=[];"
        f"[ids.append(str(AssistNudge.objects.create(relationship=r,user=u,kind='{kind}',"
        "suggestion='say goodnight').id))"
        f" for _ in range({count})];"
        "now=timezone.localtime();"
        f"target=now.replace(hour={hour}, minute=0);"
        "AssistNudge.objects.filter(id__in=ids).update(created_at=target);"
        "print(json.dumps(ids))"
    )


def _s12(couple):
    """Four dismissals at one hour teach one lesson, not four.

    The bucket is deliberately coarse — kind plus a four-way time window — and
    the risk in coarse buckets runs both ways. Too fine and every lesson is a
    coincidence with a long name; too coarse and dismissing the goodnight
    message at 11pm silences the repair opening at breakfast.
    """
    hour = 22  # inside NIGHT_HOURS, and inside the "evening" bucket
    ids = _stage_nudges(couple, "night", hour, 4)
    check("S12: four night nudges staged at 22:00", len(ids) == 4, str(len(ids)))

    for nudge_id in ids:
        code = couple.nudge_feedback(nudge_id, "dismissed", "a")
        if code != 200:
            check("S12: dismissals record", False, f"status {code}")
            return

    check(
        "S12: the night nudge is suppressed in that window",
        couple.suppressed("nudge_night", {"hour": hour}),
        f"weights={couple.policy_weights()}",
    )
    check(
        "S12: but not in the morning",
        not couple.suppressed("nudge_night", {"hour": 8}),
        f"weights={couple.policy_weights()}",
    )
    check(
        "S12: and not the repair nudge, at any hour",
        not couple.suppressed("nudge_repair", {"hour": hour})
        and not couple.suppressed("nudge_repair", {"hour": 8}),
        f"weights={couple.policy_weights()}",
    )

    # A lesson learned in March should not still be silencing someone in June.
    # Ninety days is a little over four half-lives, so a score of -6 comes back
    # above the suppression threshold.
    backdate_policy(couple, days=90)
    check(
        "S12: ninety days later it has decayed and the nudge returns",
        not couple.suppressed("nudge_night", {"hour": hour}),
        f"weights={couple.policy_weights()}",
    )


S12.body = _s12


# ── S13 — Nothing escalates ─────────────────────────────────────────────────

S13 = Scenario(
    "S13",
    "Nothing escalates",
    note="the loop may quieten, never nag — asserted so nobody adds a path later",
)


def _s13(couple):
    """Twenty accepted nudges must not buy the system a louder voice.

    This should pass trivially, because there is no code that makes the system
    more insistent. That is exactly why it is worth an assertion: the invariant
    is currently held up by nobody having written the obvious feature, and
    "acceptance rate is high, try offering more" is a natural-sounding thing to
    add six months from now.
    """
    kinds_before = _nudge_kinds()
    ids = _stage_nudges(couple, "night", 22, 20)
    for nudge_id in ids:
        couple.nudge_feedback(nudge_id, "acted", "a")

    weights = couple.policy_weights()
    check(
        "S13: twenty acceptances are recorded",
        any(entry.get("count", 0) >= 20 for entry in weights.values()),
        str(weights),
    )

    # The only thing the policy is allowed to decide is whether to hold
    # something back. There is no "offer more often" and no cooldown the
    # feedback can shorten.
    check(
        "S13: nothing is suppressed, and nothing else changed either",
        not couple.suppressed("nudge_night", {"hour": 22}),
        str(weights),
    )
    check(
        "S13: the cooldown is a constant, not a function of the policy",
        _cooldown_hours() == 20,
        f"NUDGE_COOLDOWN={_cooldown_hours()}h",
    )
    check(
        "S13: no new nudge kind appeared",
        _nudge_kinds() == kinds_before,
        f"{kinds_before} -> {_nudge_kinds()}",
    )

    # And the one-directional rule, stated as the code states it: the policy
    # can only ever subtract.
    sites = policy_call_sites()
    check(
        "S13: only the two known callers consult the policy at all",
        set(sites) == POLICY_CALLERS,
        f"{sorted(set(sites) ^ POLICY_CALLERS)} unexpected"
        if set(sites) != POLICY_CALLERS
        else f"{sorted(sites)}",
    )

    # `score_for` returns a number, and a number can be compared in either
    # direction. Every caller outside outcomes.py must go through
    # `suppressed`, which is the one place the comparison lives and only ever
    # subtracts — reading the raw score elsewhere is how "they keep accepting,
    # try offering more" would get written without anyone noticing.
    raw = [
        f"{path}: {line}"
        for path, lines in sites.items()
        if path != "apps/personalization/outcomes.py"
        for line in lines
        if "score_for" in line
    ]
    check(
        "S13: nothing outside outcomes.py reads the raw score",
        not raw,
        "\n      ".join(raw),
    )


def _nudge_kinds():
    return shell(
        "from apps.chat.models import AssistNudge;"
        "print(sorted(k for k, _ in AssistNudge.KIND_CHOICES))"
    )


def _cooldown_hours():
    return int(
        shell(
            "from apps.chat import assist;"
            "print(int(assist.NUDGE_COOLDOWN.total_seconds() // 3600))"
        )
    )


#: Where the policy is allowed to be consulted from. Both are withholding
#: decisions: one holds a nudge back, the other stops the pre-send caution
#: interrupting. Pinned as a set rather than described in prose, so that a
#: third caller cannot appear without someone deciding it should.
POLICY_CALLERS = {
    "apps/chat/assist.py",
    "apps/personalization/outcomes.py",
}


def policy_call_sites():
    """Every non-test line outside ``outcomes.py`` that reads the policy.

    A structural check rather than a behavioural one, because the behaviour
    being asserted is the *absence* of a feature: no sequence of inputs can
    demonstrate that nothing anywhere ever escalates. What can be demonstrated
    is the blast radius — that the policy has two callers, both of which can
    only withhold — so an escalation could not be wired in without this
    turning red and a person looking at it.
    """
    import subprocess

    out = subprocess.run(
        [
            "grep", "-rn", "-e", "score_for", "-e", "suppressed(",
            "apps/", "--include=*.py",
        ],
        capture_output=True,
        text=True,
        cwd=f"{repo_root()}/backend-django",
    ).stdout
    sites = {}
    for line in out.splitlines():
        path, _, rest = line.split(":", 2)
        if "tests" in path or rest.strip().startswith(("#", "def ", '"')):
            continue
        sites.setdefault(path, []).append(rest.strip())
    return sites


S13.body = _s13


# ── S19 — Sharpness is couple-relative ──────────────────────────────────────

S19 = Scenario(
    "S19",
    "Calibrating what counts as sharp, per couple",
    note="a couple can teach it to stay out of their banter — and only that",
)

BANTER = "you're the worst 😂"
CONTEMPT = "you are pathetic and I don't know why I bother, this is typical you"


def _s19(couple):
    """Two people who talk to each other like that should be left to it.

    S2 is the case this exists for: a couple whose affection sounds sharp get
    cautioned mid-joke, and that is the false positive that makes them turn the
    feature off. One global threshold cannot be right for both them and a
    couple whose sharpness means it.

    The second half is what keeps this from being an off switch. Whatever a
    couple teaches it about their banter must not touch the cold sentence with
    a verdict in it — otherwise "we joke like this" becomes "stop watching",
    and the caution that mattered goes past with the rest.

    Note this does not rescue S2, and is not meant to: S2 fails on turn two of
    a brand-new couple, and there is no history to calibrate against yet. This
    is what happens *after* a couple has told us something.
    """
    # Deliberately does *not* assert that the banter cautions first. It used
    # to, and that made this scenario depend on the model's current opinion of
    # one joke — so the day the check prompt was fixed and banter stopped being
    # flagged, S19 went red without anything it tests having changed. What is
    # under test is the bucketing: where a lesson is filed, and what it reaches.
    # Whether the model needed the lesson today is S2's question.
    for _ in range(5):
        code = couple.caution_outcome("a", "sent_anyway", draft=BANTER)
        if code != 200:
            check("S19: overrides record", False, f"status {code}")
            return

    weights = couple.policy_weights()
    check(
        "S19: the lesson is filed under the register, not the whole couple",
        "caution@playful" in weights and "caution" not in weights,
        str(weights),
    )

    check(
        "S19: the playful register is now suppressed for this couple",
        couple.suppressed("caution", {"register": "playful"}),
        str(couple.policy_weights()),
    )

    # And it short-circuits before the model, which is the point: a couple who
    # have said "stop commenting on our jokes" should not go on paying for the
    # call that decides to say nothing.
    before = model_calls()
    quiet = couple.check_draft("a", BANTER)
    check(
        "S19: the same banter goes through without asking the model",
        quiet.get("verdict") == "ok" and model_calls() == before,
        f"verdict={quiet.get('verdict')}, {model_calls() - before} calls",
    )

    # A different joke they have never sent before, so this is the register
    # being learned rather than one string being remembered.
    before = model_calls()
    unseen = couple.check_draft("a", "I hate you so much right now 😂😂")
    check(
        "S19: including a joke they have never sent before",
        unseen.get("verdict") == "ok" and model_calls() == before,
        f"verdict={unseen.get('verdict')}, {model_calls() - before} calls",
    )

    # The half that stops this being a way to switch the feature off.
    still = couple.check_draft("a", CONTEMPT, expect_caution=True)
    check(
        "S19: contempt still cautions for the same couple",
        still.get("verdict") == "caution",
        still.get("reason") or "the calibration became an off switch",
    )
    check(
        "S19: nothing about their banter reached the plain register",
        not couple.suppressed("caution", {"register": "plain"}),
        str(couple.policy_weights()),
    )

    # And an emoji cannot be used to relabel the patterns the check exists for.
    for draft in (
        "you always do this and I'm sick of it 😂",
        "you are an idiot 😂",
        "I'm done, watch me 😂",
    ):
        check(
            f"S19: an emoji does not make {draft[:28]!r} playful",
            _register_of(draft) == "plain",
            f"register={_register_of(draft)}",
        )


def _register_of(draft):
    return shell(
        "from apps.chat import assist;"
        f"print(assist.register_of({draft!r}))"
    )


S19.body = _s19


SCENARIOS = [S11, S12, S13, S19]
