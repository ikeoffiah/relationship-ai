"""The machinery a scenario is written against.

A scenario is a list of turns and a list of expectations, replayed against the
live stack with a fresh couple so nothing bleeds between them.

**Assert on decisions, not prose.** Model text is not stable enough to pin: the
same draft phrased two ways will produce two different rewrites, both fine, and
a suite that pins the words fails on the day someone improves the prompt. So
the assertions are ``verdict == "caution"``, whether guidance exists, which
nudge kind fired. Where the text itself matters — a rewrite must not put words
in someone's mouth — :func:`rewrite_faults` asserts properties of it instead.
"""

import json
import pathlib
import sys
import time
from collections import namedtuple

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from harness import (  # noqa: E402
    DJANGO,
    auth,
    check,
    pair,
    register,
    shell,
    shell_json,
    stamp,
)

#: ``who`` is "a" or "b". ``expect`` is a dict of assertions evaluated after
#: that turn lands; any key may be omitted, and an omitted key asserts nothing.
#:
#:   caution:          True | False    — /assist/check on this text before sending
#:   coach:            True | False    — /assist/read-coach for the *other* partner
#:   defer_to_support: True | False
#:   nudge:            "repair" | "night" | "opportunity" | None
#:   tendency:         signal name observed on `who` by now
#:   no_leak:          True            — partner's surfaces clean (default: always on)
Turn = namedtuple("Turn", "who text expect")
Turn.__new__.__defaults__ = ({},)


# The vocabulary that must never appear on a surface the other partner reads.
# Kept here rather than imported so the assertion does not depend on the module
# it is checking: if someone renames a signal, this suite should notice the
# rename rather than follow it.
PROFILE_VOCABULARY = (
    "withdraws_after_conflict",
    "pursues_when_unanswered",
    "escalates_under_stress",
    "reaches_for_repair",
    "accepts_rephrasing",
)


