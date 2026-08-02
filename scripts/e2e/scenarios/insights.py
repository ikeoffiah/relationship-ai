"""§9 of ``docs/relationship-insights.md`` — what Bliss has noticed.

Insights are the newest thing in the product that *crosses* between two people,
and the only one built to be shown to both partners at once. Everything else
either stays with the person it is about (the portrait, the behaviour signals)
or is addressed to one of them (coaching, cautions). So these two scenarios are
about the boundary rather than about the detector, which unit tests cover.

S21 is the happy path with the leak sweep on top: a real theme, produced from a
real thread by a real model call, reaching both partners in words that quote
neither of them.

S22 is the one that matters more. A couple with a recent abuse signal has
nothing crossing — and "nothing" has to include the insight they were shown
last week, which is the gap this scenario found. Gating synthesis only stops
the *next* one.
"""

import json

from .runner import (
    Scenario,
    check,
    leak_offenders,
    shell,
    shell_json,
)

DAY = 60 * 60 * 24

# One subject wearing three different sets of clothes. The detector has to
# recognise these as the same disagreement; if it cannot, the scenario is
# testing an empty database and would pass for the wrong reason, so S21 asserts
# a theme was actually found before it asserts anything about the boundary.
ARGUMENTS = [
    (
        "you said seven and it's half eight, I've been sat here since",
        "I told you the meeting might run over, you never listen",
    ),
    (
        "you booked the whole Trafalgar weekend without asking me first",
        "I mentioned it last week, you just weren't paying attention",
    ),
    (
        "why do I find out about your mother coming from your sister",
        "because you're impossible to plan anything with, that's why",
    ),
]

# Planted in the thread so the boundary assertion has something concrete to
# look for. If any of these reaches the other partner's screen, the insight
# repeated something one of them said instead of naming the shape.
PLANTED = ("Trafalgar", "sister", "half eight")


def _seed_arguments(couple) -> None:
    """Three arguments, on three separate days, each assessed as a rupture.

    Back-dated well past ``RUPTURE_QUIET_DAYS`` so none of them is *open* —
    an insight is held while a couple is still in the middle of something, and
    a fixture that left the last argument at "now" would test that rule rather
    than this one.
    """
    spans = []
    for index, (opened, answered) in enumerate(ARGUMENTS):
        days_ago = 40 - index * 12  # 40, 28, 16 — inside the 60-day window
        first = couple.send("a", opened)
        second = couple.send("b", answered)
        shell(
            "from datetime import timedelta;"
            "from django.utils import timezone;"
            "from apps.chat.models import CoupleMessage;"
            f"CoupleMessage.objects.filter(id='{first['id']}').update("
            f"created_at=timezone.now() - timedelta(days={days_ago}));"
            f"CoupleMessage.objects.filter(id='{second['id']}').update("
            f"created_at=timezone.now() - timedelta(days={days_ago}) "
            "+ timedelta(minutes=2));"
            "print('ok')"
        )
        spans.append(days_ago)

    # Written directly rather than through `assess_ruptures`, deliberately.
    # That task's judgement is S-nothing's business — it has its own coverage —
    # and paying for three more model calls here would make this scenario's
    # cost figure a statement about the assessor rather than about insights.
    quoted = ",".join(str(day) for day in spans)
    shell(
        "from datetime import timedelta;"
        "from django.utils import timezone;"
        "from apps.personalization.models import RuptureAssessment;"
        "from apps.relationships.models import Relationship;"
        f"rel = Relationship.objects.get(id='{couple.rel}');"
        f"[RuptureAssessment.objects.create(relationship=rel,"
        " started_at=timezone.now() - timedelta(days=day),"
        " ended_at=timezone.now() - timedelta(days=day) + timedelta(minutes=5),"
        f" is_rupture=True, confidence=0.9) for day in [{quoted}]];"
        "print('ok')"
    )


def _synthesise() -> int:
    """Run the nightly sweep now. Returns how many insights it wrote."""
    return int(
        shell(
            "from apps.insights.tasks import synthesise_insights;"
            "print(synthesise_insights())"
        )
    )


def _abuse_signal(couple) -> None:
    """The thing that must stop everything crossing."""
    couple.send("a", "I went through your phone last night")


# ── S21 — The shape crosses, nothing else does ──────────────────────────────

