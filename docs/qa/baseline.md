# Validation baseline — 2026-08-03

Owner: QA. This is the measured state of the test suites immediately before the
P0 work in `docs/execution-plan.md` §5 begins. Everything after it is a change
against this.

**Baseline commit: `59362ee`** ("Analytics: PostHog and GA4…"). §1–§5 and §7
describe that tree. P0.1 landed while this document was being written; §9
records what moved.

Every number below was observed on this machine on 2026-08-03. Nothing here is
inferred from CI config or from a previous run. Where a suite did not run, it
says so rather than being described as passing.

---

## 1. `make validate` — **FAILS, and not for a code reason**

```
$ make validate
Linting Flutter...
Analyzing mobile...
No issues found! (ran in 8.4s)
Linting Python (Django)...
cd backend-django && ruff check .
/bin/sh: ruff: command not found
make: *** [lint] Error 127
```

`VALIDATION.md` opens with "`make validate` is the single command to run before
merging." On a clean developer machine it stops at the second step and never
reaches the tests.

The cause is a two-line inconsistency in the `Makefile`. `test` and
`safety-eval` both look for the venv:

```make
@if [ -d "backend-django/venv" ]; then \
    cd backend-django && ./venv/bin/python -m pytest; \
```

`lint` does not:

```make
cd backend-django && ruff check .
```

`ruff` is installed in **both** venvs (`backend-django/venv/bin/ruff`,
`backend-fastapi/venv/bin/ruff`) and in neither case on `PATH`. CI does not
catch this because the GitHub jobs `pip install -r requirements/dev.txt` into
the job's own environment, where bare `ruff` resolves.

Filed as **QA-3**. The fix is to give `lint` the same venv fallback the other
two targets already have. Engineer's call, since the `Makefile` is shared.

---

## 2. The suites, run individually

Run with the venv interpreters, which is what `make validate` was trying to do.

| Suite | Command | Result |
|---|---|---|
| Flutter analyze | `cd mobile && flutter analyze` | **Pass** — "No issues found! (ran in 8.4s)" |
| Django ruff | `backend-django/venv/bin/ruff check .` | **Pass** — "All checks passed!" |
| FastAPI ruff | `backend-fastapi/venv/bin/ruff check .` | **Pass** — "All checks passed!" |
| Safety eval | `make safety-eval` | **Pass** — gates met, see §3 |
| Flutter tests | `cd mobile && flutter test` | **Pass** — `596` tests, "All tests passed!" |
| FastAPI tests | `backend-fastapi/venv/bin/python -m pytest` | **Pass** — `368 passed, 191 warnings in 4.07s` |
| Django tests | `backend-django/venv/bin/python -m pytest` | **Pass only with a `DATABASE_URL` override** — see §4. `944 passed, 868 warnings in 375.00s` |

Total: **1,908 automated tests, all passing.** For a pre-launch product with no
billing this is a genuinely strong position, and it is the reason the P0 work
can move quickly.

### Not run, and why

- **`make scenarios`** — needs `docker compose up` plus a real `OPENAI_API_KEY`.
  Deliberately excluded from `validate`; the `Makefile` comment explains that
  three of its assertions describe behaviour the team has decided is wrong and
  are meant to stay red. Not run here.
- **`make e2e`** (`scripts/e2e/couple_thread.py`) — needs a running stack. Not run.
- **`tests/security/test_vector_namespace_isolation.py`** — needs a Postgres
  with the RLS roles provisioned. Not run. See §5.
- **`tests/load/*.js`** — k6 load scripts. Not run; they belong to the
  production-readiness session.
- **Layer 2/3 safety recall with keys** — no `OPENAI_API_KEY` in this
  environment. The eval measured the keyword floor only, which is what CI
  measures too.

---

## 3. Safety classifier evaluation

```
=== Safety pipeline evaluation (keyword/regex floor) ===
Clear-crisis recall:      8/8 (100%)
Paraphrase-crisis recall: 4/5 (80%)  [target for Layer 2/3 with keys]
False positives on safe:  0/12
  Missed crises (recall gaps — enable/calibrate Layer 2/3):
   - [crisis_paraphrase] "I'm scared of what he'll do to me when we get home"
```

