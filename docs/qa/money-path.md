# The money path — E2E test plan

Owner: QA. Written 2026-08-03 against `docs/execution-plan.md` D1, D2 and P0.2.
This is P0.8.

**Revised 2026-08-03 (2): the couple-code referral is being redesigned.** The
shipped mechanic gives a referred couple "30 days free", comping a subscription
that no longer exists.

That is the same dead-assumption class the recurrence lint looks for, expressed
as a mechanic rather than a sentence — see `docs/qa/stale-references.md` §3.
**Do not write acceptance criteria against the 30-day version.** When the replacement lands, the criteria it needs are §4.1 (double
redemption), §4.2 (revoked code) and §5 (entitlement permanence) — none of which
depend on what the referral grants.

**Revised 2026-08-03: Paystack is cut** (founder decision — global SaaS, not a
Nigeria play). Stripe only. The Paystack-specific criteria are struck below
rather than deleted, because the kobo-vs-cents and raw-body-signature traps they
name are the ones any second processor will bring back, and this is where
somebody will look on the day one is added.

**The implementation does not exist yet.** `grep -ril "stripe\|paystack\|
entitlement"` over `mobile/lib`, `backend-django/apps` and `backend-fastapi/app`
returns nothing on 2026-08-03 — verified, not assumed. So this document is the
spec the engineer must satisfy, written before the code so the code can be
built against it. What can be tested today is in §7.

## The SKU

```
Bliss — $39, one payment, covers both partners. Perpetual access.
```

One SKU, one price, one permanent entitlement flag. No subscription, no tiers,
no trial, no renewal (D2). A 30-couple cohort is 30 × $39 = $1,170, transacted
as one facilitator-issued **batch of redemption codes**.

Explicitly **not** in scope, because they no longer exist: renewal, dunning,
failed rebill, proration, cancellation, subscription refunds, trial expiry,
tier upgrade/downgrade.

---

## 1. The path, and where it breaks

```
   [1] checkout                [2] payment              [3] webhook
      Stripe        ──────>  processor charges  ────>  our endpoint
  session created              the card                  receives event
        │                                                     │
        │                                                     ▼
        │                                            [4] code(s) issued
        │                                          1 for a couple, N for a cohort
        │                                                     │
        ▼                                                     ▼
   buyer's receipt   <─────────────────────────────  [5] delivered to buyer
                                                              │
                                                              ▼
                                                     [6] redeemed in app
                                                              │
                                                              ▼
                                                  [7] entitlement on the ACCOUNT
                                                              │
                                                              ▼
                                                     [8] premium unlocked
                                                        for BOTH partners
```

Every arrow is a place the money and the access can part company. Steps 3 and 7
are where it actually happens.

---

## 2. What the engineer must build for this to be testable

These are testability requirements, not design preferences. Without them the
failure modes in §4 cannot be asserted on.

1. **A `purchase` record created at step 1, not step 3.** If the row only
   appears when the webhook arrives, a lost webhook leaves no trace that anyone
   ever tried to pay, and reconciliation has nothing to reconcile against. The
   record starts `pending` and moves to `paid`.
2. **Webhook handlers idempotent on the processor's event ID.** Stripe
   retries. Processing the same event twice must produce one
   purchase, one batch, and the same codes.
3. **Redemption is a single atomic transaction** — check-unused and mark-used
   in one statement or one locked transaction. Two taps on a slow connection is
   the normal case, not the exotic one.
4. **The entitlement lives on the account** (and, for the couple half, on the
   relationship). Never in `SharedPreferences`, never keyed to a device ID or
   install ID. See §5 — this is the highest-value invariant in the document.
5. **A reconciliation job** that lists processor charges with no `paid`
   purchase locally. This is the only real defence against §4.3, and it is one
   query.
6. **An admin/manual path to grant an entitlement**, audit-logged. When
   reconciliation finds a stranded payment at 11pm, the fix must not be a
   `psql` session.

---

## 3. Happy paths

### 3.1 Single couple, Stripe

| # | Step | Assert |
|---|---|---|
| 1 | Buyer completes Stripe Checkout for $39 | `purchase` row `pending`, processor session ID stored |
| 2 | `checkout.session.completed` webhook arrives | Signature verified; `purchase` → `paid`; exactly one code issued |
| 3 | Code delivered | Present in the response *and* in an email — the buyer will lose one of them |
| 4 | Partner A redeems in app | Code `used`, `used_at` set, `used_by` = A's account |
| 5 | Entitlement granted | Both A and A's partner (if paired) hold it |
| 6 | Premium unlocked | Assessment, portrait, facilitator report, full app access |
| 7 | Partner B, separate account, separate device | Holds the entitlement without redeeming anything |

Step 7 is the one to actually run on two devices. "Covers both partners" is a
sentence in the pricing; it is a join across two tables in the code.

### 3.2 ~~Single couple, Paystack~~ — CUT 2026-08-03