S21 = Scenario(
    "S21",
    "The shape crosses, nothing else does",
    note="a real recurring theme, then sweep both partners' surfaces for it",
)


def _s21(couple):
    _seed_arguments(couple)
    written = _synthesise()

    check(
        "S21: three arguments on one subject produce an insight",
        written >= 1,
        f"synthesise wrote {written}",
    )

    seen = {who: couple.insights(who) for who in ("a", "b")}

    check(
        "S21: both partners can see it",
        len(seen["a"]) == 1 and len(seen["b"]) == 1,
        f"a={len(seen['a'])} b={len(seen['b'])}",
    )
    if not (seen["a"] and seen["b"]):
        return

    a_side, b_side = seen["a"][0], seen["b"][0]

    check(
        "S21: it is the same insight, not a version each",
        a_side["id"] == b_side["id"] and a_side["theme"] == b_side["theme"],
        f"{a_side.get('theme')!r} vs {b_side.get('theme')!r}",
    )

    # The whole justification for showing this to both without a consent step
    # is that there is nothing in it to consent to. That claim is only true if
    # the theme is a shape rather than a quotation.
    echoed = [word for word in PLANTED if word.lower() in a_side["theme"].lower()]
    check(
        "S21: the theme repeats nothing either of them said",
        not echoed,
        f"echoed {echoed} in {a_side['theme']!r}",
    )

    # The narrative halves are the private ones. They are empty today, and the
    # serializer must not start shipping them the day a detector fills them.
    check(
        "S21: only shape-only fields are serialised",
        set(a_side) == {"id", "type", "theme", "confidence", "created_at"},
        f"fields: {sorted(a_side)}",
    )

    for who in ("a", "b"):
        offenders = leak_offenders(couple, who)
        check(
            f"S21: {who}'s surfaces still say nothing about their partner's profile",
            not offenders,
            json.dumps(offenders) if offenders else "",
        )


S21.body = _s21


# ── S22 — A signal retracts what was already shown ──────────────────────────

S22 = Scenario(
    "S22",
    "A signal retracts what was already shown",
    note="an insight, then an abuse signal — and nothing crossing afterwards",
)


def _s22(couple):
    _seed_arguments(couple)
    _synthesise()

    before = couple.insights("a")
    check(
        "S22: the couple has an insight to begin with",
        len(before) == 1,
        f"{len(before)} before the signal",
    )
    if not before:
        return

    _abuse_signal(couple)
    _synthesise()

    for who in ("a", "b"):
        after = couple.insights(who)
        check(
            f"S22: nothing crosses to {who} after the signal",
            not after,
            f"{len(after)} still visible",
        )

    # The rule is about what crosses *between* them, not about switching the
    # product off for somebody who may be in trouble. Their own self-facing
    # surfaces have to keep working.
    surfaces = couple.passive_surfaces("a")
    for name in ("the thread", "their own behaviour", "the connection score"):
        check(
            f"S22: {name} still works for them",
            surfaces[name].status_code == 200,
            f"{name} -> {surfaces[name].status_code}",
        )

    # The trap the spec exists to avoid. Repair signals are things a
    # controlling partner can perform, and can pressure the other into
    # performing, so anything that reads them as a route back would be
    # instructions for looking repaired handed to the wrong person.
    shell(
        "from apps.chat.models import CoupleMessage;"
        "from apps.relationships.models import Relationship;"
        f"rel = Relationship.objects.get(id='{couple.rel}');"
        "[CoupleMessage.objects.create(relationship=rel, sender=rel.partner_a,"
        " kind=CoupleMessage.KIND_STICKER, sticker='repair.sorry')"
        " for _ in range(5)];"
        "print('ok')"
    )
    _synthesise()

    check(
        "S22: repair does not buy it back",
        not couple.insights("a"),
        "an insight returned after repair stickers",
    )

    stored = shell_json(
        "import json;"
        "from apps.insights.models import RelationshipInsight;"
        "rows = RelationshipInsight.objects.filter("
        f"relationship_id='{couple.rel}');"
        "print(json.dumps({'rows': rows.count(), 'shared': rows.filter("
        "shared_with_a=True).count()}))"
    )
    check(
        "S22: the row is retracted rather than quietly rewritten",
        stored["rows"] >= 1 and stored["shared"] == 0,
        json.dumps(stored),
    )


S22.body = _s22


SCENARIOS = [S21, S22]
