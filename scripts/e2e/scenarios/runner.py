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

# Scenario modules import everything from here rather than reaching into
# `harness` themselves, so there is one place that knows how the two fit
# together. `repo_root` is re-exported for that reason and used by callers.
from harness import (  # noqa: E402
    DJANGO,
    auth,
    check,
    pair,
    register,
    repo_root,  # noqa: F401 — re-exported for the scenario modules
    shell,
    shell_json,
    stamp,
)

#: ``who`` is "a" or "b". ``expect`` is a dict of assertions evaluated after
#: that turn lands; any key may be omitted, and an omitted key asserts nothing.
#:
#:   caution:          True | False    — /assist/check on this text before sending
#:                     None            — assert nothing, overriding a default
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
        self.sent: list[dict] = []

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
        message = r.json() if r.content else {}
        if message.get("id"):
            # Kept so a scenario body can reach back to a message its turns
            # sent — read-coaching is asked for by id, and the turns are played
            # by the framework before the body runs.
            self.sent.append(message)
        return message

    def last_sent(self) -> dict:
        """The most recent message in this thread, as the server returned it."""
        return self.sent[-1]

    #: How many times a caution-expected check may be asked before it counts as
    #: a real absence. Three, because two was not enough: on a full run with a
    #: Celery worker draining summaries behind it the stack slows by half, and
    #: a check that must answer inside 2.5s starts missing the window.
    CHECK_ATTEMPTS = 3

    def check_draft(self, who: str, text: str, expect_caution: bool = False) -> dict:
        """The pre-send check, as the client runs it.

        ``expect_caution`` buys up to :data:`CHECK_ATTEMPTS` tries, and only in
        that direction. The check has a 2.5s budget and fails open — correctly,
        since trapping someone's message behind a slow classifier is far worse
        than missing a warning — and a fail-open is deliberately
        indistinguishable from "ok" to everything outside, including this
        suite. So under load a caution assertion goes red for a reason that is
        the system working exactly as designed.

        Retrying only when a caution was expected is the asymmetry that keeps
        this honest: it can turn a timeout into the caution that was really
        there, and it can never turn a false positive into a pass. A draft that
        does not caution in three attempts does not caution.

        A timed-out call is not cached — `check_before_send` only caches a
        verdict it actually got — so each attempt genuinely re-asks.
        """
        for attempt in range(1, self.CHECK_ATTEMPTS + 1):
            verdict = self._check_once(who, text)
            verdict["attempts"] = attempt
            if not expect_caution or verdict.get("verdict") == "caution":
                return verdict
        return verdict

    def _check_once(self, who: str, text: str) -> dict:
        return requests.post(
            f"{self.base}/assist/check",
            headers=self.headers(who),
            json={"draft": text},
            timeout=30,
        ).json()

    def read_coach(self, who: str, message_id: str) -> dict:
        """What the system offers ``who`` about a message in their thread.

        By id, as the client asks: the endpoint reads the text out of the row
        itself, so it knows who sent it and can refuse the sender.
        """
        return requests.post(
            f"{self.base}/assist/read-coach",
            headers=self.headers(who),
            json={"message_id": message_id},
            timeout=30,
        ).json()

    def coach_on(self, who: str, text: str) -> dict:
        """Send ``text`` from the other partner, then coach ``who`` on it.

        Probing a phrasing means putting it in the thread first, now that the
        endpoint takes an id. That is the more honest test anyway — it is the
        sequence the client actually performs — and it is why these sweeps
        cost a send apiece.
        """
        return self.read_coach(who, self.send(self.other(who), text)["id"])

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

    def caution_outcome(self, who: str, choice: str, draft: str | None = None) -> int:
        """Report which way a caution went.

        ``draft`` is what lets the loop learn per register rather than per
        couple. Optional here as it is on the endpoint, so the legacy shape
        stays exercised — a client that does not send it must still be able to
        quieten a caution it keeps overriding.
        """
        body = {"choice": choice}
        if draft is not None:
            body["draft"] = draft
        return requests.post(
            f"{self.base}/assist/caution-outcome",
            headers=self.headers(who),
            json=body,
            timeout=30,
        ).status_code

    def insights(self, who: str) -> list:
        """What Bliss has noticed, as ``who`` can read it."""
        response = requests.get(
            f"{DJANGO}/api/v1/insights/", headers=self.headers(who), timeout=30
        )
        response.raise_for_status()
        return response.json().get("insights", [])

    def connection(self, who: str) -> dict:
        return requests.get(
            f"{DJANGO}/api/v1/personalization/connection",
            headers=self.headers(who),
            timeout=30,
        ).json()

    # ── internal state no endpoint exposes, and should not ──────────────

    def user_id(self, who: str) -> str:
        return shell(f"print({self.user_expr(who)}.id)")

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

    def score_components(self) -> dict:
        """The parts the score is built from, before weighting.

        Read directly because no endpoint exposes them and none should — the
        components are the couple's behaviour broken down, and a breakdown is
        a more pointed thing to publish than the number. The suite needs them
        to assert that a component moved for the reason it was supposed to
        rather than because some other part of the sum happened to rise.
        """
        return shell_json(
            "import json;"
            "from datetime import timedelta;"
            "from django.utils import timezone;"
            "from apps.personalization import connection;"
            "from apps.relationships.models import Relationship;"
            f"r=Relationship.objects.get(id='{self.rel}');"
            "since=timezone.now() - timedelta(days=connection.WINDOW_DAYS);"
            "parts,events=connection._components(r, since);"
            "print(json.dumps({**parts, 'events': events}))"
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
            # In the sweep rather than only in S21. Insights are the newest
            # thing that crosses between two people, so they are the most
            # likely place for a leak to appear — and the boundary is worth
            # asserting on every scenario's surfaces, not just the one written
            # to look for it. A plain GET with no side effects, so it belongs
            # in the passive set.
            "what Bliss has noticed": requests.get(
                f"{DJANGO}/api/v1/insights/", headers=self.headers(who), timeout=30
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


def age_score(couple: Couple, days: int = 1) -> None:
    """Move the stored score's clock back, so the next update counts as a day.

    ``connection.update`` folds in one smoothing step per day rather than per
    call, which is what makes the number's inertia a property of time instead
    of a property of how often the job ran. The cost is that a test cannot walk
    the score forward by calling in a loop; it has to say how much time passed,
    which is more honest about what it is simulating anyway.

    ``updated_at`` is ``auto_now``, so this has to go through the queryset.
    """
    shell(
        "from datetime import timedelta;"
        "from django.utils import timezone;"
        "from apps.personalization.models import ConnectionScore;"
        f"ConnectionScore.objects.filter(relationship_id='{couple.rel}').update("
        f"updated_at=timezone.now() - timedelta(days={days}));"
        "print('ok')"
    )


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
    try:
        return _play(scenario, started)
    except Exception as exc:
        # One scenario failing must not take the other seventeen with it. This
        # drives a real server over a real network for ten minutes; a dropped
        # connection is a fact about the afternoon, and a suite that aborts on
        # it throws away every result after the one that broke — including the
        # findings somebody is waiting on. Recorded as a failed check so it
        # still counts against the tally rather than vanishing.
        check(f"{scenario.key}: ran to completion", False, f"{type(exc).__name__}: {exc}")
        return {
            "key": scenario.key,
            "seconds": time.perf_counter() - started,
            "model_calls": model_calls(),
        }


def _play(scenario: Scenario, started: float) -> dict:
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
    # `None` asserts nothing, which is how a turn opts out of a group default.
    # Distinct from `nudge: None`, where None is a real expectation — hence a
    # per-key rule rather than a blanket one.
    if expect.get("caution") is not None:
        verdict = couple.check_draft(who, turn.text, expect_caution=expect["caution"])
        cautioned = verdict.get("verdict") == "caution"
        if expect["caution"]:
            attempts = verdict.get("attempts", 1)
            check(
                f"{label}: caution on {excerpt!r}",
                cautioned,
                (verdict.get("reason") or f"no caution in {attempts} attempts")
                + (f" (attempt {attempts})" if cautioned and attempts > 1 else ""),
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
        coaching = couple.read_coach(couple.other(who), sent["id"])
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
