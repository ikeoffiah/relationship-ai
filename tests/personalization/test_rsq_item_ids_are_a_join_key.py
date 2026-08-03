"""D4 invariant (b): surviving RSQ item IDs are never renumbered.

The engineer is deleting eight of thirty questionnaire items. The tempting,
tidy follow-up — renumbering what is left to 1..22 — would be silent, would
pass every existing test, and would corrupt every response blob already in the
database plus every one written afterwards, because the ID *is* the join key.

These checks are written to pass both before the cut and after it, so they can
be merged now and be the thing that catches the cut going wrong. Where the two
states differ, the check branches on `cut_has_happened()` rather than being
weakened to whichever state is convenient.

Stdlib only — no DB, no Django, no running stack.
Run: `pytest tests/personalization/ -v`
"""

from __future__ import annotations

import sys

import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rsq_contract as rsq  # noqa: E402


def test_surviving_items_keep_their_exact_text():
    """The one that catches renumbering.

    If item 4 is deleted and everything after it shifts down, item 5's text
    lands on ID 4, item 6's on 5, and so on. Nothing errors. Every stored
    response now decodes to the wrong sentence. This check compares text to ID
    and fails on the first shift.
    """
    served = rsq.served_items()
    drifted = []
    for item_id, expected in rsq.SURVIVING_ITEMS.items():
        actual = served.get(item_id)
        if actual is None:
            continue  # absence is the next test's job
        if actual != expected:
            drifted.append(f"  id {item_id}\n    was: {expected!r}\n    now: {actual!r}")

    assert not drifted, (
        "RSQ item IDs have been renumbered.\n\n"
        + "\n".join(drifted)
        + "\n\n`docs/execution-plan.md` D4: **Never renumber surviving items**; "
        "the IDs are the join key to stored responses.\n\n"
        "`rsq_responses` is a JSONField keyed by these integers, with no "
        "foreign key and no validation. Every blob already in "
        "`personalization_profiles` was written against the old numbering, so "
        "a shift does not fail loudly — it silently rescores every existing "
        "user against the wrong questions, and keeps doing it for every new "
        "one. There is no way to detect it later from the data.\n\n"
        "Delete the item. Leave the gap in the numbering."
    )


def test_every_surviving_item_is_still_served():
    """The cut must remove exactly the eight named items, and no others."""
    served = set(rsq.served_items())
    missing = sorted(set(rsq.SURVIVING_ITEMS) - served)
    assert not missing, (
        f"RSQ items {missing} are no longer served, but D4 keeps them.\n\n"
        "D4 deletes exactly eight items: 4, 11, 13, 18, 20, 21, 23, 29. "
        "Anything else disappearing is out of scope for the cut.\n\n"
        "Item 26 in particular is now load-bearing: since the P0.1 fix it is "
        "the fifth item of the Dismissing scale, restored in place of the "
        "item-28 transcription error. Deleting it silently shortens that scale "
        "to four items and shifts every dismissing score."
    )


def test_the_cut_removes_the_eight_named_items_and_stops_there():
    """A half-done cut is worse than either state, so check it as a set."""
    served = set(rsq.served_items())
    still_present = sorted(rsq.ITEMS_TO_DELETE & served)

    if not rsq.cut_has_happened():
        assert still_present == sorted(rsq.ITEMS_TO_DELETE), (
            f"The RSQ cut is half-done: {still_present} of "
            f"{sorted(rsq.ITEMS_TO_DELETE)} are still served.\n\n"
            "Either all eight go or none do. A partial cut leaves the "
            "questionnaire in a state no stored blob and no scorer was written "
            "against."
        )
        return

    assert served == set(rsq.SURVIVING_ITEMS), (
        f"After the cut the questionnaire serves {sorted(served)}, but D4 "
        f"specifies exactly {sorted(rsq.SURVIVING_ITEMS)}.\n\n"
        f"Unexpectedly absent: {sorted(set(rsq.SURVIVING_ITEMS) - served)}\n"
        f"Unexpectedly present: {sorted(served - set(rsq.SURVIVING_ITEMS))}"
    )


def test_deleted_item_ids_are_never_reused():
    """A freed-up ID is not a spare ID.

    Reusing 4 for a new question is the same corruption as renumbering, with a
    smaller blast radius and a better disguise: every blob written before today
    still has a `"4"` in it, and it means the old question.
    """
    served = rsq.served_items()
    reused = sorted(
        item_id for item_id in rsq.ITEMS_TO_DELETE if item_id in served and rsq.cut_has_happened()
    )
    assert not reused, (
        f"Deleted RSQ item IDs {reused} are being served again with new text.\n\n"
        "Stored blobs still contain these keys, holding answers to the "
        "questions that used to have those IDs. Reusing the number silently "
        "reinterprets them. Allocate 31+ for new items; the numbering has gaps "
        "in it now and that is correct."
    )


