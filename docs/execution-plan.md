# Bliss — the execution plan to first revenue

Owner: project management. Written 2026-08-03. **This document outranks the
sequencing in `docs/product-assessment.md` §3 and `docs/go-to-market.md` §6.1.**
Those two documents remain correct about *what* is wrong and *why*; this one
decides *what order we do it in, who does it, and what we sell.*

If you are one of the four working sessions, read §1, §2, your own row in §4,
and §6. Do not re-open a decision in §3 without bringing new evidence.

---

## 0. Production readiness: still NO-GO — **two of four cleared**

*Status as of handoff, 2026-08-03. Verified in code, not from reports.*

| | State |
|---|---|
| **P0-1** connection leak | **FIXED** — `close_pools()` with teardown (`575588e`) |
| **P0-2** SMTP block | **FIXED** — same commit |
| **P0-3** Sentry PII | **OPEN** — `settings.py:45` still `send_default_pii=True` |
| **P0-4** public signing key | **OPEN** — default still present; **rotation is the founder's, not the engineer's** |
| S2 / S3 fail-open | **FIXED** (`3b2b796`) |
| P0.1 RSQ scorer | **FIXED** (`09f8feb`) |
| D3.39 therapist controls | **FIXED** (`745365a`) |

**Also open, and larger than any of the above: the counsellor has no memory**
(D0.2), and `make safety-eval` still cannot report which classifier layers ran —
the largest invisible failure in the product.

**No live cohort runs until P0-3 and P0-4 are closed and the load phases re-run
clean.** Sales activity — calls, bookings, authorisations — is unaffected.
Detail in `docs/qa/production-readiness.md`, measurements in `docs/qa/load.md`.

### The queue, in order, for whoever picks this up

1. `make safety-eval` reports which layers actually ran *(safety; small)*
2. **P0-3** — delete `send_default_pii`, add `max_request_body_size="never"`,
   `include_local_variables=False`; strip mobile request/response body logging
   from release builds
3. **P0-4** — remove the `SECRET_KEY` default so it fails closed *(the key
   itself must be rotated by the founder; it is public in git history)*
4. Deploy config — `release:` migrations, the literal `\$PORT` backslash in
   `backend-django/Procfile:1`, real health endpoints, `CRISIS_RESOURCES` set
   and asserted at startup (D3.19)
5. **Counsellor memory, both halves** — thread session history *with a
   context-window cap*, and fix the `endSession` contract + missing call site
   (D0.2). Implement D-c's consent gate **before** wiring the pipeline
6. The `degraded()` helper — **before** P0.2's webhooks are written
7. **P0.2 checkout** — blocked on the founder's Stripe account
8. P0.3 facilitator report · P0.9 draft-save · P0.10 remainder · P0.11
   certificate

**Everything buildable today with nothing blocking it is listed in
`docs/specs/README.md` §2.** Read §1 — the seven hard dependencies — before
starting any of it.

| # | Defect | Measured consequence |
|---|---|---|
| **P0-1** | Every counselling turn permanently leaks 10 Postgres connections (`vector_store.py:35-38` caches a pool and never closes it; `chat_router.py:243` builds a fresh retriever each turn so the cache never hits) | **Nine counselling turns per FastAPI process — ever, not concurrent.** Then Postgres refuses everyone including Django and Celery, while `/health` still reports healthy |
| **P0-2** | Partner invites send mail inline with no `EMAIL_TIMEOUT` (`relationships/views.py:66`), on 2 sync gunicorn workers | 40 invites at concurrency 20 → **40 failed, 0 succeeded.** Two invites is the entire Django API. A cohort sends forty |
| **P0-3** | Sentry receives counselling message text, user email and IP — `send_default_pii=True`, and `max_request_body_size` defaults to `"medium"` which attaches bodies regardless of that flag. Mobile logs request *and* response bodies in **release** builds | **Therapy conversations exposed to a third party.** For this product, the worst defect on the list |
| **P0-4** | `SECRET_KEY` is the public `django-insecure-…` default, byte-for-byte in `.env.local` **and in git history**, shared by both services | It is the JWT signing key. Anyone with the repo forges a token for any user. **The key must be rotated, not just moved** |

**P1 that P0-1 promotes to critical:** the WebSocket participant check fails
*open* (`websockets.py:69-71`), and its trigger is `TooManyConnectionsError` —
which P0-1 guarantees. Under load, **any token holder can join any couple's
joint session.** CI cannot catch it: `fastapi-ci.yml:66` sets
`WS_SKIP_PARTICIPANT_CHECK=1`.

**D0.1 — The counsellor is stateless within a session, and that is a product
defect, not a cost saving.** Measured cost is $0.001349/turn (317 in / 56 out)
against `go-to-market.md` §3.1's $0.012 estimate — but only because
`chat_router._initial_state` puts a single message in the buffer. **The AI
counsellor does not remember what was said two turns ago.** Nobody caught it
because there is one real user.

Fixing it changes the economics D2.3 and D3.11a rest on: 100 turns → $1.32 per
couple (96.6% margin); **500 turns → $30.51 (21.8% margin on $39).** The
12-month bound caps duration, not intensity.

**The missing control is a context-window cap** — last N turns plus a rolling
summary — not a turn budget. That bounds per-turn cost without rationing what
anyone is allowed to say, so it does not touch `go-to-market.md` §5.5 or D7's
spirit. Cheap now, awkward after someone has paid.

**D0.2 — The AI counsellor has no memory at all. Two findings, one product.**
- *Within a session:* `chat_router._initial_state` puts one message in the
  buffer. It does not remember two turns ago.
- *Across sessions:* `memory_vectors` holds **0 rows because the writer is a
  stub** — `sessions/tasks.py:memory_update_job` logs, returns `True`, and
  carries the comment *"Vector DB upserts would happen here."* Not a swallowed
  exception; unwired.

So the personalised, memory-backed counsellor described in `README`,
`VALIDATION.md` and the product assessment does not exist in either direction.
This is the product, and it is the thing $39 buys. **P0, above the report.**

**Traced end to end, and it is worse than "the writer is a stub."** The chain
breaks twice:

```
AI session → FastAPI streams reply, writes langgraph_sessions (failing silently)
POST /api/counseling/sessions/end/   ← NEVER CALLED
   └─ CounselingApiService.endSession() has ZERO callers in mobile/lib
counseling.Session never created  (0 rows, confirmed)
   └─ process_post_session_async never fires
      └─ extract_memories_task never runs
         └─ Memory = 0, MemoryVector = 0 — structurally, not "not yet"
```

**And the missing call site would not work if it existed.**
`endSession(String sessionId)` takes a session id; the endpoint requires
`relationship_id` **and** `transcript`. A solo user has no `relationship_id` at
all, so private-session memory could never work for them even once someone wires
the call.

This is not "no real users yet." **Every real user in the world would produce
zero memories.** Scope the fix accordingly: it is a contract change plus a call
site plus the job, not a one-line wire.

**D0.5 — The further a surface is from the code that would make it true, the
longer it survives being false.** Three instances now: the consent control that
reads nothing (D3.20), the therapist-access row (D3.39), and the memory
transparency panel. Each is a well-built UI over a capability that does not run.

**The memory panel is hidden, not improved.** Same conditional render as the
therapist row. Its current empty state — *"No memories found in this zone"* — is
literally true and not honest: it reads as *nothing yet* when the truth is
*nothing ever*, and it offers Edit and Delete controls for records that cannot
exist, behind a zone filter partitioning nothing. **Do not improve that empty
state** — per D3.46 a better one makes the breakage more invisible. If it must
stay visible, `session-retention-wording.md` §3.1 already has the honest version,
which is a *stronger* privacy position than the panel implies.

**Two consequences for D-c:** the panel is **not** evidence the consent gate
works — an empty panel under a working gate and an empty panel under an unwired
pipeline are indistinguishable, so any test must assert on the extraction path
directly. And the gate must be implemented **before** the pipeline is wired, not
after.

**D0.3 — The whole counselling stack degrades silently on one root cause, and
nothing anywhere can tell.** `screen_layer2` and `screen_layer3` both fall back
to `_keyword_screen`; `llm_provider.generate_reply` returns `FALLBACK_REPLY`. All
three catch `Exception`; all three are reached by a wrong `OPENAI_API_KEY`, a
renamed model, or a rate limit.

The combined state is a product that looks fully operational and substantially
is not: the three-layer safety classifier becomes one layer of keyword matching,
and every reply becomes *"I'm here with you. I'm having trouble putting a full
response together right now — can you tell me a little more?"* — which is
conversationally coherent, so a user answers it and gets it again.

**`make safety-eval` produces byte-identical output whether Layers 2/3 work or
are dead**, because CI runs it keyless and it reports "keyword/regex floor"
either way. **Nothing anywhere distinguishes healthy from degraded.** This is a
safety finding, not an observability one. The fix — make `safety-eval` assert and
print which layers actually ran — is the highest-value single change available.

**D0.4 — Fail-safe direction is a decision, and it is not the same decision as
logging.** Standing rule:

> **Authorization and identity resolution fail closed. Convenience and
> enrichment fail open.**

Currently violated in both directions. `verify_session_and_user` — the check
gating `/ws/joint/{session_id}` — returns `True` on any exception, while
`couple_membership` 400 lines below returns `False` for the same class of
concern. `get_partner_id` returns the string `"mock-partner-id"` on failure, a
test double in a production error path, feeding `activate_window()` and
`send_to_user()`.

**D3.25 is consistent with this rule and stays.** The counsellor entitlement is a
commercial gate, not authorization or identity — and the asymmetry there runs the
other way, because wrongly denying puts a card form in front of someone in
distress. Do not "fix" it to fail closed.

## 1. Where we actually are

Verified against the code on 2026-08-03, not against the docs:

| Thing | State | Evidence |
|---|---|---|
| **Billing** | **Does not exist.** No RevenueCat, no Stripe, no Paystack, no entitlement check anywhere. | `grep -ril "revenuecat\|paystack\|stripe\|entitlement"` → two false positives |
| **Analytics** | **Shipped but dark.** 231-line taxonomy, two sinks, one call site (`SurfaceOpened`). `setConsent()` is never called from anywhere, so `_consented` stays `null` and `isRecording` is false. | `analytics.dart:42–57`, one grep hit outside `core/analytics` |
| **Store presence** | None. `store_metadata/` holds one `Info.plist`. `pubspec.yaml` still says "A new Flutter project." | `mobile/store_metadata/ios/` |
| **RSQ scoring** | Broken. The model-of-other dimension is collected and never scored — 6 of the 30 items feed nothing. | engineer's analysis, `personalization/` |
| **Daily questions** | Fixed (121 questions, per-couple ordering, category filtering). No beat job delivers them. | migration `0019_more_daily_questions` |
| **Downloads** | 0 | — |
| **Revenue** | $0, and structurally capped at $0 until something above changes | — |

