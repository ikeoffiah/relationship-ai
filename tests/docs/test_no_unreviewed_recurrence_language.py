"""Per-period language in a one-off business — flagged for review.

Companion to `test_cross_references_resolve.py`. That gate catches a pointer
that no longer resolves. This one catches the harder case it structurally
cannot see: a citation that resolves fine, a sentence that parses fine, and
arithmetic that is internally consistent — resting on a pricing model that was
replaced underneath it.

`go-to-market.md` §3.1 and §5.2 contradicted each other for days. §3.1: "gross
margin at $14.99/month is 92–96%" — a monthly margin against a monthly price,
neither of which has existed since D2. §5.2: $39-once, correctly. Each was
plausible in isolation, so neither read as wrong, and no link between them
existed to break.

**A hit here is a question, not a defect**, and that changes what this file
asserts. It does not claim per-period language is wrong — competitor prices
genuinely are "/month", vendor bills genuinely are per-month, and the QA
documents name the trial wall precisely in order to forbid it. What it asserts
is that **every occurrence has been looked at by someone who wrote down why**.
The allowlist is the record of that reading.

Fails in both directions: an unreviewed occurrence, a count that moved, or an
allowlist entry describing text that is no longer there.

Stdlib only. Run: `pytest tests/docs/ -v`
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import recurrence_lint as lint  # noqa: E402

COUNTS = lint.counts()
EXPECTED = {key: count for key, (count, _) in lint.REVIEWED_USES.items()}


def _quote(file: str, term_class: str, limit: int = 6) -> str:
    lines = lint.hits_for(file, term_class)[:limit]
    return "\n".join(f"      {h.file}:{h.line}  [{h.matched}]  {h.text[:96]}" for h in lines)


def test_every_per_period_unit_has_been_reviewed():
    """New per-period language must be triaged before it can land.

    This is the ongoing value. The existing corpus was swept by hand and the
    result is recorded in REVIEWED_USES; what this catches is the *next*
    sentence — the one written months after D2 by someone reasoning from a
    model that has not applied for a while.
    """
    unreviewed = sorted(key for key in COUNTS if key not in EXPECTED)

    assert not unreviewed, (
        "Per-period language appears in documents where it has not been "
        "reviewed:\n\n"
        + "\n\n".join(f"  {file}  [{term}]\n{_quote(file, term)}" for file, term in unreviewed)
        + "\n\n"
        "Since D2 the product sells one thing, once. A per-period unit is "
        "therefore suspect by construction — not wrong, suspect. Read the "
        "lines above and decide which:\n\n"
        "  * **A dead assumption.** The sentence is reasoning from the "
        "subscription. Fix the sentence. This is what the check is for: "
        "`go-to-market.md` §3.1 computed a gross margin against a monthly "
        "price for days while §5.2 modelled $39-once two sections away.\n"
        "  * **Legitimate.** Competitor pricing, a vendor bill, a COGS "
        "measurement, or a document naming the mechanic in order to forbid it. "
        "Add an entry to REVIEWED_USES with the count and a reason.\n\n"
        "The reason is the deliverable. An allowlist of bare paths records that "
        "someone silenced the check; a reason records that someone read it."
    )


def test_reviewed_counts_still_match():
    """A count that moved means a sentence was added or removed.

    Without counts, allowlisting `go-to-market.md` once would silence the most
    actively edited document in the repo — the one that held all five
    contradictions — permanently.
    """
    drifted = []
    for key, expected in sorted(EXPECTED.items()):
        actual = COUNTS.get(key, 0)
        if actual and actual != expected:
            file, term = key
            drifted.append(
                f"  {file}  [{term}]  reviewed {expected}, now {actual}\n{_quote(file, term)}"
            )

    assert not drifted, (
        "Per-period language has changed in documents that were reviewed:\n\n"
        + "\n\n".join(drifted)
        + "\n\n"
        "Read the lines and decide whether the new one is reasoning from the "
        "subscription. If it is legitimate, update the count in REVIEWED_USES "
        "— a one-character edit that requires having looked, which is the "
        "whole mechanism.\n\n"
        "If the count went *down*, something was removed and the entry just "
        "needs the new number."
    )


def test_reviewed_entries_have_not_gone_stale():
    """The other direction: an entry describing text that is no longer there.

    A reason that no longer corresponds to anything is worse than no entry —
    it is a standing statement that somebody checked something which has since
    been deleted, and it will be trusted.
    """
    stale = sorted(key for key in EXPECTED if key not in COUNTS)

    assert not stale, (
        "REVIEWED_USES describes per-period language that no longer exists:\n\n  "
        + "\n  ".join(f"{file}  [{term}]" for file, term in stale)
        + "\n\nDelete these entries. Each one is a recorded judgement about text "
        "that has since been removed."
    )


def test_every_reviewed_entry_states_a_reason():
    """The allowlist's whole value is the reasons in it."""
    thin = sorted(
        f"{file} [{term}]"
        for (file, term), (_, reason) in lint.REVIEWED_USES.items()
        if len(reason.strip()) < 25
    )
    assert not thin, (
        "These REVIEWED_USES entries have no real reason:\n  "
        + "\n  ".join(thin)
        + "\n\nThe reason is what a future reader uses to decide whether the "
        "judgement still holds. 'Legacy' and 'ok' do not survive contact with "
        "a pricing change."
    )


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------


