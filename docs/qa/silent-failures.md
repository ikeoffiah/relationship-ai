# Silent failures — the general defect behind the history bug

Owner: QA. Written 2026-08-03 at the PM's request, after the product session
found `persist_turn()` swallowing everything with a bare handler.

The comment on that handler is right and should stay:

```python
except Exception:
    # History is a convenience; never let it interrupt counseling.
    return
```

Failing **open** on the send path is correct. Failing **silently** is the
defect. This document is about the second half.

Scanner: `tests/observability/silent_failure_scan.py`.
Ratchet: `tests/observability/test_no_new_silent_failures.py` — the inventory
may shrink, it may not grow.

---

## 1. What the sweep found

Both backends, excluding tests and migrations, parsed with `ast`. A handler
counts as silent if it neither logs, nor emits a metric, nor re-raises.

| | Count |
|---|---|
| Silent handlers, all types | **71** |
| Of those, broad (`except Exception` / bare) | **26** |
| Of those, guarding a block that writes | **19** |

The 45 narrow ones are mostly `DoesNotExist` used as control flow and are
fine. The 26 broad ones are the population worth arguing about, and they are
now baselined in the ratchet test.

`persist_turn` is not the worst of them. It is roughly the fifth worst.

### First, the good news on the empty stores

The PM asked whether the empty tables are empty because of this defect. Checked
against the live dev database — **exact counts, not `n_live_tup` estimates,
which are stale in this database** (`django_migrations` reports 0 by estimate
and 100 by count):

| Store | Rows | Why |
|---|---|---|
| `memory_vectors` | **0** | **Unwired, not swallowed.** `sessions/tasks.py:memory_update_job` is a stub: it logs and returns `True`. The comment says "Vector DB upserts would happen here." Nothing calls `VectorStore.upsert` outside the API router. |
| `safety_incidents` | **0** | **Correct.** Only written by `chat/moderation.py::_record_incident`, on blocked media. No blocked media in this database. That function is also the **best-written handler in the codebase** — see §5. |
| `consent_change_log` | **0** | **Probably correct**, with a caveat. `UserConsent.save()` writes it on any dimension change; 1,413 consents exist with no recorded changes, consistent with seeded creates and no updates. Caveat in §3. |
| `langgraph_sessions` | 25 | Writing. Whatever broke history is not total in this environment. |
| `audit_events` | 45 | Writing. |

So: one stub, one correct, one plausible. **No store is empty because of a
swallowed exception.** That is a better answer than expected, and it means the
sweep's value is prospective — what these handlers will hide once there is
traffic — rather than a diagnosis of current emptiness.

---

## 2. Ranked findings

Ranked, as asked, by **how long a total failure could run unnoticed** × **what
breaks while it does**.

### S1 — The entire counselling stack degrades silently, on one root cause

**Time to notice: unbounded. Nothing anywhere would report it.**

Three handlers, three files, one shared dependency:

| Location | On failure, returns |
|---|---|
| `safety/layer2_semantic.py::screen_layer2` | `_keyword_screen(message)` |
| `safety/layer3_contextual.py::screen_layer3` | `_keyword_screen(message)` |
| `orchestration/llm_provider.py::generate_reply` | `FALLBACK_REPLY` |

All three catch `Exception` and all three are reached by the same causes: a
wrong or expired `OPENAI_API_KEY`, a renamed model, a rate limit, an SDK
upgrade, a network partition.

The combined failure state is a product that is **fully operational-looking and
substantially not the product**:

- The three-layer safety classifier silently becomes one layer of keyword
  matching. `VALIDATION.md` is explicit that paraphrase recall — the thing that
  catches *"I'm scared of what he'll do to me when we get home"*, the one miss
  in the current eval — exists only in Layers 2 and 3.
- Every counselling reply becomes `FALLBACK_REPLY`:

  > "I'm here with you. I'm having trouble putting a full response together
  > right now — can you tell me a little more about what's on your mind?"

  That is *conversationally coherent*. A user answers it and gets it again. It
  does not look like an outage; it looks like a slightly vague therapist.

**The observability problem is worse than the missing log line.** `make
safety-eval` produces byte-identical output whether Layers 2/3 are working or
dead, because CI runs it without keys and the report says "keyword/regex floor"
in both cases. There is no measurement anywhere in the system that distinguishes
healthy from degraded. Adding a log line to each handler does not fix that; §5.2
does.