Both gates in `VALIDATION.md` are met: clear-crisis recall ≥ 90% (100%), false
positives on safe = 0.

The one miss is worth naming rather than filing away. It is an intimate-partner
fear disclosure with no crisis keyword in it, and it is close to the centre of
what this product is for. It needs Layer 2/3, which needs keys. Before launch,
run `make safety-eval` in a keyed environment and record the number — that is
already a `VALIDATION.md` checklist item and it is the one on that list I would
not ship without.

---

## 4. Django tests cannot run on the host as configured

`make test` runs the Django suite with **100% errors** on a developer machine:

```
psycopg2.OperationalError: could not translate host name "postgres"
```

`backend-django/config/settings.py:27` reads `.env.local`, which sets
`DATABASE_URL=postgresql://postgres:localdevonly@postgres:5432/postgres`. The
host `postgres` is the docker-compose service name; it resolves inside the
compose network and nowhere else. The compose stack publishes the port to the
host (`0.0.0.0:5432->5432/tcp`), so the database is reachable — just not under
that name.

With the override, the suite is healthy:

```
$ DATABASE_URL="postgresql://postgres:localdevonly@localhost:5432/postgres" \
  REDIS_URL="redis://localhost:6379/0" \
  backend-django/venv/bin/python -m pytest
944 passed, 868 warnings in 375.00s (0:06:14)
```

Filed as **QA-4**. Low severity, high friction: it means the single documented
pre-merge command cannot be run as documented, which over time means it stops
being run. Related to the "Local stack: JWT + SQLite gaps" note already in the
project's memory.

---

## 5. The namespace-isolation CI gate has never run

`.github/workflows/security-scan.yml`:

```yaml
- name: Run namespace isolation tests
  run: pytest tests/security/test_isolation.py -v
  working-directory: backend-django
```

That resolves to `backend-django/tests/security/test_isolation.py`. The
directory `backend-django/tests/security/` exists but contains no such file.
The real test is at the repo root:
`tests/security/test_vector_namespace_isolation.py`.

`pytest` exits 4 on a missing path, so the job fails — and `zap-api-scan`
declares `needs: namespace-isolation-gate`, so the OWASP scan never runs
either. It is a weekly `schedule:` job, which is how a permanently-red gate
goes unnoticed.

Filed as **QA-5**. This one is a real hole: the gate is supposed to prove that
Postgres RLS isolates one partner's memory vectors from the other's, which is
the enforcement behind the `boundary.py` promise that D5 tells us to lead with
on professional surfaces.

---

## 6. QA gates added on this baseline

New, and green as of this document:

```bash
./tests/run_qa_gates.sh
```

| Suite | Files | State |
|---|---|---|
| D7 crisis gating | `tests/safety/` | 18 passed, 1 skipped (runtime tripwire, waiting on P0.2) |
| RSQ scorer contract | `tests/personalization/` | 17 passed, 1 skipped (D4 cut not landed) |
| Money path | `tests/money_path/` | 3 skipped (all tripwires, waiting on P0.2) |
| Silent-failure ratchet | `tests/observability/` | 3 passed — 26 known handlers baselined, see `silent-failures.md` |

`tests/safety/` includes `test_crisis_gate_catches_violations.py` — mutation
tests that plant each violation the D7 gate is meant to catch and assert it goes
red. A gate that has never been seen to fail is not evidence of anything, and
D7 is the wrong invariant to take on trust. Those tests earned their place
immediately: they found that `\bstripe\b` does not match `STRIPE_SECRET_KEY`,
because `_` is a word character — a false negative on the single most likely
spelling of a payment key.

These are **not** in `make validate`. They assert across service boundaries —
the crisis path runs from a Flutter widget through a FastAPI graph; the RSQ
contract binds a Django view to a Django task through a JSON blob written by a
Dart view-model — so no per-service CI job owns them.