Founder constraints, as stated: **solo, ~$50 budget, no therapist relationships
yet, no launch.**

## 2. The target, honestly

The ask is $100,000 in revenue in a short period. Stated plainly, once:

**$100k ARR is a 9–15 month goal at this budget, not a one-quarter goal.**
`go-to-market.md` §6.0 already models this and lands on ~1,000 paying couples at
month 12. Nothing in the last two weeks of work changes that arithmetic. Anyone
promising $100k in 90 days is promising paid installs at a $5.84 iOS CPI that
cannot be afforded and would not convert through a funnel that currently has no
paywall to convert into.

So we run two clocks:

- **90-day goal — prove the machine.** First dollar collected. **$3k–8k**
  banked. A repeatable sale we have made more than once. Real funnel numbers
  replacing the estimates in `go-to-market.md` §3.3.

  *Restated 2026-08-03 from $5–15k.* Marketing ran the §6 gate forward and the
  original number did not survive it: >3 cohorts per 10 calls, ~25 couples a
  cohort, and 20–40% couples-pay redemption leakage yields roughly $4k from 20
  calls, not $15k. **Outreach is raised to 60 contacted / 20 calls** and the
  banked target is lowered to $3–8k. Both, not either — the volume was too low
  *and* the number was too high. $15k would need ~50 calls, i.e. four founder
  calls a week sustained for a quarter while also being the entire engineering
  and product team, which is not a plan.

  Raising the price to close the gap would be the wrong answer. At zero
  downloads, price is not what stops a facilitator from saying yes.
- **12–18 month goal — $100k.** **~21 active facilitator relationships.**

  *Corrected 2026-08-03.* I originally sized this as ~2,564 couples ≈ 85 cohorts
  and marketing corrected the unit, rightly. A one-off does not compound per
  couple, but it compounds per *facilitator*, because facilitators do not run one
  cohort — a parish programme or certified counsellor runs 3–4 a year,
  indefinitely:

  ```
  1 facilitator × 4 cohorts/yr × 30 couples × $39 = $4,680/yr
  $100,000 ÷ $4,680 ≈ 21 active facilitators
  ```

  At a ~30% call-to-active rate that is ~70 calls and ~210 contacts over a year —
  four contacts a week, a solo-founder workload. Eighty-five cold cohort sales is
  not. **The unit of sale is a facilitator relationship, not a cohort.**

  Ramp, accounting for facilitators landed late in the year running one cohort
  rather than four: **~$50–60k banked in year one, exiting month 12 at a ~$98k
  run rate, $100k banked around month 15–18.**

The one-off price changes the shape of the 12-month goal and it is worth being
exact about how. Recurring revenue compounds — last month's customers still pay
this month. A one-off does not: every dollar of the $100k must be sold once.
That makes the institutional channel not merely the best option but the only
one, because 2,564 couples cannot be recruited one couple at a time by one
person. It also means the honest 12-month number is closer to $60–80k, with
$100k landing in month 15–18 — unless a subscription is added on top once we
know what couples do in month three, which D2 deliberately leaves open.

The 90-day number is not a lowered ambition. It is the only path where the
12-month number is real, because a funnel we have not measured cannot be scaled.

## 3. Decisions — closed, do not re-litigate

**Index.** Eighty-three decisions accumulated in the order they were taken, which
is not an order anyone can use. Grouped here by what they govern. The log below
stays chronological — this is the way in.

Two of this project's worst defects were only visible when separate decisions
were read *side by side* (D3.41: three decisions combined to leave the
facilitator's referral network as the entire safety net; D3.58: two sections of
one document contradicting each other for days). **Read the group, not the
entry.**

| Governs | Decisions | The load-bearing ones |
|---|---|---|
| **What we sell, and for how much** | D2, D2.1, D2.2, D2.3, D3.11, D3.11a, D3.11b, D3.54 | **D2** one SKU, $39 once · **D3.11a** counsellor bounded at 12 months |
| **Taking money** | D1, D3.3, D3.7, D3.9, D3.25 | **D1** web-first, Stripe only · **D3.25** entitlement fails *open* |
| **Safety and crisis** | D7, D3.15, D3.19, D3.28, D3.41, D0.3, D0.4 | **D7** nothing on the crisis path is ever gated · **D3.15** the paywall gates the reply, not the door · **D0.4** authorization fails closed, enrichment fails open |
| **Privacy and consent** | D3.4, D3.10, D3.13, D3.20 (D-a/b/c), D3.27, D3.57 | **D3.20** a consent control that reads nothing · **D3.4** no risk flags, no compatibility score |
| **Intimacy content** | D3.51, D3.52, D3.53 | **D3.52** opting out must be unilateral, silent, immediate |
| **Channel and distribution** | D3.0, D3.5, D3.6, D3.6a, D3.6b, D3.21, D3.22, D3.29, D3.35, D3.48, D3.49, D3.50, D3.55 | **D3.0** global SaaS · **D3.49** therapists first, cohorts for scale · **D3.55** referral is worth ~2× |
| **Product scope** | D8, D3.1, D3.2, D3.17, D3.36, D3.39, D3.42, D3.43, D3.44, D3.45 | **D8** feature freeze · **D3.1** onboarding must survive interruption |
| **Broken, being fixed** | §0 (P0-1…P0-4), D0.1, D0.2, D0.5, D3.14, D3.18, D3.23, D3.24 | **§0** four production blockers · **D0.2** the counsellor has no memory |
| **How we work** | D3.12, D3.16, D3.16a, D3.16b, D3.30, D3.31, D3.32, D3.33, D3.34, D3.37, D3.38, D3.40, D3.46, D3.47, D3.56, D3.58 | **D3.16** a capability may only be claimed if someone ran it · **D3.34** framing documents go stale unedited · **D3.56** not every recurrence needs machinery |

**The working rules, in one place**, because they are the part that outlives this
plan:

- A capability may be claimed only if someone has used it in the running app or a
  passing test exercises it end to end (**D3.16**) — and any claim about what we
  will *never* do is re-checked whenever the SKU changes (**D3.16a**).
- When a document's subject changes, the documents that frame it go stale even
  though nothing in them was edited (**D3.34**).
- A refusal is a capability claim in the negative and fails the same way, so every
  refusal written as proof needs a test behind it (**D3.31**).
- The further a surface is from the code that would make it true, the longer it
  survives being false (**D0.5**) — and polish extends the lifetime of a lie
  (**D3.46**).
- Agreeing detail is where errors hide; nobody re-checks an argument that reached
  the right answer (**D3.38**).
- Before mechanising a rule, ask whether the next instance arrives from how the
  system is shaped or because someone made a call. Only the first needs a machine
  (**D3.56**).
- Retention needs an expiring justification: "removal is riskier than retention,
  here is the coupling" is checkable and expires; "might be useful later" keeps
  everything forever (**D3.40**).
- Unrecoverable outranks slow (**D3.32**).

**D1 — We take money on the web first, not through the App Store.**
Stripe Checkout (US/UK/diaspora) and Paystack (Nigeria). Reasons: no Apple review
dependency, no 30% cut, no app-store launch on the critical path, and a
facilitator can buy on a call today. IAP comes later, for the consumer
subscription, once the app is listed.

**D2 — One SKU. One price. $39, one payment, per couple.** *(Founder decision,
2026-08-03. This supersedes the entire tier structure in `go-to-market.md` §5.)*

```
Bliss — $39, one payment, covers both partners.
Includes: assessment, portrait, facilitator report, full app access.
```

Dead, as of this decision: the $14.99/mo and $89.99/yr Premium tiers, Bliss
Together at $49/mo, the $9.99 therapist-referred rate, the separate Cohort
License SKU, the ₦ price list, and the 30-day trial mechanic in §5.2. Do not
build any of them. Do not reference them in copy.

Rationale: assessments are what institutions buy, the artefact already exists in
the codebase, a one-off has no churn problem, the buyer assembles the couples for
us, and $39 sits inside Prepare/Enrich's established $35–65 band so the budget
line already exists at the buyer. Build cost is the real argument — no renewal,
no dunning, no cancellation, no refund-on-subscription, no trial gate, no tier
checks. One payment, one permanent entitlement flag.

**Consequence, stated plainly: $100k now needs ~2,564 sales, not ~1,000.**
`go-to-market.md` §6.0 sized $100k at 1,000 paying couples on recurring revenue;
at $39 one-off, 1,000 couples is $39k. See §2.

**This decision is reversible and that is the point.** A one-off today does not
preclude adding a subscription later, once we know what couples do in month
three. Going the other way — launching tiers and retreating to a one-off — is
much more expensive.

**Selling to a cohort still works.** A 30-couple cohort is 30 × $39 = $1,170.
We removed the SKU, not the channel.

**D2.1 — the cohort licence ladder is a sales instrument, not a product
feature.** *Original finding, for the record:* marketing priced a four-step
licence ladder (Cohort 10/25/50/Annual) in what was then `go-to-market.md` §5.6 —
**a section that no longer exists; §5 now runs 5.0–5.5** — on the correct
observation that facilitator-pays achieves ~100% redemption where couples-pays
leaks 20–40%. The ladder is good
commercial thinking and it does not go into the product. **The checkout knows
exactly one price: $39.** A facilitator who negotiates a discount is invoiced
manually by the founder — which we need anyway, because churches frequently
cannot pay by card and a card-only checkout loses sales that already said yes.

This keeps the build at one price while letting sales do what sales does. The
ladder stays in the GTM doc as the founder's negotiating reference, and is not
published as a price list until a facilitator has asked for one.

**D2.2 — the 90-day revenue path is couples-pay, not facilitator-pays.** On call
one the facilitator refers and each couple buys at $39; the licence is the
cohort-two conversation, per marketing's own "never quote a licence on call one"
rule. This matters for sequencing: a parish runs ~4 cohorts a year, so cohort two
falls outside the 90-day window. If the first cohort is free, there is no 90-day
revenue. Couples-pay closes on call one with no budget approval and no invoice
cycle, and it is exactly the single $39 price we already build.

Consequence for engineering: **batch redemption codes are not needed for first
revenue.** Couples-pay needs a payment link and an entitlement, nothing more.
Batch codes serve facilitator-pays and drop to P1.