class Couple:
    """Two registered, paired users and the endpoints between them.

    A fresh one per scenario. Accumulation is most of what these scenarios
    measure — tendencies, suppression, the connection score are all functions
    of history — so a couple reused across two scenarios would carry the first
    one's history into the second's assertions.
    """

    def __init__(self, tag: str):
        self.tag = tag
        self.stamp = stamp()
        self.emails = {
            "a": f"s-{tag}-a-{self.stamp}@test.local",
            "b": f"s-{tag}-b-{self.stamp}@test.local",
        }
        self.tokens = {who: register(email) for who, email in self.emails.items()}
        self.rel = pair(self.emails["a"], self.emails["b"])
        self.base = f"{DJANGO}/api/v1/chat/{self.rel}"

    # ── identities ──────────────────────────────────────────────────────

    def other(self, who: str) -> str:
        return "b" if who == "a" else "a"

    def headers(self, who: str) -> dict:
        return auth(self.tokens[who])

    def user_expr(self, who: str) -> str:
        """A Django shell expression resolving to this partner's user row."""
        return (
            "__import__('django.contrib.auth', fromlist=['x'])"
            f".get_user_model().objects.get(email='{self.emails[who]}')"
        )

    # ── the endpoints under test ────────────────────────────────────────

    def send(self, who: str, text: str = "", **extra) -> dict:
        body = {"body": text, "client_id": stamp()}
        body.update(extra)
        r = requests.post(
            f"{self.base}/messages/send", headers=self.headers(who), json=body, timeout=30
        )
        return r.json() if r.content else {}

    def check_draft(self, who: str, text: str) -> dict:
        return requests.post(
            f"{self.base}/assist/check",
            headers=self.headers(who),
            json={"draft": text},
            timeout=30,
        ).json()

    def read_coach(self, who: str, incoming: str) -> dict:
        """What the system offers ``who`` about a message they just received."""
        return requests.post(
            f"{self.base}/assist/read-coach",
            headers=self.headers(who),
            json={"message": incoming},
            timeout=30,
        ).json()

    def rephrase(self, who: str, draft: str) -> dict:
        return requests.post(
            f"{self.base}/assist/rephrase",
            headers=self.headers(who),
            json={"draft": draft},
            timeout=30,
        ).json()

    def nudge(self, who: str, local_hour: int | None = None) -> dict | None:
        params = {} if local_hour is None else {"local_hour": local_hour}
        return requests.get(
            f"{self.base}/assist/nudge",
            headers=self.headers(who),
            params=params,
            timeout=30,
        ).json().get("nudge")

    def nudge_feedback(self, nudge_id: str, action: str, who: str) -> int:
        return requests.post(
            f"{DJANGO}/api/v1/chat/assist/nudges/{nudge_id}/feedback",
            headers=self.headers(who),
            json={"action": action},
            timeout=30,
        ).status_code

    def caution_outcome(self, who: str, choice: str) -> int:
        return requests.post(
            f"{self.base}/assist/caution-outcome",
            headers=self.headers(who),
            json={"choice": choice},
            timeout=30,
        ).status_code

    def connection(self, who: str) -> dict:
        return requests.get(
            f"{DJANGO}/api/v1/personalization/connection",
            headers=self.headers(who),
            timeout=30,
        ).json()

    # ── internal state no endpoint exposes, and should not ──────────────

    def tendencies(self, who: str) -> list:
        """What has been observed about this partner. Self-readable only."""
        return shell_json(
            "import json;"
            "from apps.personalization import behaviour;"
            f"print(json.dumps(list(behaviour.tendencies_for({self.user_expr(who)}.id))))"
        )

    def suppressed(self, kind: str, context: dict | None = None) -> bool:
        return shell(
            "from apps.personalization import outcomes;"
            f"print(outcomes.suppressed('{self.rel}', '{kind}', {context!r}))"
        ) == "True"

    def policy_weights(self) -> dict:
        return shell_json(
            "import json;"
            "from apps.personalization.models import CouplePolicy;"
            f"p=CouplePolicy.objects.filter(relationship_id='{self.rel}').first();"
            "print(json.dumps(p.weights if p else {}))"
        )

    def refresh_score(self) -> dict:
        return shell_json(
            "import json;"
            "from apps.personalization import connection;"
            "from apps.relationships.models import Relationship;"
            f"r=Relationship.objects.get(id='{self.rel}');"
            "connection.update(r);"
            f"print(json.dumps(connection.presentation('{self.rel}')))"
        )

    def passive_surfaces(self, who: str) -> dict:
        """What ``who`` can read without the reading itself changing anything.

        Deliberately excludes ``/assist/nudge``: fetching it *builds* a nudge,
        costs a model call and writes a row. Sweeping it after every turn would
        have the leak check quietly manufacturing the nudges other scenarios
        assert on, and inflating every cost figure this suite reports. S17
        sweeps it explicitly, once, which is where that belongs.
        """
        return {
            "the thread": requests.get(
                f"{self.base}/messages", headers=self.headers(who), timeout=30
            ),
            "assist settings": requests.get(
                f"{self.base}/assist/settings", headers=self.headers(who), timeout=30
            ),
            "the connection score": requests.get(
                f"{DJANGO}/api/v1/personalization/connection",
                headers=self.headers(who),
                timeout=30,
            ),
            "their own behaviour": requests.get(
                f"{DJANGO}/api/v1/personalization/behaviour",
                headers=self.headers(who),
                timeout=30,
            ),
        }

    def surfaces(self, who: str) -> dict:
        """Every surface, including the ones with side effects."""
        every = self.passive_surfaces(who)
        every["the nudge endpoint"] = requests.get(
            f"{self.base}/assist/nudge", headers=self.headers(who), timeout=30
        )
        every["their own portrait"] = requests.get(
            f"{DJANGO}/api/v1/personalization/portrait", headers=self.headers(who), timeout=30
        )
        return every


# ── back-dating ─────────────────────────────────────────────────────────────


def backdate_messages(couple: Couple, ids, seconds: int) -> None:
    """Move messages into the past.

    Every scenario about accumulation needs this: tendencies decay over weeks,
    withdrawal is defined by a gap of hours, suppression expires over months.
    Waiting is not an option and mocking the clock would test the mock.

    ``created_at`` is ``auto_now_add``, so it cannot be assigned through
    ``save()`` — the update has to go through the queryset.
    """
    quoted = ",".join(f"'{i}'" for i in ids)
    shell(
        "from datetime import timedelta;"
        "from django.utils import timezone;"
        "from apps.chat.models import CoupleMessage;"
        f"CoupleMessage.objects.filter(id__in=[{quoted}]).update("
        f"created_at=timezone.now() - timedelta(seconds={seconds}));"
        "print('ok')"
    )


def backdate_behaviour(couple: Couple, who: str, days: int) -> None:
    """Age a partner's observed signals by ``days``.

    Rewrites the stored ``updated_at`` on each signal rather than the row's,
    because that is the timestamp the decay is computed from.
    """
    shell(
        "import json;"
        "from datetime import timedelta;"
        "from django.utils import timezone;"
        "from apps.personalization.models import BehaviourProfile;"
        f"p=BehaviourProfile.objects.filter(user={couple.user_expr(who)}).first();"
        "s=dict(p.signals or {});"
        "[e.__setitem__('updated_at', (timezone.now() - timedelta(days="
        f"{days})).isoformat()) for e in s.values()];"
        "p.signals=s; p.save(update_fields=['signals']);"
        "print('ok')"
    )


