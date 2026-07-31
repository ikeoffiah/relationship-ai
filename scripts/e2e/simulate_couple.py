"""A couple, simulated over a month, watched rather than asserted.

    backend-django/venv/bin/python scripts/e2e/simulate_couple.py
    backend-django/venv/bin/python scripts/e2e/simulate_couple.py --weeks 2

Different in kind from `run_scenarios.py`. Those are short, scripted and
pass/fail: does the caution fire on *this* turn, does that phrasing route to
support. This is one couple living for four weeks — chatting, checking in,
playing the games, answering the questions, having a rough patch and coming
out of it — and the output is a **trajectory**, printed for a person to read.

Why not assertions. Everything interesting here is emergent: a score, a set of
tendencies, how often the assist spoke. Pinning emergent numbers produces a
suite that fails whenever anything improves, and a suite that cries wolf gets
muted — which is how you end up with no coverage at all in the place you most
wanted it. So the numbers are reported and judged by eye.

What *is* asserted is the small set of things that would be wrong at any value,
checked at every snapshot rather than once at the end:

  1. Nothing inferred about one partner appears on any surface the other reads.
  2. The connection score never reads a private check-in value.
  3. The outcome loop only ever quietens.
  4. Nothing the assist does can stop a message being sent.

Those exit non-zero. The trajectory does not.
"""

import argparse
import pathlib
import sys
from collections import Counter

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from harness import DJANGO, check, report, shell, shell_json  # noqa: E402
from scenarios.loop import policy_call_sites  # noqa: E402
from scenarios.runner import (  # noqa: E402
    Couple,
    backdate_messages,
    bad_night,
    leak_offenders,
    model_calls,
)

DAY = 60 * 60 * 24

#: The arc is compressed into the connection score's own window.
#:
#: It was a month at first, and every snapshot before the last read
#: `mutuality=0.00` — correctly. `connection.WINDOW_DAYS` is 14, all four weeks
#: are replayed in one real instant, so every snapshot is computed at the same
#: "now" and anything back-dated past a fortnight is invisible to it. A
#: simulation whose early readings are structurally always zero teaches nobody
#: anything, so the four phases sit at days 14, 11, 8 and 4.
PHASE_DAYS = [14, 11, 8, 4]


# ── what the couple does, and what it costs ─────────────────────────────────


class Log:
    """Everything observed, so a week can be summarised rather than narrated."""

    def __init__(self):
        self.counts = Counter()
        self.nudges = Counter()
        self.cautions = []
        self.coaching = []

    def note(self, key, n=1):
        self.counts[key] += n

    def summary(self):
        c = self.counts
        return (
            f"messages {c['msg']} (a {c['msg_a']} / b {c['msg_b']})"
            f"   check-ins {c['checkin']}   gratitude {c['gratitude']}"
            f"   games {c['game_answer']}   questions {c['question']}"
        )