This is the one I would fix first, ahead of anything else in this document, and
it is a safety finding rather than an observability one.

### S2 — `verify_session_and_user` fails **open** on the joint-session socket

`backend-fastapi/app/api/websockets.py:69`

```python
except Exception as e:
    logger.warning("db_session_verification_failed_fallback_to_true", error=str(e))
    return True
```

This is not strictly silent — it logs — but the sweep found it and it is the
most serious thing in the file, so it is reported here.

It is the authorization check gating `/ws/joint/{session_id}` (call site line
159). It verifies that the connecting user is one of the two partners on the
session's relationship. On any exception — including a transient database
error — it returns `True`, and the connection is allowed.

The correct pattern is **four hundred lines below it in the same file**:

```python
# couple_membership(), line ~415
except Exception as e:
    logger.warning("couple_membership_check_failed", error=str(e))
    return False, None
```

Same concern, same file, same author's instinct about logging — opposite
direction on the fail-safe. `couple_membership` fails closed. Applying its
shape to `verify_session_and_user` is a one-word change.

An authorization check may fail open only as a deliberate, written-down
decision. This one reads as an accident, and it sits on the joint-session path,
which is the one place in the product where two people's private material meets.

### S3 — `get_partner_id` invents a partner on failure

`backend-fastapi/app/api/websockets.py:105`

```python
except Exception:
    return "mock-partner-id"
```

A test double leaked into the production error path. The caller (line 265) feeds
the result straight into:

```python
await broker.turn_hold_manager.activate_window(session_id, partner_id)
await broker.send_to_user(session_id, partner_id, {"type": "turn_held", ...})
```

So on any database hiccup the reflection window is armed against a phantom
identity and the `turn_held` event is addressed to a socket key that cannot
exist. The real partner's turn-hold pacing silently does not happen.

No data leaks — nothing reads the phantom id back out — but the turn-hold is a
deliberate de-escalation mechanic in joint sessions, and it fails off.

Returning a fabricated identifier is worse than returning `None`: the caller
already guards with `if partner_id:`, so `None` would degrade correctly.

### S4 — The audit hash chain can silently restart at "genesis"

`backend-django/apps/audit/logger.py:158`

```python
except Exception:
    # If DB query fails during hash lookup, default to genesis to allow append
    # Error will be caught in _write_event
    return "genesis"
```

**The comment is wrong.** If `_get_last_hash` swallows a transient error and
returns `"genesis"`, the subsequent `INSERT` in `_write_event` typically
*succeeds* — so `_write_event` catches nothing and writes a structurally valid
event whose `prev_hash` is `"genesis"` in the middle of an existing chain.

Mitigating, and worth stating: **the weekly verifier does catch this.**
`verify_audit_chain` checks `event.prev_hash != prev_hash` and exits 1, and
`audit/tasks.py` re-raises. So this is detection-*delayed* (up to a week), not
undetectable — which is why it is S4 and not S1.

What it costs is attribution. The verifier reports "chain sequence mismatch,"
which is indistinguishable from tampering. Nothing recorded that the hash lookup
degraded, so the on-call answer to "were we attacked or did Postgres blink?" is
unavailable. For a tamper-evidence mechanism, an untraceable false positive is
expensive — it is the alarm that teaches people to ignore the alarm.

Contrast with the main `log()` method directly above it, which is exemplary: it
logs, writes a local fallback file for manual recovery, and escalates to
`critical` if even that fails.

### S5 — Personalization silently becomes generic

`chat_router.py` — `fetch_personalization` → `{}`, `fetch_shared_context` →
`{}`, `fetch_memories` → `[]`, all on `except Exception`.

**Time to notice: never, by inspection.** A counselling reply built with no
attachment modifiers and no shared context is a *perfectly good generic reply*.
There is no error, no blank space, no missing element. It is simply not the
product `product-assessment.md` §1.1 describes — the one whose central claim is
that it knows this relationship.

Individually each is a reasonable "best-effort" degradation. Together they mean
the personalization layer can be entirely inert and every reply still reads
fine. This is the failure mode most likely to be live right now and unnoticed.

### S6 — `persist_turn` (the known one) and its neighbour

