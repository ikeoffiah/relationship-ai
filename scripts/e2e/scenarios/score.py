"""§3.5 — the connection score.

One number on the home screen, and three properties it has to have to deserve
being there.

The one that makes it a *relationship* score rather than an engagement score is
S14: identical volume, one couple mutual and one one-sided, must not produce
the same number. The one that makes it safe is S15: the daily check-in asks
each partner privately how connected they feel, and averaging those two answers
into a shared number publishes one partner's answer to the other by arithmetic.
"""

import requests

from .runner import DJANGO, Couple, Scenario, check, shell, shell_json

# ── S14 — Mutual vs one-sided ───────────────────────────────────────────────

S14 = Scenario(
    "S14",
    "Mutual vs one-sided at identical volume",
    note="the property that makes it a relationship score, not an engagement score",
)

_LINES = [
    "morning",
    "how did the meeting go",
    "want me to cook tonight",
    "I picked up the thing you asked about",
    "that was a long day",
    "thinking about you",
    "shall we watch something",
    "what time are you back",
    "the cat has knocked the plant over again",
    "night x",
    "did you sleep ok",
    "I'll be home about six",
    "do you fancy a walk later",
    "that made me laugh",
    "love that photo",
    "see you in a bit",
    "call me when you can",
    "all sorted",
    "thanks for doing that",
    "sleep well",
]


def _s14(couple):
    """Two couples, twenty messages each. Only the distribution differs.

    Volume is held identical on purpose. If the score rewarded activity, both
    couples would land in the same place, and the number would be measuring how
    much the app is used rather than how the relationship is going — which is
    the failure mode every engagement metric has, and the one this design is
    supposed to avoid.
    """
    mutual = couple
    for index, text in enumerate(_LINES):
        mutual.send("a" if index % 2 == 0 else "b", text)

    one_sided = Couple("s14-onesided")
    for text in _LINES:
        one_sided.send("a", text)

    parts_mutual = mutual.score_components()
    parts_one_sided = one_sided.score_components()

    check(
        "S14: both couples sent the same number of messages",
        parts_mutual["events"] == parts_one_sided["events"] == len(_LINES),
        f"{parts_mutual['events']} vs {parts_one_sided['events']}",
    )
    check(
        "S14: the mutual couple's reciprocity component is materially higher",
        parts_mutual["mutuality"] - parts_one_sided["mutuality"] > 0.5,
        f"{parts_mutual['mutuality']:.2f} vs {parts_one_sided['mutuality']:.2f}",
    )
    check(
        "S14: the one-sided couple scores no reciprocity at all",
        parts_one_sided["mutuality"] == 0.0,
        str(parts_one_sided["mutuality"]),
    )

    # And the same thing said in the number the couple actually sees.
    raw_mutual = _raw_score(mutual)
    raw_one_sided = _raw_score(one_sided)
    check(
        "S14: and the score itself is materially higher",
        (raw_mutual or 0) - (raw_one_sided or 0) >= 15,
        f"{raw_mutual} vs {raw_one_sided}",
    )


def _raw_score(couple):
    value = shell(
        "from apps.personalization import connection;"
        "from apps.relationships.models import Relationship;"
        f"print(connection.compute(Relationship.objects.get(id='{couple.rel}')))"
    )
    return None if value == "None" else int(value)


S14.body = _s14


# ── S15 — Privacy ───────────────────────────────────────────────────────────

S15 = Scenario(
    "S15",
    "Identical behaviour, opposite private answers",
    note="unit-tested already; worth having end to end because of how it would break",
)


def _check_in(couple, who, value):
    return requests.post(
        f"{DJANGO}/api/v1/engagement/check-in",
        headers=couple.headers(who),
        json={"connection_score": value, "mood": "okay"},
        timeout=30,
    ).status_code


def _s15(couple):
    """Two couples who behaved identically and feel completely differently.

    Already covered by a unit test. It is here as well because of the *shape*
    of the failure: nobody would ever set out to publish one partner's private
    answer to the other. It would arrive as someone adding `connection_score`
    to the components dict, because it is right there and it is obviously
    relevant, and every existing test would stay green.
    """
    happy = couple
    unhappy = Couple("s15-unhappy")

    for pair_ in (happy, unhappy):
        for index, text in enumerate(_LINES[:12]):
            pair_.send("a" if index % 2 == 0 else "b", text)

    # Same behaviour, opposite private feelings. Five is "we are great", one is
    # "I am barely here".
    _check_in(happy, "a", 5)
    _check_in(happy, "b", 5)
    _check_in(unhappy, "a", 1)
    _check_in(unhappy, "b", 1)

    parts_happy = happy.score_components()
    parts_unhappy = unhappy.score_components()
    check(
        "S15: the components are identical",
        parts_happy == parts_unhappy,
        f"{parts_happy} vs {parts_unhappy}",
    )
    check(
        "S15: and so is the number",
        _raw_score(happy) == _raw_score(unhappy),
        f"{_raw_score(happy)} vs {_raw_score(unhappy)}",
    )

    # The structural half of the same assertion. The components are counts of
    # things both partners watched happen; the moment one of them is a *value*
    # somebody typed privately, the arithmetic publishes it.
    check(
        "S15: nothing in connection.py reads a check-in value",
        not _reads_check_in_value(),
        "connection_score or .mood is referenced in the score's own module"
        if _reads_check_in_value()
        else "behaviour only",
    )


def _reads_check_in_value():
    return shell(
        "import inspect;"
        "from apps.personalization import connection;"
        "src=inspect.getsource(connection);"
        "print('connection_score' in src or '.mood' in src)"
    ) == "True"


S15.body = _s15