class Simulated(Couple):
    """A paired couple, plus the rest of the product they actually use."""

    def __init__(self, tag, log):
        super().__init__(tag)
        self.log = log

    # ── the thread, as a client drives it ───────────────────────────────

    def say(self, who, text, day=None):
        """Send one message the way the app does: check, send, then coach.

        All three, because the cost and the noise of this feature are what the
        couple experiences, and two of the three are invisible from the
        database afterwards.
        """
        verdict = self.check_draft(who, text)
        if verdict.get("verdict") == "caution":
            self.log.cautions.append((who, text, verdict.get("reason", "")))
            # Taking the suggestion, which is also what teaches the loop.
            self.caution_outcome(who, "used_suggestion", draft=text)

        message = self.send(who, text)
        self.log.note("msg")
        self.log.note(f"msg_{who}")

        coaching = self.read_coach(self.other(who), message["id"])
        if coaching.get("guidance"):
            self.log.coaching.append((self.other(who), text, coaching["guidance"]))
        if coaching.get("defer_to_support"):
            self.log.note("deferred")

        if day is not None:
            backdate_messages(self, [message["id"]], day * DAY)
        return message

    def open_thread(self, who, hour=21):
        """What happens when someone opens the app in the evening."""
        offered = self.nudge(who, local_hour=hour)
        if offered:
            self.log.nudges[offered["kind"]] += 1
        return offered

    # ── the rest of the product ─────────────────────────────────────────

    def play_a_game(self, who):
        """Answer every question in the first pack available to this partner."""
        packs = requests.get(
            f"{DJANGO}/api/v1/engagement/games", headers=self.headers(who), timeout=30
        ).json()
        rows = packs.get("games") or []
        if not rows:
            return 0
        key = rows[0]["key"]

        detail = requests.get(
            f"{DJANGO}/api/v1/engagement/games/{key}",
            headers=self.headers(who),
            timeout=30,
        ).json()
        answered = 0
        for question in (detail.get("questions") or [])[:5]:
            response = requests.post(
                f"{DJANGO}/api/v1/engagement/games/{key}/answer",
                headers=self.headers(who),
                # Indices, not the option text — the server answers
                # "answers must be option indices" to anything else.
                json={
                    "question_id": question["id"],
                    "self_answer": 0,
                    "guess_answer": 0,
                },
                timeout=30,
            )
            if response.status_code in (200, 201):
                answered += 1
        self.log.note("game_answer", answered)
        return answered

    def answer_todays_question(self, who, text):
        response = requests.post(
            f"{DJANGO}/api/v1/engagement/daily-question/answer",
            headers=self.headers(who),
            json={"response_text": text},
            timeout=30,
        )
        if response.status_code in (200, 201):
            self.log.note("question")
        return response.status_code

    def be_grateful(self, who, text):
        requests.post(
            f"{DJANGO}/api/v1/engagement/gratitude",
            headers=self.headers(who),
            json={"text": text},
            timeout=30,
        )
        self.log.note("gratitude")

    def daily_rows(self, days, score=4):
        """Check-ins and completed micro-actions, one per person per day.

        Written directly. Both models carry a (user, date_key) unique
        constraint — the product saying a daily pulse is not something you can
        farm — so a month of them cannot be produced through the API inside one
        run. The rows are the ones the endpoints write.
        """
        made = shell_json(
            "import json;"
            "from datetime import timedelta;"
            "from django.utils import timezone;"
            "from apps.engagement.models import ("
            "MicroActionLog, MicroActionTemplate, RelationshipCheckIn);"
            "from apps.relationships.models import Relationship;"
            f"r=Relationship.objects.get(id='{self.rel}');"
            f"a={self.user_expr('a')};"
            f"b={self.user_expr('b')};"
            "today=timezone.localtime().date();"
            f"days=[(today - timedelta(days=d)).isoformat() for d in {days!r}];"
            "t=MicroActionTemplate.objects.filter(is_active=True).first();"
            "n=0;"
            "n+=len([RelationshipCheckIn.objects.get_or_create("
            f"user=u, date_key=k, defaults=dict(relationship=r, connection_score={score},"
            " mood='good'))"
            " for k in days for u in (a,b)]);"
            "n+=len([MicroActionLog.objects.get_or_create("
            "user=u, date_key=k, defaults=dict(relationship=r, template=t, completed=True))"
            " for k in days for u in (a,b)]) if t else 0;"
            "print(json.dumps(n))"
        )
        self.log.note("checkin", len(days) * 2)
        return made

    # ── what we look at ─────────────────────────────────────────────────

    def portrait(self, who):
        return requests.get(
            f"{DJANGO}/api/v1/personalization/portrait",
            headers=self.headers(who),
            timeout=30,
        ).json()


# ── the month ───────────────────────────────────────────────────────────────

BANTER = [
    ("a", "you're the worst 😂"),
    ("b", "I cannot believe you did that"),
    ("a", "stop it 😭"),
]

LOGISTICS = [
    ("a", "running 10 late"),
    ("b", "no worries, I'll put the oven on"),
    ("a", "can you grab milk on the way home"),
    ("b", "got it. bin day tomorrow?"),
]

WARMTH = [
    ("a", "thinking about you today"),
    ("b", "that made my afternoon"),
    ("a", "shall we watch something tonight"),
]

FRICTION = [
    ("a", "did you sort out the car thing today?"),
    ("b", "not yet, I ran out of time"),
    ("a", "you said that last week too, it's getting frustrating"),
    ("b", "I know. I'll do it tomorrow"),
]


def week_one(couple, log):
    """Settling in. Ordinary life, and the system should barely appear."""
    for offset, script in enumerate([LOGISTICS, BANTER, WARMTH]):
        for who, text in script:
            couple.say(who, text, day=PHASE_DAYS[0] - offset)
        couple.open_thread("a")
    couple.daily_rows(list(range(11, 15)))
    couple.play_a_game("a")
    couple.play_a_game("b")
    couple.answer_todays_question("a", "the way you laugh at your own jokes")
    couple.answer_todays_question("b", "how you always know when something is off")
    couple.be_grateful("a", "thank you for sorting the car")
    couple.be_grateful("b", "thank you for dinner")


def week_two(couple, log):
    """Busier. Less contact, and the first sharp edge."""
    for offset, script in enumerate([LOGISTICS, FRICTION]):
        for who, text in script:
            couple.say(who, text, day=PHASE_DAYS[1] - offset)
        couple.open_thread("b")
    couple.daily_rows(list(range(8, 11)))
    couple.be_grateful("a", "thanks for being patient with me this week")


def week_three(couple, log):
    """The rough patch. Two bad nights, then B messaging into silence."""
    # The sharpest thing anyone says all month, and sent through the same
    # check-send-coach path a real client uses — otherwise the caution is
    # never exercised by this simulation at all, which is what happened on
    # the first run.
    couple.say("a", "you never follow through on anything, it's always me", day=PHASE_DAYS[2])

    for index in range(2):
        bad_night(couple, index, weeks_ago=1)
        log.note("bad_night")

    for text in (
        "are you there?",
        "I don't want to leave it like this",
        "please just say something",
        "ok I'll stop",
    ):
        couple.say("b", text, day=PHASE_DAYS[2] - 1)

    couple.say("b", "I don't know if I want to keep doing this", day=PHASE_DAYS[2] - 1)
    couple.daily_rows(list(range(5, 8)), score=2)
    couple.open_thread("a")
    couple.open_thread("b")


