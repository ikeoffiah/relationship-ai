"""D4 invariant (a): stored response blobs stay readable, with no migration.

`docs/execution-plan.md` P0.1:

    Fix the RSQ scorer — score model-of-other, correct the 2x2 placement, keep
    old blobs readable without migration

Every row already in `personalization_profiles.rsq_responses` was written
against the 30-item questionnaire, by
`onboarding_viewmodel.dart:144` (`_rsqResponses[questionId.toString()] = value`),
so the keys are *strings*. After the cut those blobs will contain eight keys
for items that no longer exist. They must still score, unchanged, without
anybody writing a data migration.

These tests call the real scorer. Run them with the Django venv:

    backend-django/venv/bin/python -m pytest tests/personalization/ -v
"""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

import rsq_contract as rsq  # noqa: E402

from apps.personalization.tasks import calculate_rsq_attachment_style  # noqa: E402


# ---------------------------------------------------------------------------
# Old blobs must keep scoring
# ---------------------------------------------------------------------------


def test_a_thirty_item_blob_written_before_the_cut_still_scores():
    """The headline invariant. A blob from today, scored after the cut."""
    style, scores = calculate_rsq_attachment_style(rsq.legacy_blob_30_items())

    assert style in rsq.VALID_STYLES, (
        f"A pre-cut 30-item response blob scored to {style!r}, which is not one "
        f"of {sorted(rsq.VALID_STYLES)}.\n\n"
        "Rows in this shape are already in the database. P0.1 requires them to "
        "remain readable with no migration."
    )
    assert set(scores) == rsq.VALID_STYLES, (
        f"The scorer returned dimensions {sorted(scores)}; the four attachment "
        f"styles are {sorted(rsq.VALID_STYLES)}. `portrait.py` and "
        "`build_modifiers` both key off these names, and the facilitator "
        "report will too."
    )
    assert all(isinstance(v, (int, float)) for v in scores.values())


def test_keys_for_deleted_items_are_tolerated_and_ignored():
    """The eight deleted IDs are still in every old blob. They must be inert.

    Not an error, not a KeyError, and — the part worth checking — not silently
    folded into a score. If the scorer starts reading a deleted item, users who
    onboarded before the cut get a dimension computed from an answer that users
    who onboarded after it never gave.
    """
    baseline = {str(i): 3 for i in sorted(rsq.SURVIVING_ITEMS)}

    with_deleted_low = dict(baseline, **{str(i): 1 for i in sorted(rsq.ITEMS_TO_DELETE)})
    with_deleted_high = dict(baseline, **{str(i): 5 for i in sorted(rsq.ITEMS_TO_DELETE)})

    _, scores_low = calculate_rsq_attachment_style(with_deleted_low)
    _, scores_high = calculate_rsq_attachment_style(with_deleted_high)

    assert scores_low == scores_high, (
        "Changing only the answers to deleted RSQ items "
        f"{sorted(rsq.ITEMS_TO_DELETE)} changed the attachment scores:\n"
        f"  all 1s: {scores_low}\n"
        f"  all 5s: {scores_high}\n\n"
        "D4 deletes these items because nothing scores them. If something now "
        "does, then post-cut users — who are never asked these questions — get "
        "that input filled in with a default while pre-cut users get their real "
        "answer. Two populations, two instruments, one score column."
    )


def test_unknown_and_junk_keys_do_not_crash_the_scorer():
    """Blobs in the wild are not clean.

    `rsq_responses` is an unvalidated JSONField that the client writes to
    directly. Anything that has ever been in one is now permanent.
    """
    messy = dict(rsq.legacy_blob_30_items())
    messy.update({"99": 4, "abc": 2, "": 1, "0": 3})

    style, scores = calculate_rsq_attachment_style(messy)
    assert style in rsq.VALID_STYLES
    assert set(scores) == rsq.VALID_STYLES


def test_string_and_integer_keys_score_identically():
    """The client writes string keys; fixtures and tests write ints. Both are
    in the database. They have to mean the same thing."""
    as_strings = rsq.legacy_blob_30_items()
    as_ints = {int(k): v for k, v in as_strings.items()}

    assert calculate_rsq_attachment_style(as_strings) == calculate_rsq_attachment_style(as_ints)


def test_a_partial_blob_from_an_abandoned_onboarding_is_read_not_crashed():
    """P1 makes the RSQ progressive with no hard gate, so partial blobs stop
    being an edge case and become the normal state.

    'Readable' means it does not raise and returns the four dimensions. It
    does *not* mean it must produce a label — below `MIN_ITEMS_TO_SCORE` the
    scorer correctly declines to, which is the QA-1 fix.
    """
    partial = {"1": 5, "5": 4, "12": 5, "24": 4}
    style, scores = calculate_rsq_attachment_style(partial)

    assert set(scores) == rsq.VALID_STYLES
    assert style is None or style in rsq.VALID_STYLES, (
        f"A 4-item partial blob scored to {style!r}, which is neither None nor "
        f"one of {sorted(rsq.VALID_STYLES)}."
    )


