# Smoke suite

Owner: QA. The short, fast, deterministic set that must pass before any release.

```bash
docker compose up -d                      # a running stack is a precondition
python3 tests/production/smoke.py         # ~18s, spends one gpt-4o completion
python3 tests/production/smoke.py --no-llm   # free; skips the two paid steps
python3 tests/production/smoke.py --json     # machine-readable summary
```

Exit code is 0 only if every automated assertion passes. Manual steps are
printed but do not affect the exit code — they are printed precisely so that
nobody can pretend they were covered.

## What it is, and what it deliberately is not

It is a **release gate**, not a test suite. `make validate` already runs the
unit suites and the safety eval with no external keys; `make e2e` and
`make scenarios` already exercise conversation-level behaviour against a live
model. This sits between them: it asks whether a *deployed stack* can carry one
person from signup to a counselling reply without anything falling over.

Design rules, because a smoke suite that drifts stops meaning anything:

- **Fast and deterministic.** Under 20 seconds. Nothing sleeps waiting for a
  beat job. Nothing asserts on model wording — only on shape and on the
  guarantees.
- **Stdlib only.** It has to run from a bare shell on a deploy box, not from a
  configured virtualenv. `urllib`, `json`, `subprocess`, nothing else.
- **Every path is either automated or printed as an explicit `MANUAL` step.**
  A path that cannot be automated without live keys gets named out loud, with
  the manual procedure written down, rather than quietly dropped.
- **Assertions carry their own explanation.** A failing check prints the file
  and line of the defect it is detecting, so whoever runs it at 2am does not
  have to come back here.

`docker compose exec` is used for exactly one thing: minting a pairing invite
token. The invite API only ever emails the raw token — correctly, since a token
returned in an API response is a token an attacker can enumerate — so the
*setup* comes from the database and the *accept* still goes through the real
view. Same reasoning, and the same helper shape, as `scripts/e2e/harness.py`.

## Coverage

| # | Step | Automated | Notes |
|---|---|---|---|
| 0 | stack reachable | yes | Django responds; FastAPI `/health`; asserts Django *has* a health endpoint |
| 1 | signup | yes | both partners, token TTL, `/auth/me/`, bad token rejected |
| 2 | onboarding | yes | RSQ served, consent record + closed defaults, RSQ submitted, attachment style derived, portrait produced |
| 3 | pairing | yes | invite issued, invite latency budget, no raw token in the response, accept, relationship active, third party cannot redeem |
| 4 | daily question | yes | served, answered by A, **not revealed to B before B answers**, answered by B, both reveal |
| 5 | counselling turn | yes (paid) | SSE 200, terminates with `done`, non-empty reply, **not the provider fallback**, no spurious safety event, under 30s, unauthenticated refused |
| 6 | safety classifier | yes | layer-1 in-process on two clear crises and two known traps; live crisis over the wire raises `safety_triggered` at `level=critical`; crisis resources non-empty |
| 7 | checkout | **no — MANUAL** | not implemented (execution-plan P0.2) |

### Why these and not others

Steps 3 and 4 assert the *negative* as well as the positive: that an invite
cannot be redeemed by a third party, and that A's answer is not visible to B
before B answers. Those two are the product's actual promises. A daily-question
test that only checks both answers appear would pass on a build that leaked the
partner's answer early, which is the failure that matters.

Step 5 asserts that the reply is **not** `llm_provider.FALLBACK_REPLY`. That
looks like an odd thing to gate on until you read
`backend-fastapi/app/orchestration/llm_provider.py:67`, which swallows every
provider exception with no log and no Sentry capture. A wrong key in production
produces a warm, plausible holding reply to every user and nothing anywhere
else. This assertion is currently the only mechanism that would surface it.

## Manual steps

### Checkout — not implemented

There is no Stripe, Paystack, entitlement or redemption code in the repo
(execution-plan P0.2). When it lands, this step must assert:

1. A completed test-mode payment sets exactly one permanent entitlement flag,
   covering **both** partners.
2. A batch of facilitator redemption codes can be issued, and each code redeems
   exactly once.
3. A replayed webhook does not double-grant.
4. Nothing on the crisis path is gated by the entitlement check (D7). The
   authoritative version of that test is the other QA session's, in
   `docs/qa/crisis-gating.md`; this step should call it rather than restate it.

Stripe and Paystack test keys are required, so this cannot run key-free in CI.
Run it against a staging stack with test-mode keys as part of the release
checklist.

### Paid steps under `--no-llm`

`--no-llm` skips the live counselling turn and the live crisis message. The
layer-1 classifier assertion still runs, because it is deterministic and
key-free. Use `--no-llm` for a quick pre-merge check; run the full suite before
a release.

### Not covered here at all

These need a device, a second device, or a keyed environment, and stay in
`VALIDATION.md`'s live checklist:

- Video (LiveKit, two devices).
- Push notification delivery (needs `FIREBASE_SERVICE_ACCOUNT_JSON` and a real
  device token).
- Email delivery end to end — the suite asserts the invite endpoint *returns*,
  not that mail arrives.
- Mobile app flows. Nothing here drives Flutter.
- Keyed safety recall (layers 2 and 3) — that is `make safety-eval` in a keyed
  environment.

## Current result

Run 2026-08-03 against the local stack: **35/39 passed in 18.0s**, 1 manual
step. The four failures are all real defects, all documented in
`docs/qa/production-readiness.md`:

| Failing assertion | Defect |
|---|---|
| django exposes a health endpoint | P1-2 — no `/health` route in `config/urls.py` |
| A can invite B | P0-2 — timed out at the 12s cap |
| invite returns promptly | P0-2 — `relationships/views.py:66` sends mail inline, no `EMAIL_TIMEOUT` |
| crisis resources are configured | P1-5 — `CRISIS_RESOURCES` unset |

The suite is not "expected to fail" on these. They are the gate. It goes green
when they are fixed, and it should be green before any release after that.

## Wiring it in

Not added to `make validate` yet, and deliberately: `validate` is the key-free
CI gate, and this needs a running stack and (without `--no-llm`) a real API key.
The right home is a `make smoke` target run against staging as part of the
release checklist, and a post-deploy run against production.

Adding a permanently-failing suite to `validate` teaches people to ignore
`validate` — the same argument the Makefile already makes about `scenarios`, and
it applies here for the same reason.

## Housekeeping

The suite creates real accounts (`smoke_<tag>_a@example.com`) on every run and
does not clean up after itself. Against a local or staging stack that is fine
and the isolation is worth more than the tidiness. Do not point it at
production without deciding what you want that to mean.