DAY = 60 * 60 * 24


def bad_night(couple: Couple, index: int, weeks_ago: int) -> None:
    """One sharp exchange, a long silence, then A coming back to it.

    The fixture the withdrawal signal is defined against, driven through real
    sends rather than by calling ``behaviour.observe`` — the thing worth
    proving is that the signal is reachable from actual use.

    Every message is left sitting at ``weeks_ago``, including the repair. An
    earlier version back-dated only the sharp pair and let the repairs pile up
    at "now", which put three of A's own messages in a row at the top of the
    thread and had the fifth bad night observed as *pursuit* — A messaging into
    silence — rather than withdrawal. The signals were fine; the fixture was
    lying to them, which is §5 of the plan's warning about back-dating exactly.
    """
    when = weeks_ago * 7 * DAY
    opened = couple.send("a", f"you always do this and I'm sick of it ({index})")
    closed = couple.send("b", "forget it, I'm done talking about it tonight")

    # Nine hours before the repair, so the gap A comes back across is the
    # silence the signal is named for — and a minute apart from each other,
    # because the withdrawal check reads whoever spoke *last*. Back-dating both
    # to one timestamp left their order up to the database, so the signal fired
    # or did not depending on which row Postgres happened to return first.
    backdate_messages(couple, [opened["id"]], when + 9 * 3600 + 60)
    backdate_messages(couple, [closed["id"]], when + 9 * 3600)

    repair = couple.send("a", "I'm sorry about last night. can we try that again")
    backdate_messages(couple, [repair["id"]], when)


def backdate_policy(couple: Couple, days: int) -> None:
    """Age every lesson this couple has taught the system."""
    shell(
        "from datetime import timedelta;"
        "from django.utils import timezone;"
        "from apps.personalization.models import CouplePolicy;"
        f"p=CouplePolicy.objects.filter(relationship_id='{couple.rel}').first();"
        "w=dict(p.weights or {});"
        "[e.__setitem__('updated_at', (timezone.now() - timedelta(days="
        f"{days})).isoformat()) for e in w.values()];"
        "p.weights=w; p.save(update_fields=['weights']);"
        "print('ok')"
    )


# ── asserting on text without pinning it ────────────────────────────────────

_AFFECTION = ("love you", "i love", "sweetheart", "darling", "babe", "honey", "xx")


def rewrite_faults(original: str, rewrite: str) -> list:
    """Ways a suggested rewrite is wrong regardless of how it is phrased.

    Not a quality judgement — three properties that would make the suggestion
    actively harmful, all checkable without pinning a single word:

    * It reintroduces the sweeping-accusation pattern the check exists to
      catch, so the "improvement" is the original defect with better manners.
    * It is much longer than the draft. Someone hits send on a one-liner and is
      offered a paragraph; they send the one-liner.
    * It adds affection that was not there. Putting "love you" into a message
      about the bins is the system speaking in someone's voice, and it is the
      failure that makes a person distrust every suggestion after it.
    """
    faults = []
    lowered = rewrite.lower()

    for absolute in ("always", "never"):
        if absolute in lowered and absolute not in original.lower():
            faults.append(f"introduces '{absolute}'")

    if original and len(rewrite) > 1.5 * len(original) + 40:
        faults.append(f"{len(rewrite)} chars from {len(original)}")

    for token in _AFFECTION:
        if token in lowered and token not in original.lower():
            faults.append(f"introduces affection: {token!r}")

    return faults


# ── playing a scenario ──────────────────────────────────────────────────────


class Scenario:
    """One scripted conversation and what it should and should not produce."""

    def __init__(self, key, title, turns=(), defaults=None, body=None, note=""):
        self.key = key
        self.title = title
        self.turns = list(turns)
        self.defaults = defaults or {}
        self.body = body
        self.note = note


def model_calls() -> int:
    """Completions attempted since the counter was last reset."""
    return int(shell("from apps.chat import assist; print(assist.model_calls())"))


def _reset_model_calls() -> None:
    shell("from apps.chat import assist; assist.reset_model_calls(); print('ok')")


def leak_offenders(couple: Couple, who: str, surfaces=None) -> dict:
    """Which of ``who``'s surfaces name their partner's tendencies. Empty is clean."""
    offenders = {}
    for name, response in (surfaces or couple.passive_surfaces(who)).items():
        found = [word for word in PROFILE_VOCABULARY if word in response.text]
        if found:
            offenders[name] = found
    return offenders


