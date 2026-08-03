# Production readiness assessment

Owner: QA. Written 2026-08-03 against the code and against a running local
stack, not against the docs.

**Read this first: `docs/qa/load.md` holds the measurements behind P0-1 and
P0-2, and `docs/qa/smoke.md` is the suite that must go green before a release.**
Scope here is *can this system survive being live* — availability, data
exposure, secrets, observability. Functional correctness of the money path,
the D7 crisis-gating test and the RSQ scorer belong to the other QA session and
are deliberately not covered.

---

## The read

**No-go.** Not because the product is unfinished — it is pre-launch and that is
expected — but because of four defects that are individually launch-blocking and
two of which are already true of the code as it stands today.

Two of them will take the product down in front of the first cohort:

- **Every counselling turn permanently leaks 10 Postgres connections.**
  Measured, reproducible, linear. Nine turns per FastAPI process and the
  database is gone. Not nine concurrent — nine ever.
- **Partner invites block on an SMTP socket with no timeout.** Measured: 40/40
  invites failed at a 15-second client cap. With `gunicorn --workers 2` this is
  two invites away from taking the whole Django API down, and a cohort sends
  forty.

One of them is a privacy defect that matters more here than it would almost
anywhere else:

- **Sentry receives the user's counselling message text verbatim**, alongside
  their email address and IP. Proven by reconstructing the actual payload, not
  inferred from the config.

And one is an authentication hole that is live right now:

- **The running stack's `SECRET_KEY` is byte-for-byte the `django-insecure-…`
  default hardcoded in `config/settings.py:35`**, which is in the public repo
  and in git history. It is the JWT signing key for both services. Anyone with
  the repo can mint a token for any user id.

