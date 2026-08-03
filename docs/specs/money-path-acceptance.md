# Acceptance criteria: the money path

Owner: product/design (`local_81faf803`). Tests implemented by QA.
Covers execution-plan **P0.2** (checkout, entitlement, redemption), **P0.8**
(money-path E2E + D7 crisis gating), and the journey criteria that P0.3 depends
on.

These are pass/fail statements, not guidance. Where one encodes a decision
already taken, the decision is cited rather than re-argued.

---

## 0. The shape of what we sell

Per the founder's pricing decision: **one SKU, $39, one payment, per couple.**
No subscription, no tiers, no trial.

Two consequences that determine everything below:

**Entitlement gates exactly two things: report generation and certificate
generation.** Nothing else in the app is gated, because nothing else has a paid
tier to be gated behind. This is genuinely simple — one entitlement, one check,
two call sites — and it cannot collide with D7, because nothing on the safety
path is anywhere near it.

**An entitlement belongs to a couple, not a person.** It is granted to the
`Relationship` and both partners inherit it. Per-person entitlement would tax the
pairing loop the whole product depends on (`go-to-market.md` §5.1), and would
create the absurdity of a paid partner and an unpaid one in the same couple with
one report between them.

---

## 1. Purchase — web checkout (D1)

| # | Criterion |
|---|---|
| 1.1 | Stripe Checkout completes a $39 purchase and returns a redemption code. |
| 1.2 | At least one **non-card rail** completes a purchase and returns a code, for markets where card penetration is low or international cards fail. Paystack is the first such rail; under D3.0 it is an instance, not the design. |
| 1.3 | Currency and rail are selected by the **buyer's** choice, never by IP geolocation alone. Someone who banks in one country and lives in another must be able to pick either. |
| 1.4 | A failed or abandoned payment issues **no** code and leaves no partial record that a later retry could double-redeem. |
| 1.5 | A duplicate webhook for the same payment intent grants the entitlement **once**. Idempotent on the provider's event id. |
| 1.6 | A successful payment whose webhook never arrives is recoverable — reconciliation by payment intent, and a manual grant path the founder can run. Solo operator: this will happen, and "the customer paid and got nothing" cannot require an engineer. |
| 1.7 | Purchase requires no app install and no account. A facilitator buys on a call, on a laptop. |
| 1.8 | Card data never touches our servers or our logs. Hosted checkout only. |

### Invoicing

*Originally justified by the Cohort License's "take invoices and bank
transfers" rule. That SKU is dead, but the constraint survives it: a facilitator
buying for a cohort still frequently cannot pay by card, whether they are buying
one licence or thirty codes.*

| # | Criterion |
|---|---|
| 1.9 | Codes can be issued against an invoice or bank transfer, before payment clears, and marked provisional. Churches and NGOs frequently cannot pay by card, and a Stripe-link-only checkout loses sales that had already said yes. |
| 1.10 | A provisional batch that is never paid can be revoked, and revocation withdraws unredeemed codes without touching already-generated reports. |

---

## 2. Redemption and pairing (D3.3)

| # | Criterion |
|---|---|
| 2.1 | **One code redeems for a couple.** First partner redeems and is paired to the code; second partner redeems the *same* code and joins the *same* relationship. |
| 2.2 | A third redemption of the same code is refused, with a message that names the two accounts already on it. |
| 2.3 | The second redeemer never needs the email-invite flow. This is the point of D3.3 — the artefact requires both partners, so pairing must not depend on the weakest funnel in the product (`product-assessment.md` §2.6). |
| 2.4 | A code redeemed by someone already in a *different* active relationship is refused with an explanation, not a silent failure and not a re-pairing. |
| 2.5 | Codes are unguessable (≥128 bits of entropy, not sequential) and case-insensitive on entry, because they will be read aloud on a phone call and written on a whiteboard. |
| 2.6 | Codes do not expire. There is no licence term to expire against, and expiry pressure on a facilitator's cohort buys nothing. |
| 2.7 | Redeeming grants the entitlement to the relationship, and both partners see it immediately without re-login. |

---

## 3. Entitlement

| # | Criterion |
|---|---|
| 3.1 | `generate_report(relationship)` refuses without an active entitlement. |
| 3.2 | `generate_certificate(relationship)` refuses without an active entitlement. |
| 3.3 | **The set of files containing an entitlement check equals an explicit allowlist.** Asserted in CI. See §3.3.1. |
| 3.4 | Entitlement survives one partner deleting their account; the surviving partner keeps access to an already-generated report. |
| 3.5 | Entitlement is revoked on refund, and revocation does **not** delete an already-delivered PDF. We do not reach into someone's downloads. |

### 3.3.1 The tripwire — an allowlist, not a count

**Re-baselined for D3.11.** The original criterion asserted "exactly two entitlement
checks." D3.11 added the counsellor gate, making the expected count three — and a
count that is wrong the moment a decision lands is a test that gets disabled,
which is worse than no test.

Assert the **set of files**, not the number:

```
ENTITLEMENT_CALL_SITES = {
    "<report generation module>",       # P0.3
    "<certificate generation module>",  # P0.11
    "<counsellor session gate>",        # D3.11 — gates the reply, not the door
}
```