def test_the_lint_is_neither_blind_nor_deafening():
    """Two signals from the manual sweep that found the original five.

    `go-to-market.md` held all five contradictions; `marketing-copy.md` came
    back clean. A detector that reverses either of those is mistuned, and this
    is the one check that would notice.
    """
    gtm = sum(n for (file, _), n in COUNTS.items() if file == "docs/go-to-market.md")
    assert gtm >= 20, (
        f"Only {gtm} per-period hits in go-to-market.md. That document holds the "
        "competitor price map, the unit-economics model and the record of five "
        "withdrawn contradictions. If the detector cannot see them, it has been "
        "narrowed past usefulness."
    )

    copy = sum(n for (file, _), n in COUNTS.items() if file == "docs/marketing-copy.md")
    assert copy <= 3, (
        f"{copy} per-period hits in marketing-copy.md, which came back clean on "
        "the manual sweep. The detector is now flagging ordinary sales copy, "
        "and a lint that cries wolf on the copy deck is a lint somebody turns "
        "off."
    )


@pytest.mark.parametrize(
    "sentence",
    [
        # The §3.1 contradiction: a monthly margin against a monthly price.
        "Gross margin at $14.99/month is 92–96%, which is not the constraint.",
        # The paid-install argument, sized 2–4× wrong in the flattering direction.
        "A paid install is worth $90–150 in first-year ARPU, so the CPI clears.",
        # The event schema still emitting a trial that does not exist.
        "The funnel events are `signup`, `trial start`, `purchase`.",
        # The comped subscription inside the couple-code mechanic.
        "A referred couple gets 30-day free trial access on redemption.",
        # Churn reasoning on a product with no renewal.
        "Monthly churn of 6–8% is the number that decides the model.",
    ],
)
def test_it_sees_the_sentences_that_actually_shipped(sentence):
    """The five the manual sweep found, as fixtures.

    Each of these was live in the corpus, internally consistent, and read as
    correct. If a future narrowing of the term list stops flagging one, the
    lint has lost the case it was built for.
    """
    assert lint.scan_text(sentence), (
        f"The detector no longer flags: {sentence!r}\n\n"
        "This is one of the five contradictions the manual recurrence sweep "
        "found. Narrowing TERM_CLASSES until these pass is how the lint stops "
        "working while continuing to be green."
    )


@pytest.mark.parametrize(
    "sentence",
    [
        # The senses that made `retention` unusable as a term.
        "Week-4 couple retention above 40% is the target.",
        "Session transcript retention is governed by the consent dimension.",
        # A pilot, not a subscription trial.
        "The facilitator asks for a trial with one cohort before committing.",
        # Ordinary product copy.
        "Both partners answer privately, and both unlock together.",
        "The assessment is $39, one payment, covering both partners.",
    ],
)
def test_it_stays_quiet_on_the_things_that_are_not_about_recurrence(sentence):
    """The other half. A lint that flags 'week-4 retention' in a plan whose own
    five numbers include week-4 retention is a lint that gets deleted in a
    week."""
    assert not lint.scan_text(sentence), (
        f"The detector flags a legitimate sentence: {sentence!r}\n\n"
        "False positives are the failure mode that kills this check. It earns "
        "its place by being read, and nobody reads a list that is mostly noise."
    )


def test_the_scan_still_reads_the_corpus():
    """Guard against the lint going vacuously green."""
    total = sum(COUNTS.values())
    assert 30 <= total <= 200, (
        f"{total} per-period hits across docs/. Expected roughly 70. Outside "
        "that band the term list has either stopped matching or started "
        "matching everything, and every assertion above is meaningless."
    )