def assert_no_leak(couple: Couple, who: str, label: str) -> None:
    offenders = leak_offenders(couple, who)
    check(
        f"{label}: {who}'s surfaces say nothing about their partner's profile",
        not offenders,
        json.dumps(offenders) if offenders else "",
    )


def play(scenario: Scenario) -> dict:
    """Run one scenario against a fresh couple. Returns its stats."""
    print(f"\n== {scenario.key} — {scenario.title} ==")
    if scenario.note:
        print(f"   {scenario.note}")

    started = time.perf_counter()
    _reset_model_calls()
    couple = Couple(scenario.key.lower())

    # The leak sweep runs after every turn but reports once. Per-turn PASS
    # lines for it would be four fifths of this suite's output saying the same
    # thing, and a scoreboard nobody reads is a scoreboard that stops being
    # read on the day it matters. A failure still names the turn it happened on.
    leaks = {}
    swept = 0

    for index, turn in enumerate(scenario.turns, start=1):
        expect = dict(scenario.defaults)
        expect.update(turn.expect or {})
        _play_turn(couple, scenario, index, turn, expect)
        if expect.get("no_leak", True):
            swept += 1
            for who in ("a", "b"):
                found = leak_offenders(couple, who)
                if found:
                    leaks[f"turn {index}, {who}"] = found

    if swept:
        check(
            f"{scenario.key}: neither partner's surfaces named the other's profile"
            f" ({swept} turns)",
            not leaks,
            json.dumps(leaks) if leaks else "",
        )

    if scenario.body is not None:
        scenario.body(couple)

    elapsed = time.perf_counter() - started
    calls = model_calls()
    print(f"   {elapsed:.1f}s, {calls} model call{'' if calls == 1 else 's'}")
    return {"key": scenario.key, "seconds": elapsed, "model_calls": calls}


def _play_turn(couple: Couple, scenario: Scenario, index: int, turn: Turn, expect: dict) -> None:
    who = turn.who
    label = f"{scenario.key}.{index}"
    excerpt = turn.text if len(turn.text) <= 42 else turn.text[:39] + "..."

    # 1. The pre-send check, as the client runs it: on the draft, before the
    #    message exists. Asked first so the verdict is about the thread as it
    #    stood when the person was typing.
    if "caution" in expect:
        verdict = couple.check_draft(who, turn.text)
        cautioned = verdict.get("verdict") == "caution"
        if expect["caution"]:
            check(
                f"{label}: caution on {excerpt!r}",
                cautioned,
                verdict.get("reason") or "no caution",
            )
            if cautioned:
                faults = rewrite_faults(turn.text, verdict.get("suggestion") or "")
                check(
                    f"{label}: the offered rewrite is usable",
                    not faults,
                    "; ".join(faults) if faults else (verdict.get("suggestion") or "")[:70],
                )
        else:
            check(
                f"{label}: stays quiet on {excerpt!r}",
                not cautioned,
                f"flagged: {verdict.get('reason')}" if cautioned else "",
            )

    sent = couple.send(who, turn.text)

    # 2. Read-coaching is offered to the person who *received* this, which is
    #    the whole point of it: escalation happens in the reaction, not the
    #    opening message.
    if "coach" in expect or "defer_to_support" in expect:
        coaching = couple.read_coach(couple.other(who), turn.text)
        guidance = coaching.get("guidance")
        deferred = bool(coaching.get("defer_to_support"))

        if "defer_to_support" in expect:
            check(
                f"{label}: routes to support",
                deferred == expect["defer_to_support"],
                f"defer_to_support={deferred}",
            )
            if expect["defer_to_support"]:
                # The worst single output this system could produce is
                # "try to see it from their side" in answer to an abuse
                # disclosure. Assert the absence, not just the flag.
                check(
                    f"{label}: no accommodation coaching alongside the referral",
                    guidance is None,
                    (guidance or "")[:90],
                )

        if "coach" in expect:
            check(
                f"{label}: {'coaches' if expect['coach'] else 'does not coach'} the receiver",
                bool(guidance) == expect["coach"],
                (guidance or "none")[:90],
            )

    # 3. Whether an unprompted suggestion is offered right now.
    if "nudge" in expect:
        hour = expect.get("local_hour")
        offered = couple.nudge(who, local_hour=hour)
        kind = (offered or {}).get("kind")
        check(
            f"{label}: nudge is {expect['nudge'] or 'none'}",
            kind == expect["nudge"],
            f"got {kind or 'none'}",
        )

    if "tendency" in expect:
        wanted = expect["tendency"]
        observed = couple.tendencies(who)
        if wanted is None:
            check(f"{label}: nothing observed about {who} yet", not observed, str(observed))
        else:
            check(f"{label}: {wanted} observed on {who}", wanted in observed, str(observed))

    return sent