def test_the_scorer_only_reads_items_the_questionnaire_serves():
    """The join key, checked from the other side.

    The scorer indexes `r[N]`. If N is not an item anyone was ever asked, the
    value it reads is the neutral default the scorer fills in — so the
    dimension quietly scores as if everyone answered 3, and nothing errors.
    """
    served = set(rsq.served_items())
    scored = rsq.scored_items()
    orphaned = sorted(scored - served)

    assert not orphaned, (
        f"`calculate_rsq_attachment_style` reads items {orphaned}, which the "
        "questionnaire does not serve.\n\n"
        "Nobody has ever answered these, so the scorer's missing-value default "
        "supplies a neutral 3 for each and the dimension they feed is computed "
        "from a constant. It will not raise. It will not look wrong. It will "
        "just be a made-up number in a report a clinician is reading.\n\n"
        "If this fired after the D4 cut, the scorer is still pointing at a "
        "deleted item."
    )


def test_the_scorer_never_reads_a_deleted_item():
    """The specific version of the above that the cut is about to risk."""
    reads_deleted = sorted(rsq.scored_items() & rsq.ITEMS_TO_DELETE)
    assert not reads_deleted, (
        f"The scorer reads deleted RSQ items {reads_deleted}.\n\n"
        "D4 deletes 4, 11, 13, 18, 20, 21, 23, 29 precisely because nothing "
        "scores them. If the D3 scoring fix wired one of them into a "
        "dimension, the item needs to come back into the questionnaire — or "
        "the dimension needs to be built from the items that survived."
    )


def test_no_new_item_is_collected_and_then_ignored():
    """Every question we ask has to earn itself.

    A ratchet, not a pass/fail. The unscored set may shrink freely; it may not
    grow. `product-assessment.md` §2.2 measured the onboarding at 40+ taps for
    two labels, and P1 is trying to cut it — a new item that feeds nothing is
    that problem arriving again, one question at a time.
    """
    unscored = set(rsq.served_items()) - rsq.scored_items()

    new_orphans = sorted(unscored - rsq.UNSCORED_AFTER_P0_1)
    assert not new_orphans, (
        f"RSQ items {new_orphans} are collected and never scored.\n\n"
        "Either wire them into a subscale or stop asking. An item that feeds "
        "nothing costs a tap in a flow whose length is already the product's "
        "biggest activation problem."
    )


def test_the_cut_does_not_leave_unscored_items_behind_unexamined():
    """A decision-forcing check, not an assertion of fact.

    D4 keeps 7, 14, 17, 26, 27, 30 as "the raw material for D3". Since then,
    `docs/engineering/rsq-scoring.md` established that 26 belongs to Dismissing
    (now scored) and that the rest are Collins & Read AAS items which this
    product does not compute and has no plan to.

    If both hold, D4's keep-list is preserving five questions that will never
    feed anything — in the flow P1 exists to shorten. That is a product call.
    This check exists so it gets made rather than defaulted into.
    """
    if not rsq.cut_has_happened():
        pytest.skip("D4 item cut has not landed yet.")

    unscored = set(rsq.served_items()) - rsq.scored_items()
    unexpected = sorted(unscored - rsq.AAS_REMAINDER_KEPT_BY_D4)

    assert not unexpected, (
        f"After the D4 cut, items {unexpected} are served and score nothing, "
        "and they are not the known AAS remainder "
        f"{sorted(rsq.AAS_REMAINDER_KEPT_BY_D4)}.\n\n"
        "Either the scorer lost a subscale it used to compute, or the cut kept "
        "items nobody has accounted for."
    )

    if unscored:
        pytest.skip(
            f"D4 cut landed. Items {sorted(unscored)} survive it and feed no "
            "score — the AAS remainder. Per docs/engineering/rsq-scoring.md "
            "this is correct for the four-prototype key, which makes D4's "
            '"raw material for D3" rationale stale. PM decision: either drop '
            "them in the P1 cut to 22-minus-5, or record why they stay."
        )


def test_the_contract_is_reading_a_real_questionnaire():
    """Guard against the AST helpers silently matching nothing."""
    served = rsq.served_items()
    assert len(served) >= 22, (
        f"Only {len(served)} RSQ items were parsed out of views.py. Expected 30 "
        "before the cut or 22 after. The parser is probably no longer finding "
        "the list, which would make every check in this file vacuous."
    )
    assert rsq.scored_items(), (
        "No scored item IDs were parsed out of the scorer. Every join-key "
        "check above is inspecting an empty set."
    )
