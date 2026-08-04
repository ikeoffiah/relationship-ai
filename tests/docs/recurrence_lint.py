"""Find per-period language in a business that sells one thing, once.

Sibling detector to `doc_reference_scan.py`, aimed at a failure the
cross-reference checker structurally cannot see.

That one catches a **broken pointer**. This one catches a **valid citation
resting on a dead assumption** — where the reference resolves, the sentence
parses, the arithmetic is internally consistent, and only the pricing model
underneath has been replaced. `go-to-market.md` §3.1 and §5.2 contradicted each
other for days: §3.1 asserting "gross margin at $14.99/month is 92–96%", a
monthly margin against a monthly price, while §5.2 correctly modelled $39-once.
Each was internally plausible. Neither looked wrong on its own, and nothing
linked them.

The detector is blunt on purpose: **since D2, any sentence carrying a
per-period unit is suspect by construction.** A grep for that found five live
contradictions in about a minute, including an anti-paid-install argument sized
on $90–150 first-year ARPU when the real figure is $39 once — a number 2–4×
wrong in the direction that made paid installs look better than they are.

A hit is a **question, not a defect**. Plenty of per-period language is
correct: competitor pricing genuinely is "/month", vendor costs genuinely are
per-month, and the QA documents describe the trial wall precisely in order to
forbid it. The allowlist is where that judgement is recorded, one reason per
entry — so what this gate really enforces is that somebody looked.

Stdlib only.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = REPO_ROOT / "docs"


# ---------------------------------------------------------------------------
# What counts as per-period language
# ---------------------------------------------------------------------------

# Four classes, deliberately narrower than the founding grep.
#
# **`retention` is not here, and that is a considered removal.** It was on the
# original list and it is by a wide margin the noisiest term in this corpus: 60+
# hits across 12 files, essentially all of them one of two senses that have
# nothing to do with recurring revenue — *data* retention (`session-retention-
# wording.md` is entirely about what we keep from a session) and *week-4 couple
# retention*, which is one of the five numbers in the plan and is a perfectly
# good metric for a one-off business. Keeping it would have meant allowlisting
# a dozen files on day one, and an allowlist that large on day one is a gate
# nobody reads.
#
# Bare `subscription`, `monthly` and `trial` were narrowed for the same reason:
# most of their occurrences are documents correctly describing the subscription
# we *stopped* selling. The shapes kept below are the ones that are hard to
# write by accident.
TERM_CLASSES = {
    # "$14.99/mo", "$90 per year" — our own price with a period attached is the
    # single highest-signal shape, and it is where the §3.1 contradiction lived.
    "price-per-period": r"[$₦£€]\s?[\d.,]+\s*(?:/|per\s+)\s*(?:mo\b|month|yr\b|year|annum|6mo)",
    # Metrics that only mean anything across renewals.
    "unit-economics": (
        r"\bLTV\b|\bARPU\b|\bMRR\b|\bARR\b|lifetime value|\bchurn|\brenewals?\b|auto[- ]renew"
    ),
    # The trial mechanic D2 removed. Narrow shapes only: "asks for a trial"
    # meaning a pilot is legitimate and common in the facilitator channel.
    "trial-mechanic": (
        r"free trial|trial[ _]start|trial\s*(?:→|->|to)\s*paid|trial conversion"
        r"|\d+[- ]day\s+(?:free\s+)?trial|trial period|trial expir|trial wall"
    ),
    # Revenue that arrives more than once.
    "recurring-sku": (
        r"\bper[- ]couple per\b|\bsubscribers?\b|\brecurring revenue\b"
        r"|\bsubscription (?:tier|price|plan|revenue|ARPU)"
    ),
}

COMPILED = {name: re.compile(p, re.IGNORECASE) for name, p in TERM_CLASSES.items()}


# ---------------------------------------------------------------------------
# Reviewed uses
# ---------------------------------------------------------------------------

# (document, term class) -> (expected occurrences, why it is legitimate)
#
# Counts are part of the key on purpose. Without them, allowlisting
# `("go-to-market.md", "price-per-period")` once would silence that file
# forever — and `go-to-market.md` is both the most actively edited document and
# the one that held all five contradictions. With them, a *new* per-period
# sentence moves the number and asks its question, while the existing reviewed
# ones stay quiet.
#
# Updating a count is a one-character edit. Making it requires reading the line
# that moved it, which is the entire point.
REVIEWED_USES: dict[tuple[str, str], tuple[int, str]] = {
    # --- Reviewed 2026-08-03, after marketing's D3.56 recurrence sweep -------
    (
        "docs/go-to-market.md",
        "price-per-period",
    ): (12, "Competitor price map (§2.2: Paired $14.99/mo, Relish $99.99/6mo) plus the "
        "dead-tier list in §5.2 and the D3.56 sweep notes, which quote the removed "
        "monthly figures in order to record that they were removed."),
    (
        "docs/go-to-market.md",
        "unit-economics",
    ): (13, "The §6.0 model and §9's churn discussion, both now explicitly reasoning "
        "about why a one-off has no churn problem, plus the D3.56 annotations."),
    (
        "docs/go-to-market.md",
        "trial-mechanic",
    ): (9, "Industry trial→paid benchmarks quoted as market context, and the record of "
        "the 30-day trial mechanic D2 removed."),
    (
        "docs/go-to-market.md",
        "recurring-sku",
    ): (4, "Describes the subscription model that was considered and rejected."),
    (
        "docs/execution-plan.md",
        "price-per-period",
    ): (6, "D2 lists the dead tiers by price ($14.99/mo, $89.99/yr, $49/mo) so nobody "
        "rebuilds them; §5 compares against Paired's live $14.99/month; and the "
        "recurrence-sweep record at the end quotes the withdrawn figures in order to "
        "withdraw them."),
    (
        "docs/execution-plan.md",
        "unit-economics",
    ): (10, "The $100k ARR target and the recurring-vs-one-off comparison in §2, which "
        "is the argument for why the 12-month number moved."),
    (
        "docs/execution-plan.md",
        "trial-mechanic",
    ): (4, "D2's kill list, naming the 30-day trial mechanic explicitly."),
    (
        "docs/execution-plan.md",
        "recurring-sku",
    ): (4, "The recurring-revenue comparison that justifies the ~2,564-sales figure."),
    # --- Vendor and infrastructure costs, which genuinely are per-month ------
    (
        "docs/safety/classifier-upgrade.md",
        "price-per-period",
    ): (1, "Hosting cost for a fine-tuned classifier — a vendor bill, not our price."),
    (
        "docs/qa/load.md",
        "recurring-sku",
    ): (1, "Measured infrastructure cost per couple per month. A COGS measurement is "
        "per-period regardless of how the product is sold."),
    (
        "docs/daily-questions.md",
        "recurring-sku",
    ): (1, "Generation cost per couple per week — again COGS, not price."),
    # --- Documents describing the mechanic in order to forbid it ------------
    (
        "docs/qa/crisis-gating.md",
        "trial-mechanic",
    ): (1, "Quotes D7 verbatim: 'no paywall, no trial wall'. Naming the thing is the "
        "point of the sentence."),
    (
        "docs/marketing-copy.md",
        "trial-mechanic",
    ): (1, "Same D7 quotation, in the copy deck's own constraints."),
    (
        "docs/qa/money-path.md",
        "trial-mechanic",
    ): (1, "Lists trial expiry among the failure modes explicitly out of scope under D2."),
    (
        "docs/qa/money-path.md",
        "unit-economics",
    ): (3, "Names renewal and dunning as out of scope, and as forbidden vocabulary the "
        "one-SKU guard test asserts against."),
    # --- This lint's own documentation, which has to quote what it catches ---
    #
    # Unavoidable, and the reason a detector like this needs an allowlist rather
    # than a ban: the only way to explain the §3.1 contradiction is to reproduce
    # it. Same shape as `docs/specs/README.md` §6 having to cite the dead §5.6 as
    # its worked example.
    (
        "docs/qa/stale-references.md",
        "price-per-period",
    ): (1, "Quotes the §3.1 contradiction ('gross margin at $14.99/month is 92–96%') "
        "verbatim, as the worked example of what this lint is for."),
    (
        "docs/qa/stale-references.md",
        "unit-economics",
    ): (1, "Quotes the $90–150 first-year ARPU figure that made paid installs look "
        "2–4× better than they are."),
    (
        "docs/qa/stale-references.md",
        "trial-mechanic",
    ): (2, "The D7 'trial wall' quotation, and the `trial_start` event named in the "
        "known-limits section as an example of what a docs-only scan misses."),
    (
        "docs/qa/stale-references.md",
        "recurring-sku",
    ): (1, "Explains why `retention` was dropped from the term list — the sentence "
        "distinguishing the two innocent senses from recurring revenue."),
    (
        "docs/specs/capability-claims-audit.md",
        "unit-economics",
    ): (1, "Inside the '*Original finding, for the record:*' block recording the Cohort "
        "License ladder — a deliberate historical record, already marked as such for "
        "the cross-reference checker."),
}


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------

_FENCE = re.compile(r"^\s*(```|~~~)")


@dataclass(frozen=True)
class Hit:
    file: str
    line: int
    term_class: str
    matched: str
    text: str


def _scannable_lines(path: Path) -> list[tuple[int, str]]:
    """Lines outside fenced code blocks, with 1-based numbers.

    Code samples are excluded for the same reason as in the cross-reference
    scan: the one-SKU guard test's own forbidden-vocabulary list is a code
    block full of the exact words this lint looks for.
    """
    out, in_fence = [], False
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append((i, line))
    return out


def scan() -> list[Hit]:
    """Every per-period unit in `docs/**`."""
    hits: list[Hit] = []
    for path in sorted(DOCS.rglob("*.md")):
        rel = path.resolve().relative_to(REPO_ROOT).as_posix()
        for line_no, line in _scannable_lines(path):
            for name, pattern in COMPILED.items():
                m = pattern.search(line)
                if m:
                    hits.append(Hit(rel, line_no, name, m.group(0), line.strip()))
    return hits


def scan_text(text: str, file: str = "<memory>") -> list[Hit]:
    """The same detector, over a string. Used by the calibration tests."""
    hits: list[Hit] = []
    in_fence = False
    for line_no, line in enumerate(text.splitlines(), 1):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for name, pattern in COMPILED.items():
            m = pattern.search(line)
            if m:
                hits.append(Hit(file, line_no, name, m.group(0), line.strip()))
    return hits


def counts() -> Counter:
    """Occurrences per (document, term class)."""
    return Counter((h.file, h.term_class) for h in scan())


def hits_for(file: str, term_class: str) -> list[Hit]:
    return [h for h in scan() if h.file == file and h.term_class == term_class]