def week_four(couple, log):
    """Repair, and coming back. Both of them turning up again."""
    for _ in range(5):
        couple.send("a", kind="sticker", sticker="repair.sorry")
        log.note("repair_sticker")

    couple.say("a", "I'm sorry about last week. I want to work on this", day=PHASE_DAYS[3])
    couple.say("b", "me too. thank you for saying it", day=PHASE_DAYS[3])
    for who, text in WARMTH + BANTER:
        couple.say(who, text, day=PHASE_DAYS[3] - 2)

    couple.daily_rows(list(range(1, 5)))
    couple.be_grateful("a", "thank you for staying with it")
    couple.be_grateful("b", "thank you for coming back to me")
    couple.play_a_game("a")
    couple.open_thread("a")


WEEKS = [
    ("week 1 — settling in", week_one),
    ("week 2 — busier, first friction", week_two),
    ("week 3 — the rough patch", week_three),
    ("week 4 — repair and recovery", week_four),
]


# ── watching ────────────────────────────────────────────────────────────────


def snapshot(couple, label, log, spent):
    """Print where the couple is, and check the things that must always hold."""
    presentation = couple.refresh_score()
    parts = couple.score_components()

    print(f"\n  {label}")
    print(f"    {log.summary()}")
    print(
        f"    assist:  cautions {len(log.cautions)}"
        f"   coaching {len(log.coaching)}"
        f"   nudges {dict(log.nudges) or 'none'}"
        f"   deferrals {log.counts['deferred']}"
    )

    score = presentation.get("score")
    print(
        f"    score:   {score if score is not None else '—'}"
        f" ({presentation.get('emphasis')})"
        f"   {' '.join(f'{k}={v:.2f}' for k, v in parts.items() if k != 'events')}"
    )
    print(
        f"    lately:  a — {couple.tendencies('a') or 'nothing observed'}"
        f"   |   b — {couple.tendencies('b') or 'nothing observed'}"
    )
    weights = couple.policy_weights()
    print(f"    learned: {learned(weights)}   |   {spent} model calls so far")

    # ── the invariants, at every snapshot rather than once at the end ────
    for who in ("a", "b"):
        offenders = leak_offenders(couple, who, couple.surfaces(who))
        check(
            f"{label}: {who} is told nothing about their partner's profile",
            not offenders,
            str(offenders),
        )

    check(
        f"{label}: the score is still built from behaviour alone",
        not reads_check_in_value(),
        "connection.py now names a check-in value" if reads_check_in_value() else "",
    )
    # The loop may quieten, never nag. Behaviour cannot demonstrate the
    # absence of a feature, so this pins the blast radius the same way S13
    # does: nothing outside outcomes.py reads the raw score, and there is
    # nowhere else an escalation could be wired in.
    raw_readers = [
        f"{path}: {line}"
        for path, lines in policy_call_sites().items()
        if path != "apps/personalization/outcomes.py"
        for line in lines
        if "score_for" in line
    ]
    check(
        f"{label}: the outcome loop still has no way to become more insistent",
        not raw_readers,
        "; ".join(raw_readers),
    )


def learned(weights):
    if not weights:
        return "nothing yet"
    return ", ".join(
        f"{key} {entry.get('score', 0):+.1f}" for key, entry in sorted(weights.items())
    )


def reads_check_in_value():
    return shell(
        "import inspect;"
        "from apps.personalization import connection;"
        "src=inspect.getsource(connection);"
        "print('connection_score' in src or '.mood' in src)"
    ) == "True"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weeks", type=int, default=4, help="how many weeks to live")
    args = parser.parse_args()

    log = Log()
    print("\n== a couple, simulated ==")
    couple = Simulated("sim", log)
    print(f"   {couple.emails['a']} & {couple.emails['b']}")
    print(f"   relationship {couple.rel}")

    for label, week in WEEKS[: max(1, args.weeks)]:
        week(couple, log)
        snapshot(couple, label, log, model_calls())

    print("\n== what the assist actually said ==")
    if log.cautions:
        for who, text, reason in log.cautions:
            print(f"  caution  {who}: {text[:46]!r}\n           -> {reason}")
    else:
        print("  no cautions in the whole month")
    for who, text, guidance in log.coaching:
        print(f"  coached  {who} on {text[:40]!r}\n           -> {guidance[:96]}")

    print("\n== where they ended up ==")
    for who in ("a", "b"):
        print(f"  {who}: {couple.tendencies(who) or 'no tendencies reported'}")
    print(f"  total model calls: {model_calls()}")
    print(
        "\n  note: the score is smoothed per *call* to connection.update(), not\n"
        "  per day, so this simulation deliberately refreshes once per phase —\n"
        "  the same cadence as the nightly job. Two runs in one day would move\n"
        "  the number twice as far as one."
    )

    return report("invariants held")


if __name__ == "__main__":
    sys.exit(main())
