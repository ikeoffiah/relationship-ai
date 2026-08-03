# P0 — engineering status, estimates, and three corrections

Engineer, 2026-08-03. Written down because these answers have crossed with
incoming scope four times in chat. Anything the PM is waiting on is here.

## The question that gates the replan

**Is the RSQ fix deeper than a scorer change? No.** Answered in full in
`rsq-scoring.md`. Every stored blob has all 30 items and structurally always
will, because the hard gate forced completion. No migration, no backfill.
**P0.1 is done and merged.**

## Estimates

| Item | Estimate | State |
|---|---|---|
| P0.1 RSQ scorer | 1 day | **done** |
| P0.2 Checkout + entitlement | 3–4 days | blocked on payment accounts |
| P0.3 Facilitator report | 3–4 days | spec landed, not started |
| P0.4 Analytics + COGS | **see correction 1** | not started |
| P0.9 Onboarding draft save | 0.5–1 day | confirmed small |
| P0.10 Credibility pass | 0.25 day | **2 of 5 already shipped** |
| P0.11 Certificate | 0.5 day | rides P0.3's pipeline |

## Correction 1 — token usage is not being captured anywhere

The brief says cost-per-couple can come "from the token usage you already have
going through `model_config.py`". It cannot. Searching both services for
`usage` / `prompt_tokens` / `completion_tokens` / `total_tokens` returns
**nothing**. The provider returns usage on every response; `_complete` in
`chat/assist.py` discards it, and `model_config.py` lives in **backend-fastapi**,
a different service from the one that grep was aimed at.

So this is new instrumentation, not a read of existing telemetry. Two costs:

1. **Attribution.** `_complete(system, user, timeout, ...)` has no idea which
   couple it is serving. Callers do. Getting cost *per couple* means threading a
   relationship through every call site or a context-local — that is the work,
   not the arithmetic.
2. **Two services.** The counsellor lives in FastAPI; the assist path in Django.
   Cost-per-couple spans both.

**Recommendation: instrument the FastAPI counsellor only, and skip the Django
assist path in the first pass.** The PM's own note says the counsellor is the
only expensive surface. The assist path is short, `gpt-4.1-mini`, and gated
behind a local lexicon — it is noise against a $0.60–3.00/month figure.
Counsellor-only fits the two-day box alongside `setConsent` and the funnel
events. Both services would not.

**This also affects the QA agent measuring §3.1 under load.** If they assumed
existing telemetry, they are measuring an estimate too.

## Correction 2 — the axis-distribution handoff cannot be delivered

Product is blocked on "the axis distribution across existing profiles" to set a
real threshold for `differing`. There is no distribution to give:

```
profiles with any rsq_responses : 1   (of 70 — the rest are my test users)
```

**n = 1.** Waiting does not help; there is no data and none is arriving before
the first cohort. Product should choose a principled threshold and document it
as chosen-not-measured, then revisit after the first cohort. Anything else is a
midpoint dressed up as a finding — which is the same failure mode as the
unnormed report.

## Correction 3 — P0.10 is mostly done

Shipped and on `main` already: `SafeArea` on the disclosure banner, and the
purple strategy chip deleted. Remaining: joint-session title, first-run chat
empty state, and the privacy contradiction — which needs Product to decide which
statement is true before any copy changes. For that last one, the fact neither
document has: **both statements are wrong.** `counselor_sessions` holds 0 rows,
so full transcripts genuinely are not stored — but `langgraph_sessions` retains
a plaintext `summary_preview`. So "deleted when the session ends" is not quite
true, and "everything you have talked through before" is materially false.

## On the counsellor paywall — one design recommendation

D3.11 puts the AI counsellor behind the $39 gate. One flag, several call sites;
that is not per-feature entitlement logic and does not need escalating.

**The entitlement check on the counsellor should fail *open*.** If the lookup
errors — network, migration, bug — grant access rather than deny it. The
asymmetry is the whole argument: wrongly granting costs a few dollars of tokens;
wrongly denying puts a card form in front of someone who opened a private
session after a fight. That is the failure D7 exists to prevent, arriving
through the paywall instead of the safety path. It is also the discipline
`assist.py` already follows everywhere else — a broken classifier never traps a
message.

D7 itself will be structural: the safety and crisis modules will not import the
entitlement module at all, so a violation cannot be written rather than merely
being tested for.