**D2.3 — perpetual access ships as written; the COGS tail is instrumented, not
capped.** A one-off creates an exposure the subscription did not: ~$0.60–1.20 per
couple per month to serve against $39 collected once. A heavy user (~100 turns/mo,
~$3) is underwater inside 13 months.

We ship perpetual anyway. Introducing "24 months" into a pitch whose entire
strength is *one payment, no subscription* costs conversion immediately, while
the COGS cost is deferred, probabilistic, and blunted by the high attrition this
category has. But the exposure is real and grandfathering is what makes it
permanent, so it gets a bound rather than a shrug:

- **Instrument cost-per-couple** as part of the analytics work (engineer, P0.4).
- **Hard review trigger at 500 sold.** Before crossing it, we decide whether
  access on *new* purchases is defined as 24 months at the point of sale. Terms
  are never changed retroactively; the trigger exists so the grandfathered tail
  is ~500 couples rather than ~2,500.
- **Never a fair-use cap on counselling turns.** Marketing raised this and is
  right: rationing the thing people need most contradicts D7's spirit. If the
  numbers ever force a change it is the time bound, not the turn count.

**D3 — Therefore the broken RSQ scorer is a P0 revenue blocker.**
We are about to sell a report generated from that instrument to professionals who
know what an attachment measure is. Shipping a scorer that silently discards the
entire model-of-other dimension is not survivable in that channel. This is
promoted above every activation fix.

**D4 — RSQ item cut: the eight safe items only** (4, 11, 13, 18, 20, 21, 23, 29).
Keep 7, 14, 17, 26, 27, 30 — they are the raw material for D3. **Never renumber
surviving items**; the IDs are the join key to stored responses.

**D5 — Positioning splits by audience. The debate is closed.**
- *Consumer surfaces* (store listing, landing page, in-app): lead with the
  **mechanic** — both partners answer privately, both unlock together, nothing
  you say gets used against you. A negative claim about profiling can create the
  anxiety it answers.
- *Professional surfaces* (facilitator deck, therapist outreach, press, App
  Store review): lead with the **boundary** — `boundary.py`, the adversarial
  test, the score that can fall, the discarded call audio. Clinicians evaluate
  exactly this.

The boundary is the proof. The mechanic is the pitch.

**D6 — Analytics gets finished, timeboxed to two days, now.**
The engineer is right that at n=20 the database answers funnel questions faster
than events do. The reason to finish it anyway is that instrumentation must exist
*before* traffic arrives, and traffic is 4–6 weeks out. Two days, funnel events
only, then stop.

**D7 — Nothing that reaches crisis resources is ever gated.**
No paywall, no trial wall, no entitlement check on the support icon, the safety
path, or anything downstream of them. This is a hard test QA owns, not a
convention. `go-to-market.md` §5.2 states it; we are now adding the paywall that
could violate it.

**D3.1 — Onboarding must survive interruption, and it is P0.**
`OnboardingViewModel` holds all forty answers in memory and POSTs once at the end
via `submitOnboarding()`. No incremental save, no draft endpoint. A partner
interrupted at item 25 — a call, a dead battery — loses everything and restarts
from zero.

This was invisible while the product was free, and it is a revenue blocker now:
the report cannot generate unless **both** partners finish (report spec §3), so
questionnaire *completion* is what gates the artefact we sold — not
install→paired. The most likely way a paid cohort produces no deliverable is one
partner losing forty answers, and the person who hears about it is the
facilitator we need to sell three more cohorts to.

**D3.2 — A half-day credibility pass is in P0, and it is not activation work.**
Five things a facilitator evaluating us sees in the first ten minutes: the
disclosure banner clipped by the Dynamic Island on all four tabs (one line,
`SafeArea`); the purple "Validation" strategy chip on every AI reply; the joint
session titled "Private session"; the blank first-run chat screen; and the
privacy contradiction in assessment §2.11 — the consent sheet says sessions are
deleted, the You tab offers "everything you have talked through before."

That last one is a **sales objection, not a polish item.** A facilitator vetting
a tool for their couples reads the privacy copy, and we are asking them to stake
their professional credibility on us.

**D3.3 — The purchase issues one code per couple, and both partners redeem it.**
First partner redeems and is paired; the second redeems the same code into the
same relationship. This takes the email invite off the critical path, which is
why the P1 share-sheet does not block P0 revenue. Batch issuance — a facilitator
buying N codes at once — remains P1 per D2.2.

**D3.4 — Two things the report will never contain.** Both refused in the spec and
recorded here because both will be asked for again:
- **No risk flags to the facilitator.** A system quietly telling a third party
  that a couple looks high-risk, on 22 self-report items, without telling the
  couple. If the questionnaire surfaces a safety concern it goes to *the person*,
  through the existing safety path, which per D7 is never gated.
- **No compatibility score or percentage.** Prepare/Enrich prints them; we will
  not. One number from 22 self-report items, handed to a couple weeks before a
  wedding, either falsely reassures or hands them a reason to call it off — and
  it is the first thing a professional reader would distrust.

**D3.5 — The SKU sells two things that do not exist. Strike them from copy today.**
`go-to-market.md` §5.1 promises "an 8-session guided curriculum" and "a
completion certificate." Neither exists — `grep -rni "curriculum|8-session|
premarital"` returns zero hits across the repo, and there is no `Curriculum`,
`Programme` or `SessionPlan` model. What does exist: 121 daily questions across
6 categories, 9 game packs, 9 micro-action templates, 8 daily readings,
conversation decks — and no eight-session structure over any of it.

**Marketing strikes both from all copy before P0.7 outreach begins.** This is the
one unrecoverable failure in this channel: the facilitator's own reputation is
the collateral with their couples, and "the curriculum you told us about isn't in
here" ends cohort two and gets repeated to every facilitator they know.

The certificate is P0.11 and will exist. The curriculum is **P1** — see D3.6.

**D3.6 — Build the curriculum, but ask the buyer its shape first.**
It is a sequence over content that already exists — eight themed weeks, each
pulling a question set from the 121, one game, one commitment, one micro-action.
Arranging what is there, not adding a feature area, so D8 holds. It also closes
the arc: report → eight weeks → certificate is one programme rather than three
disconnected nouns, and report page 5's "Four conversations" should *be* sessions
1–4 rather than a parallel thing.

It is P1, not P0, for a reason we should be honest about: **we do not know
whether facilitators want our eight-week programme or materials that slot into
the one they already run.** They are running a course already. Speccing a
programme before asking is exactly the failure `product-assessment.md` §2.14
describes — a good decision made in isolation and never checked against a real
buyer. **The first ten facilitator calls answer this**, and then we build the
right one. First revenue does not need it; cohort two does.

**D3.0 — This is a global SaaS product. It is not a Nigeria or diaspora play.**
*(Founder decision, 2026-08-03. Overrides `go-to-market.md` §7's "diaspora-first"
recommendation and the ₦ pricing that D2 had already removed.)*

What this changes:
- **The target list is re-cut globally.** Not 12 RCCG parishes + 8 African-founded
  diaspora churches. English-speaking markets first: US Catholic marriage-prep
  offices (Pre-Cana is worldwide and already pays $35–65 a couple), US
  evangelical and non-denominational premarital programmes, UK/CA/AU church
  programmes, and couples therapists.
- **Paystack is cut from P0.** Stripe alone covers the markets we are selling
  into. Regional rails get added when a market demands them, not in advance.
  This is a real reduction in P0.2.
- **Nigeria-specific research is demoted, not deleted.** Lagos's premarital
  policy and the ₦ price anchors come out of the plan; the work is kept in
  `go-to-market.md` for whenever a regional entry is actually chosen.

What this does **not** change: the institutional channel itself. Premarital
programmes and couples therapists are a *global* channel — the beachhead
reasoning applied to a specific population, and the population was the part that
was wrong, not the motion. Nor does it change the product: the faith tab and
cultural framing stay, because they serve users of many backgrounds worldwide.
They are differentiators, not targeting hooks for one nationality.

**D3.6a — The curriculum question now has a prior: expect "materials, not a
programme."** RCCG — the largest Nigerian-founded denomination, with parishes
across the UK and US — requires intending couples to complete counselling before
the wedding, will not participate in the wedding of a couple who hasn't
*regardless of where it takes place*, and runs a published standard manual.
Catholic Pre-Cana is equivalent.

A facilitator inside a denomination with a **mandated curriculum** is unlikely to
want a competing eight-week programme and likely to want materials that slot into
the one they must use. So D3.6's discovery question is asked exactly as written —
a prior is a reason to listen carefully, not to skip — but three confirmations
are enough to stop the eight-week build before it starts. The inverse is a much
stronger signal: an RCCG facilitator saying "programme" would be saying it
*against* a mandate.

This also repairs the Nigeria/diaspora case on better evidence than it had.
Lagos's compulsory counselling was a government announcement with unverified
enforcement; **a church that refuses to conduct your wedding has enforced it
completely.** Caveat: denominational policy as published, not audited practice.

**D3.6b — The first ten calls are a deliberate mix, not the strongest tier
first.** Roughly six RCCG/African-founded diaspora parishes, **two Catholic
marriage-prep offices**, two others. The Catholic offices are the weakest
cultural fit and the **strongest commercial precedent — they already pay $35–65
per couple for Prepare/Enrich**, so a budget line exists and the price is
established. Six calls answer programme-vs-materials from the mandated-curriculum
population; two answer whether $39 clears a real budget. Working one tier to
exhaustion before touching another learns one thing slowly.

**D3.7 — Entitlement has exactly one job.** With no tiers and nothing else gated,
P0.2's entitlement check gates report generation and the certificate. Nothing
else. It cannot collide with D7 because nothing on the safety path is anywhere
near it. One gate, one test.

**D3.8 — The free-ride leak is real, and both payment paths get offered on call
one.** Nothing stops a cohort couple installing the free app and skipping the
$39, paying only if they want the report — which is the likely mechanism behind
the 60–80% couples-pay redemption estimate. Facilitator-pays does not have this
problem (~100% redemption). So on call one the founder offers **both**:
facilitator-pays by invoice where their budget allows it, couples-pay link where
it does not. No product change either way — the checkout still knows one price
and the invoice absorbs everything else.

**D3.9 — Refunds: 30 days, no questions, and one automatic case.**
A one-off makes a generous refund safe — there is no subscription for a refunded
buyer to keep using — and at zero downloads with no reviews it is the cheapest
objection-killer available.

