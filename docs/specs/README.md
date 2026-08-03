# Build order for the product specs

Owner: product/design (`local_81faf803`). Written 2026-08-03.

Thirteen specs, ~3,000 lines, written over several days as decisions landed.
Each states its own preconditions — but only inside itself, which means the
constraint that stops you building something in the wrong order is in a document
you may read *after* you start.

This page exists so that does not happen. **Read §1 before picking anything up.**

---

## 1. Do not build these in the wrong order

Seven hard dependencies. Each has a stated consequence, because "wait for X" gets
ignored and "this loses the user's work" does not.

| Don't build | Before | Or else |
|---|---|---|
| **Support icon into onboarding** (`support-icon-coverage.md` Group A, `onboarding_flow_screen.dart`) | **D3.1 answer persistence** | Answers live in memory only. Someone in distress taps for help, comes back, and forty answers are gone. **A safety feature that punishes the person who uses it.** Criterion 7.5. |
| **The AI session first-run** (`ai-session-surface.md` §3) | **Counsellor memory, both halves** | The blank screen is a *symptom* of statelessness. Decorate it and the screen looks better, the product is as broken, and the visible evidence that would lead someone to the cause is gone. §3.0, criterion S.8. |
| **Retention copy §3.2 / §3.3** (`session-retention-wording.md`) | **D-c: consent gate on extraction** | "Derived memories, with consent" is not true today — no retention path reads `session_transcript_retention`. Shipping the copy first makes it a false capability claim. |
| **The cohort view** | **`cohort-disclosure-rule.md`** | The allowlist and the no-rankings rule are cheap to build in and expensive to retrofit. A ranked list shipped once cannot be un-seen by the facilitator who saw it. |
| **The certificate** (`facilitator-report.md` App. A) | **Facilitator-marked completion in the cohort view** | Generates on purchase and certifies nothing. A.4. |
| **The counsellor paywall** (`counsellor-paywall-copy.md`) | **The safety pre-screen being on the reply path** | The gate is on the *reply*, not the door. A check on session entry passes the entitlement allowlist test and violates the safety design. `money-path-acceptance.md` §3.3.1. |
| **Any second entitlement check** | **Editing the allowlist** | The CI tripwire fails in both directions by design. If it fires, that is the feature working — do not raise the count, decide whether the gate should exist. |

---

## 2. Buildable now — nothing blocks these

- **`report-conversations.md`** — report page 5. Asserted independent of P0.1
  (criterion 7.2); categorical keys need no threshold.
- **`report-pairing-blocks.md`** — report page 4. P0.1 has shipped and the axis
  derivation is verified against the fixed scorer. **Ten blocks, not nine.**
- **`facilitator-session-guide.md`** — one page, no couple data, no dependencies.
- **`support-icon-coverage.md` Groups A and B *outside onboarding*** — ~24 files,
  one line each, independent of everything.
- **`facilitator-report.md`** structure, pages 0–3 and 6–8.
- **`ai-session-surface.md` §2** — the chrome collapse and the clipped
  `SafeArea` banner. Independent of the memory fix; only §3 waits.

---

## 3. The specs

| Spec | What it is | Status |
|---|---|---|
| `facilitator-report.md` | The $39 artefact. Nine pages + certificate appendix | Complete |
| `report-pairing-blocks.md` | Page 4 copy — ten blocks | Complete |
| `report-conversations.md` | Page 5 copy — four conversations, thirteen variants | Complete |
| `facilitator-session-guide.md` | How a facilitator teaches from it | Complete |
| `cohort-disclosure-rule.md` | What a facilitator may see about their cohort | Complete |
| `money-path-acceptance.md` | Checkout, entitlement, redemption, D7 criteria | Complete |
| `counsellor-paywall-copy.md` | The paywall, and where it must never appear | Complete |
| `session-retention-wording.md` | What we keep from a session, and the copy | Awaiting D-a/D-b/D-c in code |
| `support-icon-coverage.md` | Making a false claim true — 53 screens | Complete |
| `ai-session-surface.md` | Chrome collapse + first turn | §3 blocked on memory fix |
| `capability-claims-audit.md` | Claims checked against code | Live — §1.5 pending, §5 owed |
| `feature-kill-list.md` | The 21 areas ranked | Complete; re-do after real cohorts |
| `refusals-as-proof.md` | Copy pattern, and where it stops working | Complete |

---

## 4. Four rules that cut across all of them

**Enforce invariants statically, not by convention.** Four now work this way and
they all fail in both directions: the boundary import test, the entitlement
allowlist, the support-icon exemption list, the D7 assertion. A rule enforced by
the judgement of whoever writes the next endpoint is not a rule.

**A capability may be claimed only if someone has used it in the running app, or
a passing test exercises it end to end** (D3.16). A model, a migration, an
endpoint, or a design document is not evidence. Five claims failed this test in
one week.

**A refusal is a capability claim in the negative** and fails the same way
(`refusals-as-proof.md` §5). "We chose not to build X" needs a test as much as
"we built X" does. And only refuse things we *could* have shipped — a limitation
dressed as a principled choice is worse than a plainly stated limitation.

**When a document's subject changes, the documents that frame it are stale even
though nothing in them was edited** (D3.34). Whenever a spec ships: *what framed
this, and does it still describe it?* Six defects in `facilitator-report.md`
pages 1 and 8 came from exactly this.

---

## 5. Standing caveat on evidence

**1,301 of the 1,313 accounts in the database are synthetic.** `Relationship:
649` and `CoupleMessage: 6947` are scenario-harness output, not behaviour. There
is one real account.

Nothing in these specs is ranked, cut or prioritised on usage data, because
there is none. Where a document looks like it is reasoning from evidence, check
whether it says so — `feature-kill-list.md` §0 is explicit that it is not.

---

## 6. Keeping this page true

**D3.34 applies to this file too, and it is the one document that would not
notice.** A dependency in §1 that stops matching its spec is exactly the failure
the rule describes — text that framed something, gone stale because the thing it
framed moved, with nothing edited.

Enforcing it is the same shape as the other four invariants: mechanical, and
failing in both directions.

**The check** — run over `docs/` and `docs/specs/`:

1. Every `` `filename.md` `` referenced resolves to a file that exists.
2. Every `` `filename.md` §N `` resolves to a heading that exists in that file.
3. Every spec in `docs/specs/` appears in §3 of this README, and every spec named
   in §1 or §3 exists.

Historical citations are allowed — an audit entry recording a finding that a
later decision resolved should keep the reference — but must be in the past
tense and marked as such, so the reader can tell a stale pointer from a
deliberate one.

**It has already earned its keep.** The first run found four specs still
reasoning from `go-to-market.md` §5.6 — the tiered Cohort License, killed by the
one-SKU pricing decision. Not broken links: a session guide whose entire stated
justification was a dead SKU, two acceptance criteria written against a licence
term that no longer exists, and an audit finding that a decision elsewhere had
silently resolved.

Nobody edited those four documents. The document they pointed at changed, which
is the whole of D3.34.

**Owner:** QA, as a docs test. Until it exists, run it by hand whenever a spec
ships — and note that the same rot applies to `docs/*.md`, which this check
already covers.