Conditions for a go are in [§8](#8-the-go-list).

---

## 1. Method, and what is measured vs. inferred

Everything labelled **[measured]** was produced by running against the local
docker-compose stack on 2026-08-03: Django 8000, two FastAPI replicas 8001/8002,
pgvector pg14 (`max_connections=100`), Redis 7, Celery worker + beat. Tools are
`tests/production/load.py` and `tests/production/smoke.py`, both written for this
assessment and both in the repo.

Everything labelled **[inferred]** is read off the code with no run behind it.
Where an inference is load-bearing it says so.

Two caveats that cut against my own numbers, stated up front:

- The Django container runs `manage.py runserver`, not `gunicorn --workers 2`.
  Every Django throughput number below is therefore **optimistic** — runserver
  is threaded and gunicorn's production config is two synchronous workers.
- Postgres here is local docker at `max_connections=100`. Supabase free tier is
  lower and adds pooler limits, so the connection findings get *worse* in
  production, not better.

---

## 2. P0 — blocks launch

### P0-1. Every counselling turn leaks 10 Postgres connections, permanently

**[measured]** From a freshly recreated FastAPI container, five serial
counselling turns:

| | pg connections |
|---|---|
| baseline | 8 |
| after turn 1 | 18 |
| after turn 2 | 28 |
| after turn 3 | 38 |
| after turn 4 | 48 |
| after turn 5 | 58 |
| **after 60s idle** | **58** |

Exactly +10 per turn, zero recovery.

**Cause.** `backend-fastapi/app/memory/vector_store.py:35-38`:

```python
    async def _get_pool(self) -> asyncpg.Pool:
        if not hasattr(self, "_pool"):
            self._pool = await asyncpg.create_pool(self.db_url, statement_cache_size=0)
        return self._pool
```

The pool is cached on the *instance* and never closed. And
`backend-fastapi/app/api/chat_router.py:243` builds a brand-new instance on every
single turn:

```python
        retriever = SessionMemoryRetriever(db_url=os.environ["DATABASE_URL"])
```

so the cache never hits. `asyncpg.create_pool` defaults to `min_size=10`, and it
opens all ten eagerly. Nothing ever calls `close()`.

**Blast radius.** Nine turns per process exhausts a 100-connection Postgres.
Once exhausted, everything else sharing that database — Django, Celery, beat —
starts failing too. In production that is the whole product, taken down by nine
messages.

**[measured]** The 5-hour-old wreckage of the earlier sweep: 105 connections,
99 idle with a NULL query, 97 of them held by `relationshipai-fastapi-1`, forty
five seconds after all load had stopped. Postgres was refusing new connections
with `FATAL: sorry, too many clients already` and `/health` was still returning
`{"status": "healthy"}`.

The same per-call `create_pool` pattern appears in four more places, all of
which leak on at least one path:

| Location | Note |
|---|---|
| `app/api/relationships.py:15-25` (`get_db_pool`) | closes correctly; its own comment says it should be on `app.state` |
| `app/api/chat_router.py:39-58` (`get_optional_pool`) | closes correctly |
| `app/api/websockets.py:27` (`verify_session_and_user`) | not closed on the exception path, nor on the `if not pool: return True` path |
| `app/api/websockets.py:79` (`get_partner_id`) | not closed on the exception path — and this runs **per message** |
| `app/memory/vector_store.py:37` | never closed at all — this is P0-1 |

**Fix shape.** One pool on `app.state`, created in the lifespan, reused
everywhere; `min_size` sized to the worker count, not left at 10.

### P0-2. The partner invite blocks on SMTP with no timeout

**[measured]** 40 invites at concurrency 20: **40 failed, 0 succeeded**, all at
the client's 15s cap. Single-request probe: no response after 120 seconds.

`backend-django/apps/relationships/views.py:66` calls `send_mail` inline inside
the request, and **`EMAIL_TIMEOUT` is set nowhere in the repo**. Django passes
that straight to `smtplib.SMTP(timeout=None)`, so the socket has no deadline at
all. A slow, filtered or unreachable mail host holds the worker until the
platform kills it.

Production is `gunicorn --workers 2` (synchronous). Two concurrent invites is
the entire Django API. A cohort sends forty within minutes.

Three more request-path `send_mail` calls have the same shape and the same
absence of a timeout: `apps/accounts/views.py:156` (signup verification),
`apps/accounts/views.py:495` (forgot password), `apps/accounts/email_views.py:55`
(resend verification). Only `apps/relationships/tasks/dissolution.py:53` is
already in a task.

**Fix shape.** `EMAIL_TIMEOUT = 5` at minimum, and move all four onto the
`notifications` queue that already exists and is already being consumed.

### P0-3. Sentry receives counselling message content, user email and IP

`backend-django/config/settings.py:41-46`:

```python
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=1.0,
        send_default_pii=True,
    )
```

**[measured]** I reconstructed the finished, scrubbed event this client would
ship for a 500 on a chat POST, with `before_send` intercepting it so nothing
left the process. Actual output:

```json
{
  "user": {"id": "u-123", "email": "partner@example.com",
           "username": "partner@example.com", "ip_address": "203.0.113.7"},
  "request": {
    "method": "POST",
    "headers": {"Authorization": "[Filtered]"},
    "data": {
      "content": "I've been thinking about ending it. I can't tell my wife.",
      "password": "[Filtered]"
    }
  }
}
```

`password` and `Authorization` *are* filtered — the SDK's default denylist
catches those key names. `content` is not, because the denylist is a list of key
names and nobody put `content`, `message`, `answer`, `response_text`,
`transcript` or `journal` on it.

Two things make this specific rather than theoretical:

- **[measured]** `max_request_body_size` defaults to `"medium"` in sentry-sdk
  2.66.1 (verified against the installed source), which attaches request bodies
  up to 10 KB. This is **independent of `send_default_pii`**, so the FastAPI
  client at `backend-fastapi/app/main.py:25-29` has the same body exposure even
  though it correctly leaves PII off.
- `include_local_variables` defaults on. `apps/counseling/tasks.py:212` calls
  `logger.exception` inside memory extraction, which holds *decrypted* memory
  text in a local. With `CeleryIntegration()` and the auto-enabled
  `LoggingIntegration`, that traceback and its frame locals go to Sentry.

There is no `before_send`, no `before_breadcrumb`, no `EventScrubber` override,
and no `max_request_body_size` anywhere in either service. `traces_sample_rate`
is 1.0 on both.

The mobile app compounds it: `mobile/lib/main.dart:77-84` sets only `dsn`,
`tracesSampleRate` and `profilesSampleRate`, leaving `enablePrintBreadcrumbs`
at its default `true` — and `mobile/lib/core/api_services/base_api_service.dart:46`
installs `LogInterceptor(requestBody: true, responseBody: true)`, which prints
every request and response body *including the `Authorization` header set eight
lines later*. `mobile/lib/core/api_services/dio_exceptions.dart:62` calls
`log(response.toString())` unguarded by `kDebugMode`, so full response bodies
reach the device log in **release** builds.

**Fix shape.** Delete `send_default_pii=True`. Add
`max_request_body_size="never"` and `include_local_variables=False` to both
inits. Add a `before_send`. Turn off the Dio body logging and
`enablePrintBreadcrumbs`.

**This is also a legal exposure, not only a technical one.** Counselling
transcripts in a US-hosted third-party error tracker with no DPA named anywhere
in the repo is the kind of thing a facilitator's institution will ask about
before they hand you thirty couples.

### P0-4. `SECRET_KEY` has a public default, and the live stack is using it

`backend-django/config/settings.py:33-36`:

```python
SECRET_KEY = env(
    "SECRET_KEY",
    default="django-insecure-d3140*5i&*(6@@msu4m0bwmhhkq5%#e7oth&3x2iuu2v36@z#%",
)
```

**[measured]** `backend-django/.env.local` currently holds that exact string,
byte for byte. Both services share it (fingerprints match, which is the one
thing that is working). It is also recoverable from git history at
`a3a7581:backend-django/.env.local`.

This is the dangerous shape of a bad default: it *silently works*. A Railway
deploy that forgets the variable boots normally, mints JWTs, serves traffic —
signed with a key that is in a public repo. `apps/accounts/auth.py` signs with
`settings.SECRET_KEY`, so anyone holding it forges a token for any `sub`, with
any `scope`, and `is_minor` set to whatever they like.

FastAPI got the identical question right — `backend-fastapi/app/auth.py:36-45`
fails closed with an explicit comment saying why. The asymmetry is the bug.

Two settings next to it fail the same way and cascade:

- `DEBUG = env("DEBUG", default=True)` (`settings.py:49`). Unset in production →
  Django's technical 500 page, which renders POST data and frame locals, i.e.
  message text, to whoever triggered the error.
- `FORCE_HTTPS = env.bool("FORCE_HTTPS", default=not DEBUG)` (`settings.py:65`)
  feeds `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE`.
  So one unset `DEBUG` also turns off the SSL redirect and both secure-cookie
  flags. `ALLOWED_HOSTS` defaults to `["*"]` on the same theme.

Note `settings.py:26` declares `environ.Env(DEBUG=(bool, False))` — the safe
default is written and then discarded one line later at `:49`.

**Related, and only exploitable because of this one:**
`app/memory/vector_store.py:43` interpolates the user id into SQL with an
f-string:

```python
        await conn.execute(f"SET app.current_user_id = '{user_id}'")
```

`user_id` comes from the JWT `sub`. With a forgeable signing key, that becomes a
reachable injection into the statement that establishes RLS context — i.e. the
control that enforces the partner boundary.

---

## 3. P1 — will hurt inside the first cohort

### P1-1. WebSocket participant verification fails **open**

`backend-fastapi/app/api/websockets.py:69-71`:

```python
    except Exception as e:
        logger.warning("db_session_verification_failed_fallback_to_true", error=str(e))
        return True
```

Any error in the membership check — and under P0-1 the error is
`TooManyConnectionsError`, which is *guaranteed* under load — returns True. Any
holder of a valid token can then join any couple's live joint counselling
session by session id.

The function directly below it, `couple_membership` at `:392-394`, fails closed
and carries a comment explaining exactly why: *"a couple's private thread is not
something to open because a query failed."* The same reasoning applies here and
was not applied.

Worse, this is untested in CI: `.github/workflows/fastapi-ci.yml:66` sets
`WS_SKIP_PARTICIPANT_CHECK: "1"` for the whole run, so the isolation property
most worth testing is switched off in the only place that would catch a
regression.

`get_partner_id` at `:76` also still sniffs `DATABASE_URL` for `"test"`/`"mock"`
and returns a literal `"mock-partner-id"` — the exact pattern the comment at
`:14-16` says was removed as dangerous.

### P1-2. Health checks cannot fail, and migrations do not run on deploy

`backend-fastapi/app/main.py:112-114`:

```python
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

A hardcoded literal. It checks nothing. **[measured]** it returned
`{"status": "healthy"}` while Postgres was refusing every connection and the
service was functionally dead. It also returned healthy while a FastAPI replica
was crash-looping on `ModuleNotFoundError: No module named 'app'` — the process
restarts, the container stays `Up`, and nothing notices.

**Django has no health endpoint at all.** `config/urls.py` has no `/health`
route, so Railway has nothing to probe and a load balancer has nothing to
withdraw.

**Migrations do not run on deploy.** Neither Procfile declares a `release:`
process, and there is no `railway.json`/`railway.toml`/`nixpacks.toml` in the
repo. The only `migrate` in the tree is `Makefile:72`, which shells into the
local compose container. The first deploy that ships a model change serves
against a stale schema.

And `backend-django/Procfile:1` contains a literal backslash:

```
web: gunicorn config.wsgi:application --bind 0.0.0.0:\$PORT --workers 2
```

Verified at the byte level. Through a shell, `\$` escapes the dollar, so
gunicorn is handed the literal string `$PORT` and cannot bind. Present since the
initial commit — whatever has been serving, it is not this line as written.

### P1-3. LLM failures are invisible

`backend-fastapi/app/orchestration/llm_provider.py:62-71`:

```python
    try:
        if provider == "openai":
            return await _openai(system_prompt, messages, fast=fast) or FALLBACK_REPLY
        ...
    except Exception:
        return FALLBACK_REPLY
```

Degrading to a warm holding reply rather than an empty string is right, and the
comment defends it well. What is wrong is that the failure is **swallowed with
no log line and no `sentry_sdk.capture_exception`**. A wrong key, an expired
card, a rate limit, a regional outage — all produce the same gentle "I'm having
trouble putting a full response together" to every user, with nothing in Sentry
and nothing in the logs. You would learn about it from a facilitator.

Two further gaps on the same call:

- **No timeout.** The OpenAI Python SDK defaults to a 600-second request timeout
  with 2 retries. A hung provider holds the SSE connection for ten minutes.
  Django's own assist path gets this right — `apps/chat/assist.py:56-67` sets
  2.5s/6.0s budgets with reasoning for each, and `:109` sets `max_retries=0`.
  FastAPI sets nothing.
- **The declared fallback model is decorative.**
  `model_config.py:29` declares `'fallback': 'gpt-4.1-mini'` and nothing in the
  codebase ever reads the key. `grep -rn fallback backend-fastapi/app` returns
  only comments and unrelated hits. There is no model failover.

`tests/production/smoke.py` asserts on this: a turn that comes back as
`FALLBACK_REPLY` fails the suite, because right now that is the only way anyone
would find out.

### P1-4. The counselling endpoint has no rate limit at all

Django has DRF throttling (`settings.py:330-338`). **FastAPI has none** — no
`slowapi`, no limiter, no middleware. `POST /api/v1/sessions/{id}/messages`
spends a real gpt-4o completion per call and is reachable by anyone with a valid
token, unbounded.

At $0.00135 a turn (measured, see `docs/qa/load.md`) the direct cost of abuse is
small. The availability cost is not: under P0-1, ten requests take the database
down. A single looping client is a full outage.

Two lesser notes on the Django side: `DEFAULT_THROTTLE_RATES` are all
**per-day** (`anon: 100/day`, `user: 1000/day`) with no per-minute burst
ceiling, so a runaway client gets 1000 free requests before anything stops it
and then gets a hard 24-hour lockout with no client-side handling for the 429.
And `AuthAttemptThrottle`'s docstring says "Max 5 per 15 minutes" while the
configured `auth_attempt` rate is `20/hour`.

**[measured]** `AnonRateThrottle` does *not* apply to signup —
`RegisterView.throttle_classes = [AuthAttemptThrottle]` replaces the defaults —
so 80 people signing up from one venue IP is fine. I checked because I expected
the opposite: 0 × 429 across 320 requests.

### P1-5. `CRISIS_RESOURCES` is unset, so a crisis surfaces an empty list

`backend-fastapi/app/api/chat_router.py:105-122` returns `[]` unless the
`CRISIS_RESOURCES` env var holds a JSON array. The refusal to invent a hotline
number is exactly right. The consequence is that a person in crisis currently
gets a `safety_triggered` event carrying no resources at all.

**[measured]** It is not set in either `.env.local`. The smoke suite fails on it
today. This is a deploy-config item, not a code fix — but it is one env var
between a working crisis surface and a blank one, so it belongs on the go list.
The gating question (D7 — that nothing on this path is ever paywalled) is the
other QA session's, in `docs/qa/crisis-gating.md`.

---

## 4. P2 — fix before the cohort after the first

- **The FastAPI counsellor is stateless within a session.**
  `chat_router._initial_state` (`:264-289`) puts exactly one message into
  `short_term_buffer`, and `persist_turn` (`:61-92`) stores only a 200-character
  preview. The model never sees the conversation so far. **[measured]** this is
  why input is 317 tokens a turn rather than the ~3k `go-to-market.md` §3.1
  assumed. It is a product defect with a cost consequence — see
  `docs/qa/load.md` §4 for what the margin looks like once history is threaded.
- **`build_counseling_graph()` is called per request** — `chat_router.py:304`
  and twice in `websockets.py` (`:205`, `:295`). LangGraph compilation on every
  turn.
- **WebSocket "streaming" is synthetic and doubled.** `websockets.py:299-315`
  waits for the full reply, then emits it word by word with
  `await asyncio.sleep(0.05)` per word, broadcasting each word twice
  (`ai_token` *and* `agent_stream`). A 200-word reply is 10 seconds of
  artificial delay and 400 socket sends.
- **Test scaffolding in the production hot path.** `websockets.py:228-229`
  imports `unittest.mock` and branches on `isinstance(broker, Mock)` on every
  message.
- **`relationship_id=session_id`** at `websockets.py:192` and `:282` — the
  session id is passed as the relationship id into the counselling graph, which
  is also what `SUSPENDED_JOINT_SESSIONS.add(state.relationship_id)` keys on.
- **`SUSPENDED_JOINT_SESSIONS` is an in-process Python set**
  (`app/safety/sensitive_disclosures.py`). With two FastAPI replicas behind one
  port, a session suspended on replica 1 is not suspended on replica 2, and a
  restart clears it entirely.
- **`encrypt_context`/`decrypt_context` in `app/api/relationships.py:29-38` are
  no-ops** that `json.dumps`/`json.loads`. The names claim encryption that does
  not happen. The data is shared-by-design, so the exposure is limited — the
  lying function name is the problem.
- **`ENCRYPTION_MASTER_SECRET` rotation destroys every ciphertext.** No key
  version, no key id in the envelope (`nonce || ct`), no dual-key read path.
  `docs/security/incident-response.md:10` tells a responder to rotate
  `MASTER_ENCRYPTION_SECRET` — a variable that does not exist; the real name is
  `ENCRYPTION_MASTER_SECRET`. Under pressure, someone will set the wrong one,
  and if they set the right one they will destroy all message history.
- **No `CONN_MAX_AGE`, no `connect_timeout`** on the Django database. A new
  connection per request, and a hung connect blocks a worker with no deadline.
- **Redis is doing four jobs on one instance** — cache, sessions
  (`SESSION_ENGINE = cache`), Celery broker and DRF throttle store, all on db 0.
  On Upstash free tier under an eviction policy, evicting a cache key and
  evicting a queued Celery message are the same operation. Also `cache.clear()`
  via django-redis issues `FLUSHDB`, which would take the Celery queue with it.
- **No CORS and no `CSRF_TRUSTED_ORIGINS` anywhere.** Fine for a Flutter client
  sending `Authorization: Bearer`. The web checkout in P0.2 is a web client, and
  it will hit this on day one.
- **`requirements/prod.txt` is 0 bytes in both backends** and referenced by
  nothing. A trap for whoever reads the filename.
- **Dockerfiles run as root**, pin Python 3.12 while CI runs 3.14, and the
  FastAPI image's default `CMD` includes `--reload`.
- **The pre-commit trufflehog hook excludes `.env` files**
  (`.pre-commit-config.yaml:5-7`) directly under a comment that says *"Catch
  .env files anywhere in the tree."* A `.env.local` did reach a commit once
  already; this is the control that was supposed to stop a recurrence.
- **`backend-django/db.sqlite3` is tracked in git** (212 KB). The `.gitignore`
  entry cannot untrack an already-committed file. Check what rows are in it.
- **`scripts/check_jwt_alignment.py` is compose-only** and in no CI workflow or
  deploy step. It is the best-designed diagnostic in the repo and it does not
  run in the environment where the failure it catches actually happens.

---

## 5. What is genuinely solid

Worth saying, because the list above is long and it is not the whole picture.

- **Celery.** **[measured]** beat has synced all six schedules to the DB, all
  six task names resolve in the worker's registry, and the worker is consuming
  all five declared queues. Task routing is coherent. This is the healthiest
  subsystem in the stack.
- **The JWT fingerprint diagnostic.** `key_fingerprint()` is an HMAC of a fixed
  public label *under* the key rather than a hash *of* it, so it is safe to log,
  and both services log it at startup. The docstring explains the silent failure
  it exists to catch. Genuinely good engineering.
- **`apps/chat/assist.py`.** Per-path timeout budgets with the reasoning
  written down, a process-wide OpenAI client with the measured latency win
  recorded, `max_retries=0` with a justification, and a call counter so the cost
  of a widened gate cannot be silent. This is what `llm_provider.py` should look
  like.
- **Consent defaults are closed.** **[measured]** a fresh account has
  `cross_partner_insight_sharing="never"` and `model_improvement_data=false`.
- **Layer-1 safety.** **[measured]** 0.95 on both clear-crisis probes, 0.00 on
  both known traps.
- **`crisis_resources()` refusing to invent a hotline number** is the right call
  even though it currently produces an empty list.
- **The `.gitignore` env coverage** is visibly hard-won, including the
  `*.env.local*` pattern for backups.
- **`app/auth.py` failing closed on a missing `SECRET_KEY`**, with the comment
  explaining that the old published placeholder would have accepted forged
  tokens.
- **The mobile analytics layer** — sealed event taxonomy, no string-keyed
  `track`, tri-state consent gate. It is the template `AuditEvent.metadata`
  should follow.

---

## 6. Logging and PII, beyond Sentry

A separate sweep of all 114 Python logging sites and every Flutter
`print`/`debugPrint`/`log` call. Full detail is in the audit; the ones that
matter:

| Where | What leaks |
|---|---|
| `backend-fastapi/app/api/websockets.py:339-342` | `logger.warning("invalid_json_received", …, data=data)` — `data` is the raw client frame, i.e. the counselling message. Any malformed frame logs the utterance. |
| `mobile/lib/core/api_services/base_api_service.dart:46` | `LogInterceptor(requestBody: true, responseBody: true)` — every chat send, journal entry and RSQ submission, plus the `Authorization` header set at `:56`. |
| `mobile/lib/core/api_services/dio_exceptions.dart:62` | `log(response.toString())`, unguarded by `kDebugMode` — full response bodies in **release** builds. |
| `backend-django/apps/notifications/push_service.py:63` | `log.error("push_send_failed for %s: %s", notification.title, …)` — push titles carry partner names and message previews, and `log.error` becomes a Sentry event. |
| `backend-django/apps/notifications/email_service.py:37` | logs the recipient address. Separately, `log` here is a **stdlib** logger and the call passes `to=`/`subject=` kwargs — as written this line raises `TypeError` inside the exception handler. Live bug, independent of the privacy issue. |
| `mobile/lib/features/auth/viewmodels/auth_viewmodel.dart:220,250,300,388,429` | email addresses, unguarded. |
| `backend-django/apps/counseling/tasks.py:83,212` | `logger.exception` inside memory extraction — with `include_local_variables` on, the decrypted memory text in frame locals goes to Sentry. |

**Clean by omission, worth keeping that way:** no `django.db.backends` logger and
root at INFO, so SQL parameters are not logged. Adding `"level": "DEBUG"` to the
root logger would start logging every query's bound parameters. No
request/response body middleware server-side. `AuditEvent.metadata` holds only
ids, counts and enums at every first-party call site — though the field is an
untyped `JSONField` and `apps/audit/views.py:40-46` accepts client-supplied
metadata with no schema, which then lands verbatim in the plaintext
`audit_fallback.log` at `apps/audit/logger.py:129-142`.

One to close before it opens: nothing sets `LANGCHAIN_TRACING_V2`, but
`langsmith` is in the FastAPI dependency tree. If that variable is ever set,
every prompt and completion uploads to LangChain's cloud. Pin it to `false` in
compose and in the Railway env.

---

## 7. Rate limiting, throttling and abuse — summary

| Surface | State |
|---|---|
| Django auth endpoints | `AuthAttemptThrottle`, 20/hour per IP+email. Reasonable. |
| Django authenticated API | `UserRateThrottle` 1000/day. No burst ceiling, hard 24h cliff, no client handling of 429. |
| Django anonymous API | `AnonRateThrottle` 100/day per IP. **[measured]** does not apply to signup. |
| **FastAPI, all endpoints** | **None.** Including the one that spends money. |
| WebSocket connections | None. No per-user socket cap. |
| Throttle store | Redis, shared with the Celery broker on db 0. |

---

## 8. The go list

Launch is a go when all of these are true. Numbered so they can be ticked off.

**Blocking — code**

1. One shared asyncpg pool on `app.state`; `vector_store._get_pool` no longer
   creates per-instance pools; every remaining `create_pool` in `websockets.py`
   closed in a `finally`. Verified by re-running
   `python3 tests/production/load.py --phase db` and seeing connections return
   to baseline.
2. `EMAIL_TIMEOUT` set, and all four request-path `send_mail` calls moved to the
   `notifications` queue. Verified by the smoke suite's invite latency
   assertion.
3. `send_default_pii=True` deleted; `max_request_body_size="never"` and
   `include_local_variables=False` on both Sentry inits; a `before_send` that
   drops `request.data`. Mobile: `LogInterceptor` bodies off,
   `enablePrintBreadcrumbs=false`, `dio_exceptions.dart:62` deleted.
4. `SECRET_KEY` default removed from `settings.py` so it fails closed like
   FastAPI does; `DEBUG` default flipped to `False`; `ALLOWED_HOSTS` default
   `["*"]` removed. Then **rotate `SECRET_KEY` in both services** — the current
   one is public — and re-check fingerprint alignment.
5. `verify_session_and_user` fails closed. Remove
   `WS_SKIP_PARTICIPANT_CHECK: "1"` from `fastapi-ci.yml` so a regression is
   caught.
6. A timeout on the counselling LLM call, and `sentry_sdk.capture_exception`
   before returning `FALLBACK_REPLY`.

**Blocking — deploy config**

7. `release:` process in both Procfiles running `manage.py migrate`.
8. Fix the `\$PORT` backslash in `backend-django/Procfile:1`.
9. Real health endpoints — Django gets one, FastAPI's checks Postgres and Redis
   — and a `healthcheckPath` configured on Railway.
10. `CRISIS_RESOURCES` set to a verified, region-appropriate list.
11. `LANGCHAIN_TRACING_V2=false` set explicitly.
12. `scripts/check_jwt_alignment.py` (or a Railway-shaped equivalent) run as a
    post-deploy check.

**Blocking — process**

13. `python3 tests/production/smoke.py` green, with the checkout MANUAL step
    replaced by real assertions once P0.2 lands.
14. A rate limit on the FastAPI counselling endpoint before any facilitator gets
    a code.

**Not blocking, but do it in the first week:** everything in §4, plus
`git rm --cached backend-django/db.sqlite3`, and fixing the trufflehog
`exclude`.

---

## 9. What would change my read

- If P0-1 and P0-2 are fixed and the load phases re-run clean, the remaining
  P0s are configuration changes that take an afternoon, and the answer flips to
  a conditional go.
- If the first cohort is genuinely 25 couples rather than 40, none of the
  capacity numbers change — P0-1 fails at nine turns, and a cohort of any size
  sends more than nine messages.
- If Sentry is turned off entirely for launch rather than fixed, P0-3 stops
  being a blocker and becomes a P1 observability gap, which is a trade I would
  take on day one but not on day thirty.