The automatic case: two people in the same class may each buy $39 before pairing.
**Detect at pairing and refund one without being asked.** Making them notice and
request it is visible to the facilitator immediately, and "they double-charged my
couples" is the sort of thing that ends a channel. Cap and alert on the automatic
path so it cannot be driven in volume.

Corollary: **a couple who never pairs must still receive the assessment and
private sessions.** Otherwise the refund rate equals the pairing-failure rate and
we are refunding our own funnel defects.

**D3.10 — The post-cohort facilitator summary needs a floor, and product rules on
it.** Marketing proposes an anonymised post-cohort summary — completion rate, and
which items the class scored lowest on. It is genuinely good teaching material,
it proves the programme worked, and it arrives without asking the facilitator for
anything, which is why it may decide whether cohort two happens.

But it is a facilitator being shown data derived from couples, which is the
neighbourhood D3.4 refused risk flags in. Aggregate is a different thing from a
risk flag — and at small N it stops being aggregate. A ten-couple cohort where
one item scored lowest is not anonymous to a facilitator who knows the room.

**Requirement: a minimum-N floor below which no per-item breakdown is shown, and
completion rate only.** Product owns the number and the rule, not marketing and
not engineering. Nothing ships until they set it.

**D3.11 — What $39 buys, and what an unpaid install gets. This supersedes D3.7.**

| Free, always | Behind the $39 |
|---|---|
| Daily question and the two-sided reveal | The assessment and both portraits |
| Check-in, connection score, commitments | The facilitator report and certificate |
| Games, conversation decks | **The AI counsellor — private and joint sessions** |
| **Everything reachable from the support icon, for paid, unpaid and refunded alike** | |

Product's D3.7 said the entitlement gates the report and certificate only, and
that the app "cannot justify $39 today and shouldn't have to." That was sound
before the COGS analysis existed. It doesn't survive it, so I'm overruling it.

**The decisive argument is cost, not value.** The counsellor is the only
expensive surface in the product — ~$0.60–3.00 per couple per month against a
one-off $39. Leaving it open to unpaid installs is unbounded LLM spend against
zero revenue, and Loop 1 exists specifically to grow the number of unpaid
installs. That is not a leak, it is a hole in the hull.

**The second argument is that it makes the price obviously fair**, which is the
founder's stated criterion. "$39 once for unlimited AI counselling, an
assessment, and a report" is a materially better offer than "$39 for a PDF" — and
against Paired at $14.99/month it stops looking expensive and starts looking
like the aggressive option.

**The free tier is not charity and does not shrink.** The daily loop is Loop 1,
the only structurally free acquisition the product has, and partner B must
always enter without meeting a paywall. Walling it to protect a $39 sale would
kill the growth engine to defend the transaction.

**Two hard constraints on the counsellor paywall:**
1. **Nothing reachable from the support icon or the crisis path is ever gated**
   — D7, unchanged, and it now matters more because a paywall sits nearby.
2. **The paywall must surface crisis resources in its own copy.** A person
   opening a private session the night of a fight and meeting a card form is the
   precise scandal `go-to-market.md` §5.2 warns about. The gate is on the
   counsellor; the door to help is never closed, and the paywall itself has to
   say so. Product owns that copy and QA tests it.

No per-turn metering, no counselling credits — `go-to-market.md` §5.5, unchanged.