# ── S16 — Cold start and recovery ───────────────────────────────────────────

S16 = Scenario(
    "S16",
    "Cold start, then quiet, then feature",
    note="a new couple is shown nothing rather than a zero",
)


def _s16(couple):
    """Hidden, then quiet, then feature — and honest in between.

    ``emphasis`` is the part that matters. The morning after a fight, a low
    number is the least helpful thing that could be on the screen, so the home
    screen leads with help instead. But it must lead with help rather than with
    a *flattering* number: `quiet` is the honest answer to a bad fortnight, and
    the direction shown alongside it has to be the real one.
    """
    fresh = couple.connection("a")
    check(
        "S16: a brand new couple is shown nothing rather than a zero",
        fresh.get("score") is None and fresh.get("emphasis") == "hidden",
        str(fresh),
    )
    check(
        "S16: and both partners see the same nothing",
        couple.connection("b") == fresh,
        str(couple.connection("b")),
    )

    # A low-activity fortnight: enough events to clear MIN_EVENTS, nothing like
    # enough to score well.
    for index in range(8):
        couple.send("a" if index % 2 == 0 else "b", _LINES[index])

    quiet = couple.refresh_score()
    check(
        "S16: a thin fortnight reads as quiet rather than hidden",
        quiet.get("score") is not None and quiet.get("emphasis") == "quiet",
        str(quiet),
    )

    # Now they turn up: both check in, both say thank you, actions get done.
    _seed_recovery(couple)

    # The score is smoothed at 0.85, so it takes several nightly runs to move —
    # which is the design, not a delay to work around. Running the job a few
    # times is running a few days.
    for _ in range(8):
        recovered = couple.refresh_score()

    check(
        "S16: sustained effort lifts it to feature",
        recovered.get("emphasis") == "feature",
        str(recovered),
    )

    # `direction` is weekly, never daily — a daily delta is noise carrying
    # emotional weight — so every point above landed in one ISO week and the
    # direction stayed None throughout. Which means the assertion above proves
    # nothing about it. Give the series a real previous week and ask again.
    #
    # Both ways round, because the property is honesty rather than optimism:
    # the number is allowed to go quiet on a bad fortnight, and it is not
    # allowed to say "steady" about a fall.
    risen = _with_previous_week(couple, value=recovered["score"] - 20)
    check(
        "S16: a rise across weeks reports up",
        risen.get("direction") == "up",
        f"{risen.get('direction')} from {recovered['score'] - 20} to {risen.get('score')}",
    )

    fallen = _with_previous_week(couple, value=recovered["score"] + 20)
    check(
        "S16: and a fall is reported as a fall, not smoothed into steady",
        fallen.get("direction") == "down",
        f"{fallen.get('direction')} from {recovered['score'] + 20} to {fallen.get('score')}",
    )

    check(
        "S16: both partners still see the same number",
        couple.connection("a") == couple.connection("b"),
        f"{couple.connection('a')} vs {couple.connection('b')}",
    )


def _with_previous_week(couple, value):
    """Give the stored series a point in the week before, and read it back.

    The trend is one point per week by design, so there is no way to produce a
    second point inside a single run other than writing one.
    """
    return shell_json(
        "import json;"
        "from datetime import timedelta;"
        "from django.utils import timezone;"
        "from apps.personalization import connection;"
        "from apps.personalization.models import ConnectionScore;"
        f"row=ConnectionScore.objects.get(relationship_id='{couple.rel}');"
        "last=timezone.now() - timedelta(days=7);"
        "current=[p for p in row.series if p['week'] == timezone.now().strftime('%Y-W%W')];"
        f"row.series=[{{'week': last.strftime('%Y-W%W'), 'value': {value}}}] + current;"
        "row.save(update_fields=['series']);"
        f"print(json.dumps(connection.presentation('{couple.rel}')))"
    )


def _seed_recovery(couple):
    """A fortnight of both partners turning up.

    Written straight to the database rather than through fourteen days of
    endpoints: check-ins are one per day per person, so there is no way to
    produce a fortnight of them through the API inside one run. The rows are
    the same rows the endpoints write.
    """
    return shell_json(
        "import json;"
        "from datetime import timedelta;"
        "from django.utils import timezone;"
        "from apps.engagement.models import ("
        "GratitudeMoment, MicroActionLog, MicroActionTemplate, RelationshipCheckIn);"
        "from apps.relationships.models import Relationship;"
        f"r=Relationship.objects.get(id='{couple.rel}');"
        f"a={couple.user_expr('a')};"
        f"b={couple.user_expr('b')};"
        "today=timezone.localtime().date();"
        # One row per person per day: both models carry a (user, date_key)
        # unique constraint, which is the product saying a check-in is a daily
        # pulse rather than something you can farm.
        "days=[(today - timedelta(days=d)).isoformat() for d in range(10)];"
        "t,_=MicroActionTemplate.objects.get_or_create("
        "text='ask them how their day actually went', defaults={'category':'e2e'});"
        "made=0;"
        "made+=len([RelationshipCheckIn.objects.create("
        "relationship=r,user=u,connection_score=4,mood='good',date_key=k)"
        " for k in days for u in (a,b)]);"
        "made+=len([GratitudeMoment.objects.create("
        "relationship=r,user=u,kind='gratitude',text='thank you for yesterday')"
        " for k in days[:4] for u in (a,b)]);"
        "made+=len([MicroActionLog.objects.create("
        "relationship=r,user=u,template=t,date_key=k,completed=True)"
        " for k in days[:5] for u in (a,b)]);"
        "print(json.dumps(made))"
    )


S16.body = _s16


SCENARIOS = [S14, S15, S16]