`chat_router.py::persist_turn` and `get_optional_pool`. Already understood.
Worth noting they compound: `get_optional_pool` swallows pool-creation failures
and yields `None`, and `persist_turn` returns immediately on `pool is None`. So
a bad `DATABASE_URL` produces *two* silent exits before the write is even
attempted, and history, personalization, shared context and memory all go quiet
together with no single point that noticed.

### S7 — Couple-thread delivery drops messages

`broker.py::_listen_to_redis` (inner `except Exception: pass` around
`ws.send_text`) and `broker.py::send_to_user`.

`send_to_user` is defensible — the direct-send failure falls through to a Redis
publish, so there is a real fallback path. The inner one in `_listen_to_redis`
has none: a failed `send_text` drops that message for that socket, permanently
and unrecorded.

Mitigated by design: `couple_thread_websocket` documents that messages are sent
over HTTP and persisted first, so the socket only carries push. A dropped push
costs liveness, not the message. Worth a counter, not urgent.

### S8 — The rest

`assist.py` (`_count_call`, `model_calls`, `_partner_notes`,
`_caution_is_wanted`), `behaviour.py::tendencies_for`,
`engagement/services.py::_allowed_categories`, `chat/media.py::has_metadata`,
`memory/extractor.py::extract` (skips malformed candidates),
`relationships.py::decrypt_context` (returns `{}` on bad JSON — note it is
named *decrypt* but currently only does `json.loads`, which is its own issue).

All degrade to a defensible default. All should be counted rather than logged —
`_count_call` failing silently is mildly funny, since it is the rate counter.

**Tier C, leave as written:** `accounts/middleware.py::process_request` returns
a 401 (that is a response, not a swallow); the two WebSocket disconnect
handlers; `chat/views.py::toggle_reaction`'s documented `IntegrityError` race;
`chat/views.py::upload_media`'s nested cleanup `pass`, which sits inside a
handler that already called `log.exception`.

---

## 3. The consent caveat

`UserConsent.save()` writes `ConsentChangeLog` correctly, but two paths bypass
it, and neither is a swallowed exception — they are the same *class* of problem,
so they belong in this report:

1. **`except UserConsent.DoesNotExist: super().save()`** (`consent/models.py:168`).
   If that ever fires on an update, the consent is persisted and **no change log
   row is written**. The comment says "should not happen." Unlogged, so if it
   does, nobody learns.
2. **`.update()` bypasses `save()` entirely.** Any
   `UserConsent.objects.filter(...).update(...)` changes a consent dimension
   with no `ConsentChangeLog` row and no audit event, because Django does not
   call `save()` on queryset updates. Nothing currently does this. Nothing
   prevents it either.

`ConsentChangeLog`'s own docstring says "Append-only record of **every** consent
change." Two ways exist to make that false silently. Suggest a database trigger
rather than a code convention, given the model is already documented as having
`REVOKE UPDATE/DELETE` enforced in a migration — the enforcement style is
already there.

---

## 4. Which of these touch consent, safety, or money

The PM asked for this cut specifically, because a silent failure there is a
broken promise rather than a lost convenience.

| Finding | Consent | Safety | Money | Verdict |
|---|:-:|:-:|:-:|---|
| S1 counselling stack | | ● | | **Broken promise.** The safety classifier is the product's most legally-exposed component and it can be running at one layer with no signal. |
| S2 fail-open authorization | ● | ● | | **Broken promise.** Gates the joint session, where two people's private material meets. |
| S3 phantom partner id | | ● | | Turn-hold de-escalation fails off. |
| S4 audit chain | ● | | | Tamper-evidence with an untraceable false-positive mode. |
| S5 personalization | | | | Lost convenience — but it is the convenience we are charging $39 for. |
| S6 persist_turn | | | | Lost convenience. |
| S7 couple delivery | | | | Liveness only; message is persisted first. |
| §3 consent bypasses | ● | | | **Broken promise.** "Every consent change" is currently not enforceable. |

**Nothing on this list touches money**, because there is no money code yet. That
is the actionable part: P0.2 is about to add webhook handlers, and a webhook
handler is exactly the shape that attracts a broad `try/except` — a processor
retrying is normal, so swallowing looks harmless. `docs/qa/money-path.md` §4.3
is the failure this produces, and the ratchet test will now catch it as it is
written rather than after the first stranded payment.

---

## 5. The recommended fix — not forty log lines

"Add a log line" repeated 26 times produces 26 log lines nobody reads and no
way to answer "is this happening?". Three pieces, in priority order.