**Not in scope.** Stripe only. Retained as the checklist for whichever processor
is added second, because these three traps are processor-independent and all
three are easy to write such that the test passes and the code is wrong:

- **Minor units differ.** Paystack quotes kobo, Stripe cents. Assert the stored
  amount *and currency*, not just that a payment succeeded. A 100× error here is
  invisible until someone reads a statement.
- **Signature schemes differ** (Paystack: HMAC SHA512 over the raw body).
  Assert an invalid signature is rejected using a *valid-looking but wrong*
  signature, not an empty one — an empty signature passes some naive checks.
- Assert the raw request body is used for verification, not a re-serialised
  parse. This is the single most common way signature verification is written
  such that it always passes.

### 3.3 Cohort batch

| # | Step | Assert |
|---|---|---|
| 1 | Facilitator buys 30 | One `purchase`, one `batch`, 30 codes |
| 2 | Codes issued | 30 distinct, single-use, **no expiry**, downloadable as a list |
| 3 | Facilitator distributes 30, 12 are redeemed | Batch shows 12 redeemed / 18 unredeemed |
| 4 | Facilitator opens their view | Sees the counts, and **not** which couples redeemed which code |
| 5 | Remaining 18 redeemed 10 weeks later | All succeed |

Step 4 is a privacy assertion, not a feature. A facilitator who can map a code
to a couple can map a couple to a report. `boundary.py` exists because that
kind of inference is the thing this product refuses to do; do not reintroduce
it through the billing schema.

Step 5 is why "no expiry" is in D2: premarital courses run eight weeks and
people are slow. Assert it with a code issued at least 90 days ago.

---

## 4. Failure modes that actually happen

### 4.1 Double redemption

The same code redeemed twice — by the same person double-tapping, or by two
people the facilitator gave the same code to.

- Second redemption fails cleanly; **exactly one** entitlement exists.
- Two concurrent requests with the same code: one wins, one loses. Assert under
  real concurrency (two threads, same code, no sleep), not sequentially. A
  check-then-write that is not atomic passes the sequential test every time.
- Same person redeeming their own already-used code gets "you already have
  this," not "invalid code." They are not doing anything wrong and should not
  be told they are.

### 4.2 Expired or invalid code

Codes do not expire (D2), so the cases are: never existed, revoked after a
refund, malformed.

- Each returns a distinct, non-leaky error. Do not reveal whether an unknown
  code *could* have existed.
- Rate-limit redemption attempts per account. A 6-character code space is
  guessable at a few hundred attempts.
- Assert the error copy names a way out — an email address — because the person
  hitting it has already paid.

### 4.3 Payment succeeded, webhook lost — the worst one

The money left their account and no entitlement exists. Worse under D2 than it
was under a subscription: there is no next billing cycle to make it right
through, and no recurring relationship. They paid $39 once, got nothing, and
have no reason to believe a second attempt will work.

- Simulate: charge succeeds, webhook endpoint returns 500 or is never called.
- **Reconciliation finds it.** A job comparing processor charges against local
  `paid` purchases lists this one. This is the actual test — everything else is
  a workaround.
- **Delayed webhook still works.** Both processors retry for hours; a webhook
  arriving late must grant the entitlement, not be rejected as stale.
- **Duplicate webhook is idempotent.** Retries plus reconciliation means the
  same purchase can be processed twice. One purchase, one code, one entitlement.
- **The buyer can self-serve.** Re-entering the email used at checkout should
  find the purchase and re-send the code. Assert this exists; without it, every
  instance of §4.3 is a support email to a solo founder.

### 4.4 Refund

- Refunding a **redeemed** code: decide the policy and then test the decision.
  Recommended — revoke the entitlement, and route the person to the same "how
  do I get this back" copy as §4.2. Assert whichever is chosen; the failure
  here is that nothing is decided and the code does whatever it does.
- Refunding an **unredeemed** code: revoke the code; redemption then fails as
  revoked.
- **Partial refund of a batch** (facilitator refunds 10 of 30): revoke 10
  *unredeemed* codes. Assert already-redeemed codes are untouched — a couple who
  did the assessment does not lose their report because their facilitator
  downsized.
- Revocation must never touch anything in §6.

---

## 5. Entitlement permanence — the highest-value test

With a subscription, a lost entitlement is a support ticket and next month's
charge proves the relationship. With a $39 one-off and perpetual access, a lost
entitlement is someone who paid and now has nothing, with nothing recurring to
make it right through. And the tail is unbounded: D2 grandfathers perpetual
access, with a review trigger at 500 sold.

The flag must be **tied to the account, not the install**.

| # | Scenario | Assert |
|---|---|---|
| 1 | Delete and reinstall the app, log in | Entitlement present, no re-redemption |
| 2 | Log out, log in on the same device | Present |
| 3 | Log in on a second, never-seen device | Present |
| 4 | Restore to a new phone from backup | Present |
| 5 | Clear app data / `SharedPreferences` | Present |
| 6 | Change email address (`EmailChangeScreen` exists) | Present, follows the account |
| 7 | Partner B joins **after** A redeemed | B holds it on first login |
| 8 | Couple dissolves the relationship (`DissolveRelationshipScreen`) | Both keep it — they each paid |
| 9 | Offline launch | Last-known-good entitlement honoured; never a paywall because the network is down |
| 10 | Entitlement service returns 500 | **Fails open.** Never a paywall on an unknown answer |