**D3.11a — Counsellor access is time-boxed to 12 months. Everything else the $39
buys is permanent.** *(Amended after product's pushback, which was correct.)*

D3.11 closed an unpaid hole and left a paid one open. A one-off price against a
recurring cost is structurally unstable for any metered feature, and the
counsellor is the only metered feature we have: at $0.60–3.00 per couple per
month, a *paying* couple crosses $39 of LLM cost between month 13 and month 65
and then keeps costing. "Unbounded against zero revenue" became "unbounded
against $39 once." Better, still unbounded.

```
$39, once.
  Permanent — assessment, both portraits, report, certificate,
              daily question and reveal, check-ins, games, commitments
  12 months — the AI counsellor, private and joint
```

**Twelve, not the six the old SKU implied.** Six months can expire before the
wedding of a couple who bought at the start of an eight-week course, and a
premarital product whose counsellor dies before the marriage starts is the wrong
artefact in this channel. Twelve covers the course, the wedding, and the first
year — which is the period this couple actually needs it. It bounds COGS to
~$7–36 against $39: thin at heavy usage, healthy at typical, and **bounded**,
which is the property that was missing.

This is not a second price and not a tier. It is the scope of the one price,
stated plainly at the point of sale. It also creates an honest moment to offer a
subscription in year two without breaking the one-SKU decision now.

D2.3's 500-sale review survives as the check on whether 12 months was right.

**D3.11b — The tone coach and "say it better" stay free.** Metered, so D3.11's
logic technically reaches them — but they run on a small model inside a 2.5s
budget, an order of magnitude cheaper than a counselling turn, and they live in
`couple_chat` where partner B must never meet a paywall. They are also the best
free-tier hook we have. If cost ever bites, cap by volume; do not gate by payment.

**D3.12 — Product audits every capability claim in `marketing-copy.md` against
the repo.** Two false capability claims have now been found in two days, both by
someone reading code rather than by the author. §§1, 7 and 8 — the App Store
description especially — assert six capabilities verified only as far as "the
models exist," which is not the same as shipped and reachable. This is a
prerequisite for P0.7 outreach, not a follow-up.

**D3.13 — Session history is silently broken. We fix the promise, not the
feature.** `sessions.Session` holds **0 rows**, including after a real AI session
run against the local stack. The writer, `persist_turn()` in `chat_router.py`,
swallows everything:

```python
except Exception:
    # History is a convenience; never let it interrupt counseling.
    return
```

Failing open on the send path is the right instinct and stays. The consequence is
that the feature can be wholly broken with nothing anywhere reporting it — which
is how it reached this point unnoticed.

This makes assessment §2.11 worse than a copy contradiction. The You tab offers
"everything you have talked through before"; the thing behind it stores nothing;
and a facilitator vetting us reads the privacy copy *and* taps what it
contradicts.

**Resolution: do not build session-transcript storage. Make the copy true.**
Three reasons — it is what the code does today, building persistence plus its
privacy review is not P0 work and would break D8, and **"we do not keep
transcripts of your sessions" is a materially stronger position for this product
than "we keep them forever."** For a product whose differentiator is
trustworthiness about data, the accident is better than the intention.

The honest statement has two halves and product owns the wording: raw session
transcripts are not retained, and derived counselling memories *are*, with
consent, which is a different thing and must not be blurred into the first.

**Also required: `persist_turn` gets a log line and a metric.** Fail open, never
fail silent. This is the general defect, not the specific one.

**D3.14 — The database is 1,301 synthetic accounts and one real one.** Of 1,313
users, 1,301 are `test.local` fixtures; `Relationship: 649` and
`CoupleMessage: 6,947` are simulation output. Anyone glancing at this database
will read traction that does not exist — it is §1's "downloads: 0" seen from the
other end.

Consequence: **nothing may be ranked, cut, or prioritised on usage data until
real cohorts exist.** The kill-list ranks on strategic dependency and says so.
No zero row count in that document means "users don't want this"; nobody has yet
had the chance to want anything.

**D3.15 — The paywall gates the reply, not the door.** A paywall on the private
session fires *before* the user has typed anything, so at the moment it appears
we cannot know whether someone opened the app to browse or because something
happened tonight. No wording survives a card form at 1am after a fight.

```
open session → no gate, no price
  → user writes and sends their first message
    → safety pre-screen runs (it already runs on every turn)
      ├─ crisis signal → safety path. NO paywall, and none for the
      │                  rest of that session. It continues, free.
      └─ no signal    → paywall, with the message preserved
                         └─ declines → draft KEPT
```

Better on every axis: nobody in distress meets a card form, because the
classifier reads the message before we ask for money; it costs nothing extra,
since the pre-screen already runs and the expensive counsellor call is still what
is gated; and it converts better, because someone who has typed out the thing
they are dreading is far closer to paying than someone facing an empty screen.
That is `go-to-market.md` §5.2's own moment-of-need argument applied one step
later.

Two details are load-bearing: the crisis exemption is **per session, not per
message** — nobody meets a gate on turn four because turn three read calmer — and
it **fails open** like `assist.py`, so a classifier error or timeout means no
paywall.

**D3.16 — A capability may be claimed only if someone has used it in the running
app, or a passing test exercises it end to end.** A model, a migration, an
endpoint, or a design document is not evidence.

Three false capability claims in three days, every one caught by reading code,
every one the same shape: *a model or a design doc exists and was read as
shipped.* In one case the document said "Status: proposed" in its own header.

**The five `docs/` specs marked "proposed" are a do-not-quote list.** Two have
since partly shipped and still say otherwise, so claims need checking in both
directions — the trap runs backwards as well as forwards.

**D3.16a — Any claim about what we will *never* do is re-checked whenever the SKU
changes.** D3.16 is keyed to "has someone run it," which catches capability
claims and misses a second class entirely. "No reports about your partner, to you
or to anyone else" was **true when written and became false the day we decided to
sell a facilitator report.** No code changed; the product's commitments did. A
rule about running code cannot catch a promise invalidated by a business
decision.

**D3.16b — When a claim is struck, grep the spoken scripts specifically.**
`marketing-copy.md` §§12 and 13.4 are the call script and the one-sheet the
founder holds *during* a call. Two claims have now propagated there — the
curriculum and the licence promise — and they are the last place anyone looks and
the only place that reaches a facilitator's ear rather than their inbox. A false
line in an email can be corrected by a later email. A false line said aloud
cannot.

**D3.17 — "Support resources are one tap from every screen" is false. Make it
true rather than softening it.** `SupportAction` appears on 11 screens plus
`HubScaffold`, out of **53**. It is missing from games, faith, focus,
commitments, two truths, daily ritual, relay, dissolve-relationship, joint video
— **and all six onboarding screens.**

The onboarding gap is the one that matters. That is 40+ taps answering items
about abandonment and rejection, with no visible route to help on the screen.

One line per app bar. It is the cheapest safety win available and it converts a
false marketing claim into a true one, which is the right direction of travel.
Into P0.10.

**D3.18 — Release blockers found by QA, 2026-08-03.**

**QA-5 — the namespace-isolation CI gate has never run.** `security-scan.yml`
invokes `pytest tests/security/test_isolation.py` with `working-directory:
backend-django`. That path does not exist — the real test sits at repo root as
`test_vector_namespace_isolation.py`. pytest exits 4, the job fails, and
`zap-api-scan` declares `needs: namespace-isolation-gate`, so **the OWASP scan
has never run either.** It is a weekly `schedule:` job, which is how a
permanently-red gate went unnoticed.

This is not an ordinary CI defect. That gate is the enforcement behind the
partner-boundary promise D5 tells us to lead with on professional surfaces. We
are about to tell clinicians the boundary is machine-checked.

**QA-3 — `make validate` cannot run on a clean machine.** Exit 127,
`ruff: command not found`, before a single test executes. `lint` calls bare
`ruff` while `test` and `safety-eval` do a `venv/bin` fallback. CI misses it
because the GitHub jobs pip-install into the job environment. `VALIDATION.md`
calls this "the single command to run before merging."

**QA-4** — Django's `.env.local` points at the docker-internal hostname
`postgres`, so the suite 100%-errors on the host without an override.

**Baseline is otherwise healthy: 1,908 tests pass** — 596 Flutter, 368 FastAPI,
944 Django, safety eval at 8/8 clear-crisis and 0/12 false positives.

**D3.19 — `CRISIS_RESOURCES` is unverified in deployment.**
`crisis_resources()` returns `[]` unless the env var is set. QA's gate proves the
plumbing is ungated; it cannot prove anything comes out of the other end.
Nothing in CI or on any checklist confirms the deployed value is set, non-empty,
and contains numbers a human has dialled. **Add a startup assertion and a release-
checklist item.** An ungated path to an empty list is the same outcome as a gate.

**D3.20 — A consent control that does nothing. Rulings on D-a/D-b/D-c.**
`UserConsent.session_transcript_retention` is a real field, surfaced as the
"Session storage" row *with an Edit link* on the sheet that blocks every session
— and **no retention path reads it.** Not a gap: a control that appears to work.
Masked today only because all three stores are empty, and it unmasks the moment
`persist_turn` is fixed. All three rulings point the same way — **make the code
match what the UI already promises.**

- **D-a: delete `counseling.Session.transcript`.** A built-but-unwired encrypted
  full-transcript field is a loaded gun. "We don't keep transcripts" is currently
  true by accident, and one helpful engineer connecting an unused field breaks it
  with no decision taken. Deleting makes the claim structural rather than
  incidental. If we ever want transcripts, that is a decision with a consent
  design attached, not a field someone wires up.
- **D-b: drop `summary_preview`.** Plaintext, 200 characters of what was actually
  said, and history is frozen anyway. It is the field that makes "we don't keep
  what you said" false.
- **D-c: gate extraction on `session_transcript_retention`.** One lookup. The
  alternative is a control users can see that does nothing, which is worse than
  never having offered it.

**D3.21 — The cohort is the only context where both partners are in the same
room.** Install→paired is ~6% today and every channel is throttled by it. In a
premarital class that constraint disappears: both partners are sitting together
with phones out while someone they trust tells them what to do.

**So: pair in the room, pay in the room, assess at home.** Pairing fails without
supervision and takes two minutes. Payment in the room also dissolves the D3.8
free ride, because nobody weighs skipping it while everyone around them is
paying.

**The questionnaire never happens in the room, and the reason is stronger than
convenience.** Two sessions reached this independently; the product session's
argument is the one to keep:

- **Co-presence corrupts the instrument.** The RSQ items doing the work are "I
  worry about being abandoned" (23), "I often worry that romantic partners won't
  want to stay with me" (21), "I often worry that romantic partners don't really
  love me" (11). Answering those on your phone with your fiancé beside you three
  weeks before the wedding is not the same measurement. Social-desirability bias
  is the best-documented threat to self-report, and physical co-presence of the
  person the items are *about* is its strongest trigger. We would sell a
  facilitator a report built in close to the worst available condition for the
  data, and print a methodology page describing it as self-report.
- **It fails worst exactly where it matters most.** Someone in a controlling
  dynamic will not answer item 23 honestly with their partner next to them —
  and that is precisely the couple a premarital facilitator most needs to see
  clearly. The co-present design silences them. This is a safety argument, not a
  psychometric one.
- **Visible dropout is a dignity problem.** A partner who is slower — second
  language, poor eyesight, dyslexia — is watched by the room not finishing.

Each partner completes the assessment separately before the next session. The
facilitator receives reports for session two, which is the cadence they already
run.

**One demo caveat for the session guide: the two-sided reveal cannot be shown in
the room.** Its whole mechanic is that neither partner sees the other's answer
until both are in. Side by side, it spoils — and it is exactly the thing a
facilitator will reach for when showing the app.

**Promoted to P0 by this:**
- **A short pairing code.** No QR, no code, no in-person pairing exists today —
  the invite is a token emailed to the partner's address. Emailing an invite to
  someone sitting beside you fails visibly on church-hall wifi, in front of the
  room, with the facilitator's reputation attached. A 6-character code is far
  less work than QR plus deep links and solves the same problem.
- **~~Deferred email verification~~ — likely no engineering needed.** Email
  signup routes to a mandatory OTP screen (`signup_screen.dart:115`), but
  **Google sign-in goes straight to `AuthLandingScreen` and skips verification
  entirely.** So the in-room fix is to make Google sign-in the primary path, with
  email as fallback — a CTA change, not a deferred-verification flow. Engineer to
  confirm; if it holds, this drops out of P0 having cost nothing.
- **A cohort tag on the purchase.** Small, and **unrecoverable if skipped**: you
  cannot reconstruct after the fact which couples were in cohort one. Without it
  nobody can tell a facilitator who has finished, and the post-cohort summary has
  nothing to compute from.

**Not promoted: shortening onboarding.** Marketing is right that a couple
abandoning at item 19 produces no report — but **D3.1 (answer persistence) is the
fix, not cutting the instrument.** With persistence a couple does ten items
tonight and twenty tomorrow. The RSQ cut stays P1.

**D3.22 — Reports are held, never sent partial.** They reach the facilitator 48h
before the session; an incomplete couple is held back. A half-report invites a
facilitator to draw conclusions from one partner's answers, which is the exact
asymmetry `boundary.py` exists to prevent. **Reminders go to the couple, never to
the facilitator** — a facilitator chasing 25 couples does not run cohort two.

**D3.23 — The scorer question is answered, and D3 was promoted on an analysis
its author has now retracted.** `docs/engineering/rsq-scoring.md`. The shipped
scorer is the published Griffin & Bartholomew (1994) instrument with **one item
wrong** — Dismissing uses item 28 where the key uses item 26 — not an invented
ad-hoc scale. The 14 "unused" items are Collins & Read AAS material this product
does not compute: **unused ≠ discarded in error.** Two real defects, both fixed
and merged: the item-26 index, and a blank submission returning `secure`.

**The corrected scorer does not compute model-of-other as a dimension.** On the
face of it that fires the P0.3 gate, because the report's pairing section
generates from two axes.

**It probably should not fire, and this needs verifying before anyone replans.**
The two axes are *derivable from the four prototype scores* — that is
Bartholomew's own construction, where secure = positive self + positive other,
dismissing = positive self + negative other, preoccupied = negative self +
positive other, fearful = negative self + negative other. So:

```
model_of_self  ≈ (secure + dismissing) − (fearful + preoccupied)
model_of_other ≈ (secure + preoccupied) − (fearful + dismissing)
```

**Verified, 2026-08-03, with one gap stated honestly.**

*Confirmed:* the RSQ is **fundamentally intended as a continuous measure of the
two dimensions** — Model of Self and Model of Other — with the four prototype
scores as the alternative scoring, not the primary one. And Bartholomew &
Horowitz's own definitions give exactly the 2×2 assignment above: secure =
positive self + positive other; dismissing = positive self + negative other;
preoccupied = negative self + positive other; fearful = negative self + negative
other. Griffin & Bartholomew's *"Models of the Self and Other: Fundamental
Dimensions Underlying Measures of Adult Attachment"* is the paper on precisely
this, and is the citation for the methodology page.

*Not confirmed:* I did not find the linear-combination formula stated verbatim in
an accessible source — Bartholomew's own lab site is offline. The combination
follows directly from the confirmed 2×2 structure and is standard practice, but
**it is a derivation, not a quotation.** Product should cite the dimensional
model, not a specific published formula, and say the axes are *derived from
prototype scores* rather than measured directly.

**So the two-axis report section is buildable today** with arithmetic on scores we
already compute — no new items, no questionnaire change. The P0.3 gate does not
fire.

**Empirically confirmed against the live scorer.** Product built the four
canonical prototype response patterns and ran them through:

```
prototype                   SELF   OTHER   max()
SECURE  (+self +other)      1.90    6.10   secure
PREOCC  (-self +other)     -4.40    2.80   anxious-preoccupied
DISMISS (+self -other)      5.20   -2.00   dismissive-avoidant
FEARFUL (-self -other)     -4.00   -4.00   fearful-avoidant
all-neutral (blank):        0.00    0.00
```

All four land in the correct quadrant, every sign right.

**D3.24 is resolved, and better than "chosen not measured."** A fully neutral
responder lands on **exactly (0.00, 0.00)**. Zero is the model's own boundary —
positive versus negative model-of-self/other *is* the four-category cut — and it
is empirically the neutral point of our own scorer. **`differing` = the partners
fall on opposite sides of zero.** Principled, needs no distribution, so n=1 does
not bite.

**Three constraints that travel with it:**
1. **Item 28 gets *better* under the derivation.** Under `max()` it appears in
   secure and dismissing with the same sign and cannot discriminate between them.
   Under the axes it double-weights on SELF and **cancels to exactly zero** on
   OTHER — and since item 28 is a model-of-self item, the sign is right and only
   the magnitude is wrong. P0.1 still fixes it; it is no longer inert.
2. **Never compare a SELF value to an OTHER value.** The subscales have different
   item counts and reversals, so the axes are not on a common scale — SECURE's
   SELF is +1.90 where DISMISS's is +5.20. Page 4 compares only *the two partners
   on the same axis*. **State this in the code** so nobody later renders both on
   one chart.
3. **The structure is Bartholomew's; the inputs are not.** This is a linear
   recombination of an unvalidated instrument. Page 8 says "two dimensions
   derived from prototype scores" — never "measured" — consistent with the
   "adapted from" wording D3.12 already requires.

**D3.24 — There is no axis distribution and there will not be one.** Profiles
with any `rsq_responses`: **1**, of 70. Product must choose a principled
threshold for `differing` and document it as **chosen, not measured**, then
revisit after the first cohort. The engineer's framing is right: anything else is
a midpoint dressed up as a finding, which is the same failure as an unnormed
report.

**D3.25 — The entitlement check on the counsellor fails OPEN.** If the lookup
errors — network, migration, bug — grant access rather than deny it. The
asymmetry decides it: wrongly granting costs a few dollars of tokens; wrongly
denying puts a card form in front of someone who opened a private session after a
fight. That is the D7 failure arriving through the paywall instead of the safety
path. It is also the discipline `assist.py` already follows — a broken classifier
never traps a message.

**D3.26 — Cost-per-couple is new instrumentation, not a read of existing
telemetry.** Nothing captures token usage anywhere: the provider returns it on
every response and `_complete` discards it. **Instrument the FastAPI counsellor
only**; skip the Django assist path in the first pass — it is short,
`gpt-4.1-mini`, lexicon-gated, and noise against a $0.60–3.00/month figure.
Attribution is the actual work, since `_complete` has no idea which couple it
serves.

**D3.27 — Both privacy statements are wrong, which resolves D-b.**
`counselor_sessions` holds 0 rows, so full transcripts genuinely are not stored —
but `langgraph_sessions` retains a plaintext `summary_preview`. So "deleted when
the session ends" is not quite true and "everything you have talked through
before" is materially false. **Dropping `summary_preview` per D-b makes the first
statement fully true**, and the You tab's promise goes.

**D3.28 — No premarital report is generated for a couple in crisis.** If either
partner's `relationship_stage` is `crisis`, `post_infidelity` or
`separation_considering`, the generator does not fall through to a
happy-Wednesday-in-three-years variant. Product's stronger recommendation is
adopted: **do not generate the document at all.**

But "not ready" must never reach the facilitator, because that is a disclosure
about the most sensitive field we hold, to someone who knows the couple by name —
D3.10's whole point. So:

- **The facilitator sees exactly what they see for an incomplete couple**: no
  report available, no reason given, no distinguishable state.
- **The couple is told plainly and gently** that this document is written for
  couples preparing to marry and does not fit where they are now; their
  counsellor access stands; support is one tap away.
- **No special refund path.** D3.9's 30-day no-questions policy already covers
  it. Building a "we noticed you're in crisis, here's your money back" flow would
  say the thing we just decided not to say.

**D3.29 — The supplement motion: sell to dioceses that have already chosen an
instrument.** Marketing found that dioceses typically approve several premarital
inventories rather than mandating one, and that a diocese requiring a *Nihil
Obstat* has a doctrinal gate we cannot pass — **visible on their website in under
a minute**, before any call is spent.

The reframe matters more than the filter: **in a diocese with a closed inventory
list we are not competing for the inventory slot at all — we are what the couple
keeps *after* the inventory.** We are not asking anyone to displace an instrument
their bishop approved, which is an easier conversation, and it converts a
disqualified segment into an addressable one.

Promoted into `go-to-market.md` §6.3 as a second motion. **One caveat that must
travel with it:** the supplement motion sells the app and the 12-month counsellor,
not the report — the inventory already occupies the report's job. So product's
open question ("can the app justify $39 on its own?") becomes live specifically
for this motion, where it was previously answerable by pointing at the report.
Test it inside the first ten calls rather than after.

**D3.30 — `docs/execution-plan.md` is the decision log.** Every D-number lands
here as it is taken. Sessions should read it before reasoning about a decision
rather than waiting to be told — two sessions have now argued against rulings
that already existed. Checking is cheaper than broadcasting.

**D3.31 — A refusal is a capability claim in the negative, and fails the same
way.** "We chose not to build X" is only honest when we *could* have built X.
A limitation dressed as a principled refusal is worse than a plainly stated
limitation, because a professional reader can tell the difference and will
downgrade everything else we said.

**Test: if the sentence would still be true had we tried harder, it is a
limitation, not a refusal.**

| Refusal — may be written as proof | Limitation — state flat, unhedged |
|---|---|
| No compatibility score | The instrument is not psychometrically validated |
| No partner profile | Self-report at one point in time |
| No risk flags to the facilitator | No norming data |
| No transcripts retained | The report can be wrong |
| No cohort rankings | No real cohorts have run |

**Every refusal written as proof must have a test behind it** — the boundary
import test, the entitlement allowlist, the disclosure rule, the D7 static
assertion. A refusal without enforcement is in the same category as the four
capability claims the audit struck, so **refusals go through D3.16 before they
go into copy.**

The flat column is what buys the credibility the proof column then spends.

**D3.32 — Unrecoverable outranks slow.** A completion view can be added in month
three at no cost; **who was in cohort one cannot be reconstructed.** Anything
that silently discards history it cannot rebuild outranks work that is merely
harder later — the same argument that puts the event schema before the traffic
it measures. Apply it when sequencing, not just to the cohort tag.

**D3.33 — Persistence converts abandonment into stalling, so the cohort-one
metric is "both partners complete."** With draft-save, a couple lost at item 19
becomes a couple *parked* at item 19 — and because incomplete reports are held
rather than sent partial (D3.22), the facilitator still gets nothing. Same
failure, but it stops announcing itself: a couple who quit looks like a couple
who will finish tomorrow.

So the day-3 reminder matters *more* under persistence, not less, and the number
that decides whether the RSQ cut gets promoted on evidence is
**both-partners-complete rate**, not abandonment.

**D3.34 — When a document's subject changes, the documents that frame it go
stale even though nothing in them was edited.** The third direction of the D3.16
trap: not a claim that was never true, and not one a business decision
invalidated (D3.16a), but one that quietly stopped matching a sibling document.

Found across six defects in the report spec — page 1 described "how each of you
tends to approach closeness," which is pages 2–4, while page 5 is 40 of the 90
minutes; page 8 named one instrument of three, so a professional asking where the
family question came from found no answer on the page that exists to answer it.
Both pages were correct when written. The pages they framed changed underneath
them.

**Checklist item whenever a spec ships: what framed this, and does it still
describe it?**

**D3.35 — v1 ships with no humans in the loop. No clinicians, no coaches, no
therapist supply.** *(Founder decision, 2026-08-03.)* Most of this already
followed from D2: the $49 guided tier and the therapist-seat SKU died with the
single price. This confirms the direction and closes it.

**The distinction that matters: a facilitator is not a clinician.** The entire
distribution plan sells to premarital programme coordinators — diocesan Family
Life staff, parish volunteers, programme leads. They already exist, already run
cohorts, already do this work, and they are **buyers, not supply.** We do not
recruit, schedule, pay, train, or carry liability for them. Nothing in the
channel plan is affected by this decision.

**What is cut:** the five couples-therapist targets from the outreach list — not
because a referring therapist is supply (they aren't), but because it is a
trickle channel (couples arriving one at a time) against a cohort channel (25 at
once), and a one-off price makes cohorts strictly better. Focus, not principle.

**The therapist portal is frozen, not deleted.** It is only ~425 lines, but
`therapist` is woven through the **consent** system — `models.py`,
`constants.py`, `access_policy.py`, `gate.py`, `serializers.py` — and through
safety. Removing it means surgery on the most sensitive code in the product, in
the exact area where D3.20 just found a consent control that does nothing.
**Freezing costs nothing; deleting costs risky work in the consent layer with no
revenue attached.** Revisit only if it obstructs something.

**The honest cost, which must be a decision rather than an omission:**
`go-to-market.md` §9 assumed budget for human review of every safety escalation.
With no clinicians, **that reviewer is the founder.** At 25–75 couples it is
feasible; it is also a standing, unscheduled commitment, and a crisis flag at
11pm does not wait for business hours. This is the single operational cost the
decision does not remove.

**What gets cleaner:** positioning. No humans in the loop means no ambiguity
about whether we provide licensed care, which is the largest App Store risk in
this category. The in-app AI disclosure already exists and is correct.

**D3.36 — The AI disclosure banner comes off the three non-AI tabs and stays on
the session surfaces.** It currently sits permanently on all four tabs *and*
again inside every chat. A permanent warning stops being read within a day while
still costing vertical space on every screen — and banner blindness on Today, Us
and You makes the disclosure *less* effective on the one surface where it
matters.

Keep it on **Talk** (the entry point to AI conversation) and inside **every
session**. Remove from Today, Us and You. The disclosure is then present wherever
an AI conversation is happening or one tap away, which is what the claim needs to
be true.

Compliance-adjacent, so: reversible on a single reviewer objection, and the
in-session disclosure — the one that matters in App Store review — is untouched
and stays visible without interaction.

**D3.37 — "14 of 30 items are never read" is withdrawn as an argument.** It was
used as evidence against the word "validated." It is wrong: the scorer reads 17
of 30, and the remainder are unread because the RSQ embeds Collins & Read AAS
material belonging to subscales this product does not compute. **Correct by
design, not a defect.**

**The "validated" verdict is unchanged** — it rests on ad-hoc subscales, no
norming sample and no reliability figures, none of which the item count touches.
Removing the bad argument makes the remaining case stronger. **Do not use the
item-count point in any copy or facilitator conversation.**

**D3.38 — Agreeing detail is where errors hide.** Four corrections in three days.
The two caught by the author re-reading their own work were found *faster* than
the two caught by review — and D3.37's bad argument would have been close to
invisible to review, because it looked like a supporting detail on a verdict
everybody already agreed with. **Nobody re-checks an argument that reached the
right answer.**

Two practical consequences: re-read your own work rather than waiting for review
to catch it, and when auditing, check the *supporting* claims under conclusions
you agree with — not just the conclusions you dispute.

D3.37 also has a shape worth noting: **it is the only error found this week that
ran in the direction of understating the product.** Safer, and no more true.

**D3.39 — Two live surfaces advertise a therapist nobody can have. Hide the row;
do not touch the backend.** `consent_dashboard_screen.dart:197` renders a
**"Therapist access"** row unconditionally — *"Your therapist cannot see your
sessions"* — and the same row appears on the in-session consent sheet that blocks
every session.

The sentence is not false; there is no therapist, so none can see anything. It is
a **control implying a capability v1 does not have** — D3.16's shape appearing in
the UI instead of in copy. A user may reasonably wonder whether we have connected
someone, and a facilitator vetting us will ask about a clinician network we do
not have, on a screen we chose to show them.

**Fix: conditional rendering when the user has no therapist connection.** No
model change, no migration, **no consent surgery** — line 70 of the same file
already does exactly this for the "What your therapist can see" section. Into
P0.10.

Freeze the backend (D3.35), hide the surface. They are separable and only one is
risky.

**D3.40 — Retention needs an expiring justification.** "Might be useful later"
keeps everything forever and cannot be checked. **"Removal is riskier than
retention, and here is the coupling"** is checkable, and it *expires when the
coupling does.* Applied to the therapist portal: retained because `therapist`
runs through five consent files including `access_policy.py` and `gate.py`, plus
two migrations and safety. Use this form for anything else the freeze keeps.

**D3.41 — The facilitator's own referral network is the entire safety net, and
the guide says so.** Three decisions combine into something none of them creates
alone: the software declines to produce the report for a couple in crisis
(D3.28); it tells the facilitator nothing, because telling them is the
risk-flagging we refused (D3.4); and we have no clinician to refer anyone to
(D3.35).

The session guide now states it plainly — *"We have no clinicians and we are not
a referral service… it cannot hand a couple to a professional and we will not
pretend otherwise."* **Any edit that warms this into something friendlier is
reject-on-sight.** A facilitator who half-believes we can hand a couple onward is
worse off than one who knows the referral is entirely theirs — they would be
relying on something that does not exist, at the moment it mattered most.

**D3.42 — The report will never contain a 2×2 with the couple plotted on it.**
*(Design's refusal, adopted.)* The content spec bans printed numbers because they
invite comparison. **A diagram with two dots is two numbers plus a third the
couple invents — the distance between them — rendered more memorably than digits
would be.** It is D3.4's compatibility score with better graphic design.

A diagram of the *model* on the methodology page is fine. A diagram with *your
dot on it* is not.

**D3.43 — Every primary button in the app fails contrast, in both directions at
once.** `onPrimary: Colors.white` on coral measures **2.04:1** — below even the
large-text floor. And because no `elevatedButtonTheme` existed, the 39
`ElevatedButton`s that *didn't* override it inherited Material's default of
primary-on-surfaceContainerLow: coral on cream, **1.98:1**. Styled buttons failed
one way, unstyled buttons failed the other.

The fix is **not** to darken coral — that lands on `#E82200`, one step from the
reserved crisis red (D7's palette reservation). Keep the fill, darken the ink to
`#3B2A24`: clears 4.5:1 on every fill in the palette, preserves the reservation,
and reads as paper rather than as a notification.

**D3.44 — Twenty of twenty-six `ColorScheme` roles were unset, so the
counsellor's reply bubble rendered in Material's default lavender.** Any widget
touching an unset role silently imported another design system — on the one
surface the $39 buys. Fixed at the root so it cannot recur by accident.

**D3.45 — Two motion curves contradict the brand.** `Curves.elasticOut` and
`Curves.easeOutBack` overshoot — a confetti gesture, and the motion signature of
exactly the streak-and-badge product this one deliberately is not. Also:
`AppTheme.slowFade`/`gentleMotion`/`orbAnimation` have existed since the first
commit and are referenced by **nothing**, while 47 animations each chose their own
number across 14 durations; and reduced motion is honoured in **zero** of 187
files.

**D3.46 — A good empty state on a broken feature is how the breakage stays
hidden.** Design applied the D3.13 rule and found two more surfaces that must not
be designed yet: **session history** — which "currently has one of the *better*
empty states in the app, which is precisely how a wholly broken feature went
unnoticed" — and the **memory transparency panel**, unverified and the same
shape. Session history is resolved by D3.13 (we remove the promise, so the empty
state is moot). **The memory transparency panel goes to product as a claim-audit
item**: `memory_vectors` holds 0 rows and its writer is a stub, so whatever that
panel is showing needs checking before anyone styles it.

**D3.47 — The design rules were all true once, and came back because nothing
enforced them.** The existing code comments describe a previous cleanup of
exactly these categories. **`docs/design/audit.md` item 21 — the CI grep — is the
highest-leverage item in the design work**, not the visual fixes. Same
construction as the support-icon static test and the boundary import test: fails
in both directions, allowlist carries a reason per line. This is
`an invariant a person has to remember is not an invariant` applied to design.

**D3.48 — There is no therapist portal. There is a REST API with no client.**
`apps/therapist/` has a login view and viewsets for connections and strategy
notes, and **nothing to log into** — no mobile feature, no web app, no templates.
Verified 2026-08-03.

So D3.35's "frozen" understated it: the portal was never a surface, only an
interface. **The therapist offer is a referral plus a report delivered to them —
not an account they use.** The words *portal, dashboard, account, log in* are
prohibited in all therapist-facing copy.

This is the fourth capability claim that would have shipped from a document
rather than from code — and the PM brief that commissioned this channel repeated
it, having taken the language from `go-to-market.md` §6.3(b) without checking.
**A claim laundered through a plan document arrives looking like a decision.**

**D3.49 — Therapists cannot be the scale engine, and the doc says so.**
~171 active therapists for $100k → 1,100–1,700 contacted → **five to eight years
at four a week.** Facilitator ~$4,680/yr against therapist ~$390–780/yr is a
6–12× gap per relationship. Recorded so the question does not reopen.

**Dual ramp:** therapists from month 1, programmes from ~month 6.
**Year one ~$16k, exiting month 12 at ~$41k/yr, $100k around month 24–30.**

**The cost of the reversal, stated plainly:** ~$16k in year one against
facilitator-first's ~$54k, and $100k pushed out six to twelve months. The
counter-argument, which is the right one: **the $54k required conservative
institutions to say yes to an unproven product with no users, no outcomes, no
references and a discoverable `spicy` category. A lower number at higher
probability beats a higher number that depended on the hardest possible first
customer.**

**D3.50 — With a one-off price and a trickle channel, referral is the only thing
that compounds.** Nothing else in the model does: a therapist sending 10–20
couples a year is a flat annuity, and the $39 does not recur. The couple-code
(Loop 2) and the shareable portrait were sequenced as P2/P3 growth features on
the assumption that cohorts carried volume. **Under D3.49 they carry more weight,
not less** — revisit their priority once the product is stable enough to be worth
referring.

**D3.51 — The intimacy content stays. The packaging goes. The entry point gets
gated.** `docs/specs/intimacy-content-position.md`.

**The content is clinically ordinary.** One pack of nine, `After Dark`: *"My
favourite kind of affection is…"*, *"I feel most desired when you…"*, *"My ideal
romantic evening is…"* That is closer to a Gottman Love Maps exercise than to an
adult game, and desire is standard couples-therapy territory — Gottman, EFT and
sensate focus all address it directly. **Removing it would weaken us in the
therapist channel, not protect us**: a couples product that cannot mention desire
is conspicuously avoiding something every clinician in that channel handles
routinely, and the avoidance is more noticeable than the content.

**"Spicy" and 🌶️ are the whole problem.** A therapist recommending this would
have to explain a chilli pepper, and having to explain it is exactly why they
would not recommend it. Rename the category to `intimacy`, drop the emoji.
Both are safe to change: `category` is internal, `After Dark` is a fine pack
name, and **no user has ever seen either** — `GameConsent` is 0 rows and
`age_verified` is 0 of 1,416.

**The actual defect is the ungated affordance.** `games_list_screen.dart` puts a
🌶️ `IconButton` in the Games app bar **unconditionally**, tooltip "Spicy games",
before any opt-in, for every user including couples who will never enable it and
anyone glancing at the phone. Server-side gating is correct; the *affordance* is
not gated at all. This is the same error this codebase already diagnosed and
fixed elsewhere — *"a navigation menu disguised as chrome."* Move it into
preferences, found deliberately.

**D3.52 — Opting out of intimacy content must be unilateral, silent and
immediate.** The double opt-in is justified in code as "symmetric rather than one
partner enabling adult content for the other." The stronger reason is
**coercion**: one partner asking the other to opt in to sexual content is a
pressure point, and it lands hardest in exactly the relationships this product is
careful about everywhere else. The symmetric gate cannot remove that pressure —
nothing in software can — but it ensures **the app is never the mechanism**.

The missing half: **either partner revokes, the packs vanish, and the other is
not told who did it.** A gate requiring both to enable *and* both to disable
would be worse than no gate, because withdrawal would become a negotiation.
**Current behaviour is unverified — verify before shipping the rename.**

**D3.53 — The intimacy gate is fail-closed by accident, not by design.**
`age_verified` is **0 of 1,416**, so the open path has never executed. Same
category as the memory pipeline, less severe. **It needs a test before the rename
ships.**

**App Store rating:** answer the rating questionnaire truthfully at submission
and accept whatever it returns. The rename is for the therapist channel, not for
review — do not let rating-avoidance become its motivation.

**D3.54 — The couple-code doesn't survive the single price, and it needs
redesigning rather than re-prioritising.** `go-to-market.md` §5.5 gives a
referred couple **"30 days free."** Under a $39 one-off there is no subscription
to comp — nothing to give away by extending time. Same class of survival as the
licence ladder: a mechanic written under one pricing model, still sitting in the
doc after the model changed, **looking finished.**

**Test the zero-incentive version first — just a share link.** It costs nothing,
the two paid alternatives (a discount on the referred couple's $39, or a credit
to the referrer) are only worth building if it fails, and in a category where
people recommend things they love unprompted it may simply be sufficient. It also
largely rides on infrastructure already in P0: the post-purchase share action is
specified as the same share sheet as the in-app invite, built once.

**A sweep is owed of anything else written pre-D2 that assumes recurrence.**
The stale-reference checker will not catch this class — the citation is valid,
the *assumption underneath it* is dead.

**D3.55 — Referral is worth roughly a doubling, and it is the only lever left
that does not consume founder-hours.** Steady-state volume multiplies by
`1/(1−R)`:

| R | Multiplier | Year-1 revenue | Month-12 run rate |
|---|---|---|---|
| 0 (today) | 1.00× | ~$16,000 | ~$41k/yr |
| 0.30 | 1.43× | ~$22,900 | ~$59k/yr |
| **0.50** | **2.00×** | **~$32,000** | **~$82k/yr** |

At R = 0.5 the month-12 run rate approaches $100k **without adding a single
facilitator.**

**The precondition binds harder than "wait until it's good."** A referral
mechanic shipped onto a product people do not yet recommend produces R = 0 **and
a false negative about the whole lever** — which is worse than not shipping it,
because it would look like evidence and would be cited later as proof referral
does not work here.

**Sequencing: after the counsellor memory and the turn-depth fix — but not at P2
behind six months of cohort features.** The ramp table is the argument for
moving it.

**D3.56 — Not every recurrence is a pattern needing machinery.** The
ungated-affordance defect was swept and is **bounded: two instances, one fixed
(the Us tab, now guarded on `connected`), one specced (the 🌶️ entry point).** No
other app-bar action leads somewhere gated; no other engagement endpoint fails on
a missing partner.

The distinction worth keeping, because this week produced five rules and the
sixth would have been wrong:

- **D0.5 earned its rule** because each instance survived for a *structural*
  reason — distance between the surface and the code that would make it true.
  Structure recurs whether or not anyone is paying attention.
- **This one recurred because two people made the same local judgement twice.**
  The fix is the fix. A rule here would mostly duplicate the support-icon static
  test and add a gate nobody needs to pass.

**Test before mechanising: does the next instance arrive because of how the
system is shaped, or because someone made a call?** Only the first needs a
machine.

**D3.57 — There is no churn in this business, and revenue retention must never be
reported as a metric.** A couple cannot churn from a purchase they already
completed. Two things replace it, and they point in opposite directions:

- **Usage retention** — week-4 activity. Under a one-off this **costs** money
  rather than earning it. It is kept as a metric only because it is the leading
  indicator for referral (D3.55), which is the one thing that compounds. It is
  not a revenue signal and should never be presented as one.
- **Relationship retention** — whether a therapist keeps referring and a
  facilitator runs cohort two. **These are the only recurring things in this
  business**, which is why D3.49 counts active relationships rather than couples.

**D3.58 — The recurrence sweep found five more, all the same class: a valid
citation resting on a dead assumption.** All in `go-to-market.md`;
`marketing-copy.md` came back clean.

- **§3.1 contradicted §5.2 for days** — "gross margin at $14.99/month is 92–96%"
  (a monthly margin against a monthly price, neither of which exists) against
  §5.2's correct one-off runway model. Two sections, opposite frames, each
  internally plausible, so neither looked wrong alone. **Under a one-off, cost is
  not a margin percentage — it is how long the couple stays profitable**, which
  is exactly why D3.11a bounds the counsellor at 12 months.
- **§6.6's anti-paid-install case was sized on $90–150 first-year ARPU** —
  subscription-era. The real figure is $39 once, so the number was 2–4× wrong
  **in the direction that made paid installs look better than they are.**
- **§2.2's "wide-open gap between $15/month and $436/month"** — withdrawn. There
  is no band to occupy at $39 once. Prepare/Enrich at $35–65 one-off is the row
  that still does work.
- **§9's churn paragraph** — replaced per D3.57.
- **The event schema still emitted `trial start`.** No trial exists. Now
  `purchase` — and it would otherwise have shipped into the taxonomy the engineer
  is wiring and produced an event nobody could explain in three months.

**The detector is not textual, and it is cheap.** A stale-reference checker
cannot see this class: the citation is correct, the sentence parses, the number
is internally consistent, and only the pricing model underneath is dead.
**But any sentence containing a per-period unit — /month, /year, annual,
monthly, churn, retention, LTV, ARPU — is suspect by construction in a one-off
business.** That grep found all five in about a minute. It goes to QA as a lint,
not a review pass.

**D3.59 — For a therapist, the disclosure threat model inverts: the risk is what
we *retain*, not what we *show*.** The cohort rule was written against a
facilitator — someone who knows the couples socially, must not learn what any
couple answered, and whose side information defeats k-anonymity at any k.

**A therapist's side information is not merely large, it is the point.** They sit
with the couple weekly; anything a summary could tell them about their own
clients they already know better, from the source, with context we do not have.
The disclosure risk we designed against is close to zero here.

A different risk replaces it:

> We would be creating a written record about a therapist's clients, held on our
> servers, that neither the therapist nor the couple asked us to keep.

Discoverable, breachable, and subject to a duty of confidentiality that is
**theirs rather than ours**. A therapist asks what we *retain* about their
clients long before they ask what we *show* them — the opposite of the question
a facilitator asks.

**The tell was Rule 4.** N=5 banding is almost always active at therapist scale —
three client couples trips it on every statistic. That is not conservatism, it is
a signal the mechanism is wrong for the channel. **So the therapist rule is a
subset, not a variant: per-couple status only, no aggregate generated at all.**
Simpler than the cohort rule and strictly safer. Rules 1–3 continue to govern the
programme channel from ~month 6.

**D3.60 — Two report properties get *stronger* in the therapist channel.**
Symmetry — everyone holds the identical document — moves from a design principle
to a clinical-ethics one, because a therapist holding a version the couple cannot
see is a different category of problem than a facilitator doing so. And page 8's
four admissions (derived, relative, not normed, threshold chosen) become the
highest-value paragraph in the artefact rather than a candour flourish, because a
couples therapist is far more likely than a parish coordinator to recognise the
instrument.

**D8 — Feature freeze.** No new feature areas. Twenty-one is already the problem
(`product-assessment.md` §2.8). Everything below is finishing, fixing, or
selling what exists.

## 4. Ownership — who writes what

File collisions are the main risk with four sessions. These boundaries are hard.

| Session | Owns (writes) | Never writes |
|---|---|---|
| **Engineer** `local_b69883b7` | `mobile/lib/**`, `backend-django/**`, `backend-fastapi/**` | `docs/marketing-copy.md`, `docs/go-to-market.md` |
| **Product/design** `local_81faf803` | `docs/product-assessment.md`, `docs/specs/**`, acceptance criteria, artefact design | any code |
| **Marketing** `local_b3113dec` | `docs/go-to-market.md`, `docs/marketing-copy.md`, landing page, outreach | any code, any product spec |
| **QA — correctness** | `tests/**`, `docs/qa/crisis-gating.md`, `docs/qa/money-path.md` | product code |
| **QA — production readiness** | `docs/qa/production-readiness.md`, `docs/qa/smoke.md`, `docs/qa/load.md` | product code |

Two QA agents run in parallel with split scopes. **Correctness** owns the money
path, the D7 crisis-gating test, and RSQ scorer regression. **Production
readiness** owns the smoke suite, load testing against the real arrival pattern
(a 25–40 couple cohort onboarding inside an hour, not a smooth ramp), and the
production-risk assessment — including whether anything logs message content or
PII, which for a counselling product is a launch blocker rather than a defect.
Neither fixes product code; both report to PM.

Product and marketing propose code changes by writing them into a spec and
handing it to the engineer. Only the engineer commits code.

## 4a. Build order

**`docs/specs/README.md` §1 is the authoritative build order** — seven hard
dependencies across thirteen specs, each stated with its *consequence* rather
than its rule, because "wait for X" gets ignored and "this loses the user's forty
answers" does not. Read it before starting any spec. §2 lists what is buildable
now with nothing blocking it, which is most of it.

The failure it exists to prevent: every spec states its own preconditions, but
only *inside itself* — so the constraint that stops someone building in the wrong
order lives in a document they may open after they have started.

## 5. The work, in order

### P0 — the money path (weeks 0–3). Nothing else ships first.

| # | Work | Owner |
|---|---|---|
| P0.1 | Fix the RSQ scorer — score model-of-other, correct the 2×2 placement, keep old blobs readable without migration | Engineer |
| P0.2 | Web checkout: Stripe + Paystack, **one $39 SKU**, one permanent entitlement flag, and an invoice/bank-transfer path (churches often cannot pay by card). No renewal, no trial, no tiers. **Batch codes moved to P1** per D2.2 | Engineer |
| P0.3 | The facilitator report artefact — printable per-couple PDF a facilitator can teach from | Product designs → Engineer builds |
| P0.4 | Analytics: wire `setConsent` to the consent flow + the funnel events. **Two days, hard stop** | Engineer |
| P0.5 | Landing page + checkout page the sale runs through | Marketing |
| P0.6 | Rewrite `go-to-market.md` §5 to the single $39 price; re-target §6 volumes against 2,564 couples | Marketing |
| P0.7 | Facilitator outreach: **60 contacted, 20 calls booked** (raised from 30/10 — see §2) | Marketing |
| P0.8 | Money-path E2E test, and the D7 crisis-gating test | QA |
| P0.9 | **Onboarding must survive interruption** — incremental save / draft endpoint. See D3.1 | Engineer |
| P0.10 | **Credibility pass** — the five things a facilitator sees in ten minutes (D3.2), plus **the support icon on all 53 screens** (D3.17) and `persist_turn` logging (D3.13) | Engineer |
| P0.11 | Completion certificate — one page, generated with the report | Product specs → Engineer builds |

**Gate on P0.3:** if P0.1 (the RSQ scorer) slips, the report does not ship to
professionals. The pairing section generates from two axes — model-of-self and
model-of-other. Without model-of-other there is one usable axis, the pairing page
collapses to a label comparison, and the methodology page cannot honestly
describe a 2×2. A thin artefact in the one channel where thin is fatal is worse
than a late one.

### P1 — activation (weeks 2–5)

RSQ cut to 22 items with progressive profiling and no hard gate · share-sheet
invite, WhatsApp first · store metadata, ASO and the `pubspec` description ·
first 50 couples recruited by hand, two interviews a week.

### P2 — retention (weeks 5–10)

Daily-question beat job, routed through `CouplePolicy` suppression **and** the
rupture rule — no "today's question is ready" push the morning after a fight ·
notification controls for all 19 types · hub badges.

## 6. The five numbers

Unchanged from `go-to-market.md` §8, plus one:

| Metric | Target |
|---|---|
| **Active facilitators** | **21 by month 12** |
| **Cohorts per facilitator per year** | **≥3** |
| Install → paired couple | >20% |
| Invite send rate | >60% of activated |
| Invite accept rate | >60% |
| Week-4 couple **usage** (see below) | >40% |
| **Cohorts closed per 10 facilitator calls** | **>3** |
| **Couples redeemed per cohort sold** | **>70%** |

"Trial → paid" is deleted — D2 removed the trial. Its replacement is the
redemption rate: a facilitator buying 30 codes of which 12 are redeemed is a
refund conversation and a churned channel, so this is the number that tells us
whether the cohort sale is real.

Plus the qualitative gate: two couple interviews per week, written down.

## 7. What would change my mind

- If fewer than 2 of the first 10 facilitator calls convert, the institutional
  channel is wrong for a solo founder and we fall back to the consumer
  subscription with the invite loop as the only engine.
- If the Phase-0 fixes do not move install→paired above 15%, no channel saves
  it and the problem is the product (`go-to-market.md` §9).
- If Apple rejects on clinical-claims grounds, the web-first decision in D1 goes
  from convenient to load-bearing and the app-store path gets re-planned.