def test_no_migration_rewrites_stored_response_blobs():
    """'Without migration' checked as a fact about the repo, not a promise.

    A `RunPython` that renumbers keys would satisfy every other test in this
    file while doing exactly the thing P0.1 forbids — and it would run once,
    irreversibly, against production.
    """
    migrations_dir = rsq.MIGRATIONS_DIR
    assert migrations_dir.exists(), f"{migrations_dir} is missing"

    offenders = []
    for path in sorted(migrations_dir.glob("0*.py")):
        text = path.read_text(encoding="utf-8")
        if "rsq_responses" in text and "RunPython" in text:
            offenders.append(path.name)

    assert not offenders, (
        f"Migrations {offenders} run Python against `rsq_responses`.\n\n"
        "P0.1 requires old blobs to stay readable *without* a migration. A data "
        "migration over this column rewrites answers people gave, in place, "
        "with no way back — and if the mapping in it is wrong, the damage is "
        "silent and total.\n\n"
        "If a migration is genuinely required, that is a decision to take to "
        "the PM with a backup plan, not something to land inside the cut."
    )


# ---------------------------------------------------------------------------
# Regression locks on the two defects QA raised and P0.1 fixed
# ---------------------------------------------------------------------------


def test_an_empty_blob_does_not_report_secure_attachment():
    """QA-1, fixed in P0.1 (09f8feb). Locked here so it cannot come back.

    Before the fix, `calculate_rsq_attachment_style({})` returned
    `('secure', {all 3.0})`: every missing item defaulted to a neutral 3, all
    four prototypes tied at 3.0, and `max()` broke the tie by dict insertion
    order — `secure` was declared first. Someone who answered nothing was told
    they were securely attached, as confidently as someone who answered thirty.

    That output feeds `portrait.py`, `build_modifiers`, and shortly a $39
    report a facilitator teaches from. It becomes a live mislabelling rather
    than a latent one the moment P1 removes the hard onboarding gate.
    """
    style, scores = calculate_rsq_attachment_style({})

    assert style is None, (
        f"An empty response blob produced attachment style {style!r} with "
        f"scores {scores}. Answering nothing must not produce a label — least "
        "of all the reassuring one.\n\n"
        "If the return contract changed from None to a sentinel, check every "
        "consumer first: portrait.py and engagement/services.py guard with "
        "`(profile.attachment_style or '')` and chat/assist.py with "
        "`if getattr(...)`, so a truthy sentinel would inject "
        "'attachment style: unknown' straight into a counseling prompt."
    )


def test_a_tie_at_the_top_is_not_reported_as_a_finding():
    """The general form of QA-1: undifferentiated answers are not a result."""
    flat = {str(i): 3 for i in range(1, 31)}
    style, scores = calculate_rsq_attachment_style(flat)

    top = sorted(scores.values(), reverse=True)
    if len(top) > 1 and top[0] == top[1]:
        assert style is None, (
            f"Prototypes tied at {top[0]} but the scorer still reported "
            f"{style!r}. A tie is what an undifferentiated set of answers looks "
            "like; picking one anyway is how 'secure' used to happen."
        )


def test_dismissing_reads_item_26_and_not_item_28():
    """QA-2, fixed in P0.1. Locked here because it is a one-character regression.

    Griffin & Bartholomew score Dismissing from 2, 6, 19, 22, **26**. The
    shipped version read `(6 - r[28])` — item 28 reversed, which is a self-model
    anxiety item already used by the secure scale with the same sign. Because
    the term appeared identically in both scales it cancelled between them,
    costing the key its power to separate the two prototypes that most need
    separating.

    Detected behaviourally rather than by reading the source, so it holds
    however the scorer is next restructured.
    """
    baseline = {str(i): 3 for i in range(1, 31)}

    def dismissing(**overrides):
        blob = dict(baseline, **{str(k): v for k, v in overrides.items()})
        return calculate_rsq_attachment_style(blob)[1]["dismissive-avoidant"]

    base = dismissing()

    assert dismissing(**{"26": 5}) > base, (
        "Raising item 26 ('I prefer not to depend on others') did not raise the "
        "dismissing score. It is the fifth item of the published Dismissing "
        "scale; if it no longer feeds that scale, the item-28 transcription "
        "error has come back."
    )
    assert dismissing(**{"28": 5}) == base, (
        "Item 28 ('I worry about having others not accept me') still moves the "
        "dismissing score. It is a self-model anxiety item with no place in "
        "that scale — see docs/engineering/rsq-scoring.md."
    )