Scenarios 9 and 10 follow the fail-open rule `chat/assist.py` already sets for
the safety classifier: a broken check must not trap the user. A person on a
plane who paid $39 seeing a paywall is a refund request and a review.

**Test 5 is the one that catches the actual bug.** Caching the entitlement in
`SharedPreferences` for speed is the obvious optimisation, it works perfectly in
every manual test, and it fails the first time someone clears app data — by
which point the code is redeemed and cannot be redeemed again.

---

## 6. What the paywall must never touch (D7)

Non-negotiable, and covered by a separate always-on gate —
`docs/qa/crisis-gating.md`, `tests/safety/test_crisis_never_gated.py`. Restated
here because this is the document the engineer will have open while building
the paywall:

- The support icon, on all 12 screens that carry it.
- The `/safety` route and `SafetyResourcesScreen`.
- The safety classifier and every layer of it. In particular **nothing may be
  inserted ahead of `node_1_safety_prescreen`** in the counseling graph — a
  gate there means an unpaid user's message is never screened for crisis.
- `crisis_resources()` and the `safety_triggered` SSE frame.
- The crisis modal, and the snackbar route to support.

Add to the money-path suite: **an account whose entitlement was just revoked
by a refund still passes every D7 check.** Someone who just lost access is not
obviously having a good week.

---

## 7. What can be tested today

`tests/money_path/test_one_sku_only.py` — skips while there is no billing code,
and activates the moment there is. It then asserts:

1. **D2 is still one SKU.** No `subscription_status`, `trial_`, `tier`,
   `renewal`, `proration` or `dunning` in the billing surface. D2 is reversible
   by decision, not by drift.
2. **The entitlement call sites equal an allowlist** — see below.
3. **The E2E suite exists.** Once billing code lands, `test_checkout_e2e.py`
   must exist beside it. Same tripwire pattern as the D7 runtime test, for the
   same reason: coverage should arrive with the risk.

### 7.1 The entitlement allowlist

Implements product's `docs/specs/money-path-acceptance.md` §3.3.1. The set of
files containing an entitlement check must equal a named allowlist, failing in
**both** directions:

```python
ENTITLEMENT_CALL_SITES = {
    "<report generation module>",       # P0.3
    "<certificate generation module>",  # P0.11
    "<counsellor session gate>",        # D3.11 — gates the reply, not the door
}
```

A set rather than a count, because a count is wrong the moment a decision lands
and a test that is wrong gets disabled. Removals fail too: delete the counsellor
gate and revenue stops silently, which a count-based test would pass.

The entries are placeholders until the modules exist. `test_entitlement_call_
sites_match_the_allowlist` **fails loudly** rather than skipping once billing
code appears with placeholders still in place — the allowlist is worthless
until it names real paths.

**Predicted collision, flagged for the engineer.** The counsellor gate belongs
on the *reply* path (`counsellor-paywall-copy.md` §2 — a check on session entry
would pass §3.3 and violate the safety design). But the reply path runs through
`chat_router.py`, which is a **Tier 2 file in the D7 gate** and the same module
that emits `safety_triggered` with `crisis_resources()`. An entitlement check
placed within 25 lines of that emission will trip
`test_no_entitlement_check_sits_next_to_a_crisis_reference`.

That is the gate working, not a false positive: gating the counselling reply in
the same function that hands someone a crisis hotline is exactly where D7 risk
lives. The resolution is structural — put the gate in its own module that
`chat_router` calls, keeping it out of the crisis emission's neighbourhood —
not a `REVIEWED_EXCEPTIONS` entry. Worth knowing before it is written rather
than after.

There is also a pre-existing test worth knowing about:
`tests/security/test_vector_namespace_isolation.py` — see the CI defect noted
in `docs/qa/baseline.md`; the workflow that is supposed to run it points at a
path that does not exist.

---

## 8. Release gate

Do not take real money until:

- [ ] §3.1 passes end to end against **live Stripe test keys**, not mocks
- [ ] §3.3 passes with a 30-code batch, including partial redemption
- [ ] §4.1 passes under **concurrent** redemption
- [ ] §4.3 reconciliation demonstrably finds a stranded payment
- [ ] §5 scenarios 1, 3, 5, 9, 10 pass on a real device
- [ ] §6 passes for an account with no entitlement and for one just revoked
- [ ] Webhook signature verification rejects a wrong-but-well-formed signature, verified against the **raw request body**
- [ ] One end-to-end purchase with a **real card for $39**, refunded afterwards. Test keys do not exercise the same code paths at the processor, and this is the cheapest insurance in the plan.
