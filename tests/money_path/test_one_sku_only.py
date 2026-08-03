"""D2: one SKU, one price, one permanent entitlement flag.

`docs/execution-plan.md` D2 kills the tier structure outright — the $14.99/mo
and $89.99/yr Premium tiers, Bliss Together, the therapist-referred rate, the
separate Cohort License SKU, and the 30-day trial. What ships is:

    Bliss — $39, one payment, covers both partners. Perpetual access.

D2 also says the decision is reversible and that this is the point. Reversible
by decision is not the same as reversible by drift, and billing is where drift
is cheapest: a `subscription_status` column added "for later", a `trial_ends_at`
that nothing reads yet, a `tier` that is always `'standard'`. Each is one line,
each is defensible on its own, and together they rebuild the tier structure
without anyone deciding to.

The whole file skips while there is no billing code, and activates the moment
there is. See `docs/qa/money-path.md` for the full plan.

Run: `pytest tests/money_path/ -v` (stdlib only).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "safety"))

import crisis_surface_map as cmap  # noqa: E402

E2E_TEST = Path(__file__).parent / "test_checkout_e2e.py"

# `docs/specs/money-path-acceptance.md` §3.3.1 — the set of files containing an
# entitlement check, asserted as a set rather than a count.
#
# A count was the original criterion and it was re-baselined once already when
# D3.11 added the counsellor gate. A number that is wrong the moment a decision
# lands is a test somebody disables, which is worse than no test. A set makes
# adding a gate a visible line in a reviewed diff, and — the half a count
# misses — makes *removing* one fail too. Delete the counsellor gate and revenue
# stops silently; a count-based test would happily pass the swap.
#
# Placeholders until P0.2/P0.3/P0.11 land. The test below fails rather than
# skips if billing code appears while these are still placeholders.
ENTITLEMENT_CALL_SITES: set[str] = {
    "<report generation module>",  # P0.3
    "<certificate generation module>",  # P0.11
    # D3.11. Must gate the REPLY path, not session entry — a check on session
    # open would satisfy this test and violate the safety design. See
    # docs/specs/counsellor-paywall-copy.md §2.
    "<counsellor session gate>",
}

_PLACEHOLDER = "<"

# The vocabulary of a product D2 says we are not building.
FORBIDDEN_BY_D2 = [
    ("subscription", r"subscription[_]?(status|plan|tier|id|state)|is[_]?subscribed"),
    ("trial", r"trial[_]?(wall|expired|ends|active|remaining|started)"),
    ("tier", r"(price|pricing|plan|feature|subscription)[_]?tier|tier[_]?(id|name|level)"),
    ("renewal", r"\brenew(al|s|ed)?\b|auto[_]?renew|next[_]?billing"),
    ("dunning", r"\bdunning\b|failed[_]?(payment|charge|rebill)|retry[_]?charge"),
    ("proration", r"prorat(e|ed|ion)"),
    ("cancellation", r"cancel[_]?(subscription|at[_]?period[_]?end)|period[_]?end"),
]

COMPILED_D2 = [(name, re.compile(p, re.IGNORECASE)) for name, p in FORBIDDEN_BY_D2]


def _billing_files() -> list[Path]:
    """Source files that appear to be part of the billing surface."""
    return [
        path
        for path in cmap.all_dart_files() + cmap.all_python_files()
        if cmap.find_gates(cmap.read(path))
    ]


def test_billing_surface_contains_no_subscription_machinery():
    """D2's build-cost argument, kept honest.

    'No renewal, no dunning, no cancellation, no refund-on-subscription, no
    trial gate, no tier checks' is the reason a solo founder can ship this in
    three weeks. Every one of those that creeps back in is scope that was never
    costed and a test matrix nobody wrote.
    """
    billing = _billing_files()
    if not billing:
        pytest.skip("No billing code in the product yet (P0.2 unstarted).")

    violations = []
    for path in billing:
        text = cmap.read(path)
        for name, pattern in COMPILED_D2:
            for match in pattern.finditer(text):
                line_no = text.count("\n", 0, match.start()) + 1
                violations.append(f"{cmap.rel(path)}:{line_no} [{name}] {match.group(0)!r}")

    assert not violations, (
        "Subscription machinery has appeared in the billing surface, but D2 "
        "specifies one SKU with one permanent entitlement flag:\n\n  "
        + "\n  ".join(violations)
        + "\n\n`docs/execution-plan.md` D2 lists these as dead: renewal, "
        "dunning, cancellation, subscription refunds, trial gates, tier checks. "
        "Not deferred — dead.\n\n"
        "D2 is reversible by decision, and reversing it is a conversation with "
        "the PM about pricing. It is not a column added ahead of time in case "
        "it is wanted later. If a subscription is genuinely coming back, this "
        "test should be deleted in the same commit that reopens D2, deliberately."
    )


def test_entitlement_call_sites_match_the_allowlist():
    """Product acceptance §3.3.1. Fails on an unexpected addition *or* removal.

    The goal is not to count gates. It is that no new paid tier can appear
    without a decision being written down in a file called
    `money-path-acceptance.md` — and that an existing gate cannot quietly
    vanish.
    """
    billing = _billing_files()
    if not billing:
        pytest.skip("No billing code in the product yet (P0.2 unstarted).")

    placeholders = sorted(p for p in ENTITLEMENT_CALL_SITES if p.startswith(_PLACEHOLDER))
    assert not placeholders, (
        "Billing code exists but ENTITLEMENT_CALL_SITES still holds "
        f"placeholders: {placeholders}\n\n"
        "The allowlist is worthless until it names real module paths — a set of "
        "placeholders matches nothing and would fail every comparison below for "
        "the wrong reason. Replace them with the actual paths from P0.3, P0.11 "
        "and D3.11, then this test starts doing its job.\n\n"
        "This deliberately fails rather than skips: a skipped tripwire is how "
        "the gate would end up never being armed."
    )

    entitlement_files = {
        cmap.rel(path)
        for path in billing
        if any(rule == "entitlement" for _, rule, _ in cmap.find_gates(cmap.read(path)))
    }

    unexpected = sorted(entitlement_files - ENTITLEMENT_CALL_SITES)
    missing = sorted(ENTITLEMENT_CALL_SITES - entitlement_files)

    assert not unexpected, (
        "New entitlement check(s) in files not on the allowlist:\n  "
        + "\n  ".join(unexpected)
        + "\n\nEvery entitlement check is a decision about what is paid for. "
        "If this one is intended, add it to ENTITLEMENT_CALL_SITES here and to "
        "docs/specs/money-path-acceptance.md §3.3.1 — that is the point of the "
        "test, not an obstacle to it.\n\n"
        "Before you do: check it is not on a crisis path. See "
        "docs/qa/crisis-gating.md."
    )

    assert not missing, (
        "Entitlement check(s) have disappeared from:\n  "
        + "\n  ".join(missing)
        + "\n\nRemovals fail on purpose. Deleting a gate stops revenue silently "
        "— there is no error, no alert, and the product simply becomes free. "
        "If a gate was intentionally removed, delete its line here and record "
        "why in money-path-acceptance.md §3.3.1."
    )


def test_e2e_suite_exists_once_billing_lands():
    """The money path needs a test that spends money.

    Static checks cannot tell you whether $39 leaving someone's account results
    in an entitlement. Only an end-to-end run against processor test keys can,
    and the failure it is looking for — §4.3, payment succeeded and webhook
    lost — is one nobody hits until a stranger does.
    """
    if not _billing_files():
        pytest.skip("No billing code in the product yet (P0.2 unstarted).")

    assert E2E_TEST.exists(), (
        f"Billing code exists but {E2E_TEST.relative_to(cmap.REPO_ROOT)} does "
        "not.\n\n"
        "docs/qa/money-path.md §3 and §4 are the spec. The gate before taking "
        "real money is §8.\n\n"
        "The one that matters most is §4.3: the charge succeeds and the webhook "
        "never arrives. With a $39 one-off there is no next billing cycle to "
        "make it right through — the money left their account, no entitlement "
        "exists, and nothing in the system knows. Reconciliation is the test."
    )