### 5.1 One helper, two twins

The pattern already exists in this codebase, written correctly, in
`chat/moderation.py::_record_incident`:

```python
except Exception:
    log.exception("moderation_incident_not_recorded media=%s", media.id)
```

Named event, structured context, `.exception` so the traceback survives. What is
missing is that it is one instance of a convention rather than a shared thing
with a counter behind it. Give it a name:

```python
# backend-fastapi/app/observability/degrade.py  (+ a Django twin)

@contextmanager
def degraded(operation: str, *, fallback: str, tier: str = "B", **context):
    """Run a non-critical operation. On failure, record it and continue.

    `fallback` states in the code what the user gets instead, so the reader
    does not have to infer it from the return statement.
    """
```

Call site:

```python
with degraded("persist_turn", fallback="history row not written",
              session_id=session_id):
    await conn.execute(...)
```

Why this is a fix and not a log line:

- **One place to change the policy.** Log level, Sentry routing, sampling and
  metric emission are decided once, not 26 times.
- **It emits a counter**, not just a log: `degradation{operation="persist_turn"}`.
  That is what turns "it failed" into "it is failing 400 times an hour," which
  is the question anyone actually needs answered.
- **The fallback is named in the source.** `fallback="history row not written"`
  survives review in a way that a bare `return` does not.
- **It is enumerable.** `tests/observability/` can assert that broad handlers on
  write paths use it — which is the enforcement, and it is already half-built.

Roughly a half-day for the helper plus its Django twin, then mechanical
adoption per finding.

### 5.2 Tier A needs more than a counter

For S1 this is the actual fix, and it is a design change rather than
instrumentation.

The problem is not that Layer 3 fails quietly. It is that **the degraded state
is indistinguishable from the healthy state at every point where anyone looks.**
A counter helps only if someone is looking at it.

Make the degradation part of the result, not just a side effect:

1. `Layer2Result` / `Layer3Result` carry which layer actually produced the
   answer (`source: "semantic" | "keyword_fallback"`).
2. The pipeline exposes an aggregate — "% of screens in the last hour that
   reached Layer 3" — and a readiness endpoint that reports *degraded* when
   that number is near zero while keys are configured.
3. `make safety-eval` **asserts** which layers ran and prints it. Today its
   output is byte-identical whether Layers 2/3 work or are dead, and it is the
   only safety measurement anyone runs. That is the single highest-value change
   in this document.
4. Same for `FALLBACK_REPLY`: count it. A fallback rate above a few percent is
   an outage, and right now it is unobservable.

None of this changes the fail-open behaviour, which is correct and should stay.

### 5.3 Fail-safe direction is a separate decision from logging

S2 and S3 are not observability defects that a helper fixes. They are
fail-*open* decisions on paths where fail-*closed* is right:

- `verify_session_and_user` → `return False`, matching `couple_membership`.
- `get_partner_id` → `return None`, which the caller already handles.

Recommend a written rule: **authorization and identity resolution fail closed;
convenience and enrichment fail open.** Both directions get recorded. `degraded()`
handles the second; the first should not use it, because a helper named
"degraded" is the wrong shape for "deny the connection."

---

## 6. Suggested order

| # | Work | Why here |
|---|---|---|
| 1 | S2 — `verify_session_and_user` fails closed | One word. Authorization. The correct version is already in the file. |
| 2 | S1.3 — `safety-eval` reports which layers ran | Half a day. Makes the largest invisible failure visible, and it is the measurement we already run. |
| 3 | S3 — `get_partner_id` returns `None` | One line. Deletes a test double from a production path. |
| 4 | Build `degraded()` + Django twin | Half a day. Unblocks everything below, and P0.2's webhooks should be written with it from the start. |
| 5 | S1.1/1.2 — layer + provider degradation counters | Uses the helper. |
| 6 | S4 — record the hash-lookup degradation | Makes the weekly verifier's alarm attributable. |
| 7 | §3 — consent change-log bypasses | Database trigger, not convention. |
| 8 | S5–S8 | Mechanical, once the helper exists. |

Items 1 and 3 are two lines between them and I would take them in the current
sprint regardless of everything else.

**Not recommended: a blanket ban on broad handlers.** Several here are correct,
and a rule that forbids them produces `except Exception: logger.debug(...)`,
which is the same defect with a log line in front of it. The ratchet plus the
helper gets the behaviour without the ritual.