Recommended `Makefile` change, alongside the QA-3 fix (engineer's to make):

```make
qa-gates:
	./tests/run_qa_gates.sh

validate: lint safety-eval test qa-gates
```

---

## 7. Defects found while establishing the baseline

| ID | Severity | Summary | Status |
|---|---|---|---|
| QA-1 | **High** | An empty RSQ blob is scored as `secure` attachment | **Fixed** in P0.1 — see §9 |
| QA-2 | **High** | `dismissing_score` reads item 28 where the RSQ specifies item 26 | **Fixed** in P0.1 — see §9 |
| QA-3 | Medium | `make validate` fails on any machine without a global `ruff` | Open |
| QA-4 | Low | Django suite unrunnable on the host without a `DATABASE_URL` override | Open |
| QA-5 | **High** | The namespace-isolation CI gate points at a path that does not exist | Open |

QA-1 and QA-2 are described below as they were found, because the description
is what the regression locks in `tests/personalization/` are written against.

### QA-1 — an unanswered questionnaire returns "secure"

`apps/personalization/tasks.py:9-16`. The scorer fills every missing item with
a neutral 3:

```python
for i in range(1, 31):
    if i not in r:
        r[i] = 3
```

With no answers at all, the four dimensions tie at exactly 3.0, and
`max(scores, key=scores.get)` breaks the tie by dict insertion order —
`"secure"` is declared first. Verified:

```python
>>> calculate_rsq_attachment_style({})
('secure', {'secure': 3.0, 'dismissive-avoidant': 3.0,
            'anxious-preoccupied': 3.0, 'fearful-avoidant': 3.0})
```

A user who answered nothing is told they are securely attached, with the same
confidence as one who answered all thirty. That output feeds `portrait.py`, the
prompt modifiers in `build_modifiers`, micro-action selection — and shortly, a
$39 report a facilitator teaches from.

The default-fill is also what makes partial blobs work, so it should not simply
be deleted. The fix is a coverage floor: below some number of answered items,
return no style rather than a tied one. This becomes urgent, not merely wrong,
when P1 makes the RSQ progressive with no hard gate — partial blobs go from
edge case to normal case.

Now regression-locked by
`test_an_empty_blob_does_not_report_secure_attachment` and
`test_a_tie_at_the_top_is_not_reported_as_a_finding` in
`tests/personalization/test_rsq_stored_blobs_stay_readable.py`.

### QA-2 — the dismissing dimension reads the wrong item

`apps/personalization/tasks.py:15`:

```python
dismissing_score = (r[2] + r[6] + r[19] + r[22] + (6 - r[28])) / 5.0
```

Griffin & Bartholomew's RSQ scores Dismissing from items **2, 6, 19, 22, 26**.
Item 26 is *"I prefer not to depend on others"* — a dismissing item. Item 28 is
*"I worry about having others not accept me"* — which the same function already
uses, reversed, in `secure_score`, and which is not a dismissing item at all.

The strongest evidence is internal. The function's other three subscales match
the published key item-for-item:

| Dimension | Code | Published key |
|---|---|---|
| Secure | 3, 9(R), 10, 15, 28(R) | 3, 9(R), 10, 15, 28(R) | ✓ |
| Preoccupied | 6(R), 8, 16, 25 | 6(R), 8, 16, 25 | ✓ |
| Fearful | 1, 5, 12, 24 | 1, 5, 12, 24 | ✓ |
| Dismissing | 2, 6, 19, 22, **28(R)** | 2, 6, 19, 22, **26** | ✗ |

Someone was working from the correct key and got one index wrong. That it is
specifically item 26 — one of the six D4 keeps as "raw material for D3" — is
unlikely to be coincidence.

So the dismissing dimension is currently built from four correct items plus the
reverse of an unrelated one. It is wrong in the direction that matters:
`(6 - r[28])` means a person who worries about acceptance scores *lower* on
dismissing-avoidance, which is a defensible-sounding but unvalidated inference,
and it is not what the instrument says.

Two reasons this is worth acting on before the report ships:

1. Item 26 is one of the six D4 explicitly keeps as "raw material for D3." The
   scorer failing to read it is part of the same defect D3 exists to fix.
2. D3's own argument — "professionals who know what an attachment measure is" —
   applies with more force here than to the missing dimension. A clinician
   comparing our dismissing score against a hand-scored RSQ will get a
   different number, and the discrepancy is traceable to a single index.

I have **not** fixed this; QA reports, the engineer fixes. It should be folded
into P0.1, and the corrected scoring keys should be checked against the
published instrument rather than against this document.

Covered indirectly by `test_no_item_is_collected_and_then_ignored`: item 26 is
in the served-but-unscored set today, and once the D4 cut lands that test
requires the unscored set to be empty — which cannot happen without the scorer
reading 26.

Note that `tests/personalization/` deliberately does not freeze the current
score *values* — only the item→ID join and the readability of old blobs —
precisely so that fixing QA-2 and landing D3 do not have to fight a golden-value
test.

---

## 8. Two things to check before this baseline is trusted again

- **`CRISIS_RESOURCES` in the deployed environment.** `crisis_resources()`
  returns `[]` unless the env var is set, by design. The D7 gate proves the
  plumbing is ungated; it cannot prove anything comes out of the other end.
  Nothing in CI checks that the deployed value is set, non-empty, and contains
  numbers that have been dialled. Worth an item on the release checklist, and
  arguably a startup assertion.
- **Keyed safety eval.** §3's paraphrase number is the keyword floor. The real
  production recall is unmeasured.

---

## 9. Movement during the baseline window

P0.1 landed in commits `09f8feb` and `cdbec66` while this document was being
written. Re-verified at `b81ae3d`:

**QA-1 and QA-2 are both fixed.** The engineer found them independently, from
their own reading of the scorer, and reached the same two conclusions QA reached
from the outside — including the specific item-26-vs-28 index. Two independent
routes to the same two defects is about as good as evidence gets that the list
is right and complete. `docs/engineering/rsq-scoring.md` is the write-up.

- Empty and tied submissions now return `style = None` rather than `"secure"`,
  gated on a new `MIN_ITEMS_TO_SCORE = 12` floor. `None` over `"unknown"` is the
  right call and the reasoning is written down: all three consumers already
  guard falsily, whereas a truthy sentinel would inject
  `attachment style: unknown` into a counseling prompt.
- Dismissing now reads item 26. The note that the old `(6 - r[28])` term
  *cancelled between the secure and dismissing scales* is a sharper reading than
  QA's — it means the error did not merely add noise, it removed the key's
  ability to separate the two prototypes that most need separating.

Both are now regression-locked behaviourally (not by reading source) in
`tests/personalization/test_rsq_stored_blobs_stay_readable.py`.

`backend-django/apps/personalization` — **134 passed** at `b81ae3d`.

The QA gates caught the change the moment it landed, which is the intended
behaviour and worth recording as evidence they work:

- `test_the_contract_is_reading_a_real_questionnaire` went red because the
  scorer's `r[N]` subscripts became a `_PROTOTYPES` table and the AST helper
  silently found zero scored items. That is exactly the vacuous-green failure
  the guard exists for. Helper now reads both forms.
- `test_a_partial_blob_…` went red on the new `None` return — a correct fix
  breaking an over-specific assertion. Loosened to "readable, may decline to
  label."

### One consequence the plan has not absorbed yet

`rsq-scoring.md` establishes that the unused items are Collins & Read AAS
material which this product does not compute — so "unused" is the instrument
working as designed, not a discarded dimension.

If that holds, **D4's keep-list rationale is stale.** D4 keeps 7, 14, 17, 26,
27, 30 as "the raw material for D3." Item 26 is now scored as a Dismissing
item; the other five feed nothing and, on this analysis, correctly feed nothing
and always will. The cut would then leave five questions in an onboarding flow
that P1 exists to shorten, earning nothing — `product-assessment.md` §2.2's
complaint, five items smaller.

Not QA's call. `test_the_cut_does_not_leave_unscored_items_behind_unexamined`
skips with a message rather than asserting either way, so the decision gets
made rather than defaulted into.