CI fails if the set of files referencing the entitlement check differs from this
allowlist in **either** direction — an unexpected addition, or a removal.

Why this shape:

- **Adding a gate becomes a visible line in a diff**, in a file named
  `money-path-acceptance.md`, rather than a number someone bumps. That is the
  actual goal: no new paid tier appears without a decision.
- **Removals fail too.** If someone deletes the counsellor gate, revenue silently
  stops. A count-based test would pass a swap.
- **It never needs re-baselining for the wrong reason.** A refactor that splits a
  module updates a named entry; a new tier does not.

The counsellor entry must point at the gate on the **reply path**, not on session
entry — see `counsellor-paywall-copy.md` §2. A check on session open would pass
this test and violate the safety design.

---

## 4. D7 — nothing downstream of crisis resources is ever gated

The decision is closed. These criteria exist because we are adding the paywall
that could violate it, and because a convention is not a test.

| # | Criterion |
|---|---|
| 4.1 | The support icon is present and functional on every screen that has an app bar, for an account with **no** entitlement. |
| 4.2 | `/safety` renders in full, with every hotline, for an unentitled account. |
| 4.3 | Every `tel:`, `sms:` and chat URL on the safety screen launches for an unentitled account. |
| 4.4 | The safety protocol modal triggers and displays for an unentitled account. |
| 4.5 | **Static assertion:** no module reachable from the safety path imports the entitlement check. Same construction as the boundary import test — a convention someone can edit is not a guarantee. |
| 4.6 | No paywall, upsell, "upgrade" prompt or price appears on any safety surface, in any state, including after a refund or a revoked entitlement. |
| 4.7 | Regression: 4.1–4.6 re-run whenever the entitlement module changes. |

**Failure of any 4.x is a release blocker, not a bug.** It is the one failure in
this product that is a news story.

---

## 5. Journey — what the artefact actually depends on

The report cannot generate unless both partners finish onboarding, so completion
is on the money path (D3.1).

| # | Criterion |
|---|---|
| 5.1 | A partner who force-quits mid-questionnaire and reopens the app resumes with every prior answer intact. |
| 5.2 | The same holds across a device restart and an app update. |
| 5.3 | Progress is visible — the user can see they are at item 18 of 22 and that their answers are held. |
| 5.4 | A partner who has finished can see whether their partner has, without seeing any of their answers. |
| 5.5 | The cohort view shows per-couple status — `not started` / `one partner done` / `ready` / `report generated` — and **no** scores, styles, labels or answers. |
| 5.6 | A couple stuck at `one partner done` for 7 days triggers a nudge to the unfinished partner, and nothing to the facilitator beyond the status already shown. |

5.1 is the one to build first. `OnboardingViewModel` currently holds all answers
in memory and POSTs once at the end; an interrupted partner loses everything and
restarts. It is the most likely way a paid cohort produces no deliverable.

---

## 6. Refunds and the things that go wrong

A solo operator needs these to be self-service or they become support load that
does not scale.

| # | Criterion |
|---|---|
| 6.1 | A refund is processable from the provider dashboard alone, with the entitlement revoked by webhook. No engineer, no shell. |
| 6.2 | A couple who never paired within 30 days can be refunded without an argument. This will be the most common refund and it is our fault, not theirs. |
| 6.3 | A facilitator can reassign an unredeemed code from one couple to another. Cohorts change; people drop out the week before. |
| 6.4 | Every entitlement grant, revoke and reassign writes an `AuditEvent`. |

---

## 7. Analytics on this path (P0.4, two days, hard stop)

Funnel events only. Names and timestamps, no content, consent-aware.

| # | Criterion |
|---|---|
| 7.1 | `setConsent()` is called from the consent flow. Until it is, `_consented` stays null and nothing records — the taxonomy has emitted zero events since it shipped. |
| 7.2 | Events fire for: checkout started, purchase completed, code redeemed, first partner paired, second partner paired, onboarding started, onboarding completed (per partner), report generated, certificate generated. |
| 7.3 | No event carries an answer, a score, an attachment style, or message content. |
| 7.4 | With consent withheld, zero network calls to either sink. Asserted, not assumed. |

**Stated limit, so nobody over-reads the output:** at cohort scale these counts
are operational instrumentation — *did this couple get stuck* — not statistical
evidence. Per the engineer's point, at n=20 the database answers funnel questions
faster than events do, and interviews answer *why*, which no event schema will.

---

## 8. What "done" means for P0.2 + P0.8

All of §1–§6 pass, plus one end-to-end run against **real provider test keys**,
performed manually before the first facilitator call:

> Buy on the web → receive a code → redeem as partner A on a clean install →
> complete onboarding → redeem the same code as partner B on a second device →
> complete onboarding → report generates → both partners and the facilitator can
> download it → facilitator marks the couple complete → certificate generates →
> refund → entitlement revoked → **safety path still fully functional throughout,
> at every step above.**

If that run has not been done end to end by one person on two real devices, the
money path is not finished, regardless of what the test suite says.
