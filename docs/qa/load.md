# Load, capacity and LLM cost

Owner: QA. Measured 2026-08-03 against the local docker-compose stack.

```bash
python3 tests/production/load.py --phase onboard   # free
python3 tests/production/load.py --phase db        # free
python3 tests/production/load.py --phase counsel --turns 20   # costs money
python3 tests/production/load.py --phase cost      # 3 paid completions
```

## 0. The one-line answer

**The system supports nine counselling turns per FastAPI process, total, for the
lifetime of that process.** Not nine concurrent. Nine, ever. Then Postgres is
out of connections and everything sharing that database — Django, Celery, beat —
starts failing with it.

A 40-couple cohort would take the product down on the tenth message anybody
sends.

## 1. Method, and why not k6

Neither k6 nor locust is installed on this machine and `ab` cannot drive the
shapes that matter here — an SSE stream, a multi-step onboarding sequence, or a
run that samples `pg_stat_activity` while it works. So `tests/production/load.py`
is a stdlib `ThreadPoolExecutor` driver with a background connection sampler. It
is not a replacement for a real load tool at scale; at the scale that matters
here — 80 people, tens of concurrent requests — it is sufficient and it measures
the one thing an off-the-shelf tool would not.

**Stack under test:** Django `manage.py runserver` on 8000, two FastAPI replicas
(8001/8002), pgvector pg14 with `max_connections=100`, Redis 7, Celery worker +
beat. All local, all in docker.

**Two caveats that cut against these numbers:**

- Django here is `runserver`, which is threaded. Production is
  `gunicorn --workers 2`, synchronous. **Every Django throughput number below is
  optimistic.**
- Postgres here allows 100 connections. Supabase free tier allows fewer and adds
  pooler limits on top. **The connection findings get worse in production, not
  better.**

Everything below is **[measured]** unless it says otherwise.

## 2. The arrival pattern being modelled

Not a smooth ramp. A facilitator sells a cohort, hands out 25–40 codes, and the
whole cohort onboards inside an hour — often inside one session, in one room, on
one wifi. So the interesting question is never requests per second; it is what
happens when eighty people create accounts, submit a 30-item instrument and pair
up within the same few minutes, and then start talking to a counsellor.

Three phases model that: `onboard`, `db`, `counsel`.

## 3. Results

### 3.1 Cohort onboarding — Django holds

40 couples (80 people), concurrency 20. Each person: register → submit RSQ →
read portrait → fetch daily question.

| | |
|---|---|
| requests | 320 |
| succeeded | **320** |
| failed | 0 |
| wall | 8.0s |
| throughput | 40.2 req/s |
| latency | p50 **358ms**, p95 **1091ms**, p99 **2170ms**, max 2219ms |
| pg connections | baseline 22, peak 28 |
| 429s | **0** |

Django absorbs a whole cohort onboarding at once with no errors and acceptable
tail latency. Remember the caveat: this is runserver, not two sync gunicorn
workers.

The zero 429s is worth naming because I expected the opposite. `AnonRateThrottle`
is configured at `100/day` per IP, and eighty people in one room share one IP —
but `RegisterView.throttle_classes = [AuthAttemptThrottle]` **replaces** the
defaults, so the anon bucket never applies to signup. The cohort-in-one-room
scenario is safe. `AuthAttemptThrottle` keys on IP *and* email, so it does not
collide across people either.

### 3.2 Partner invite — total failure

Same run, 40 invites at concurrency 20, 15-second client cap.

| | |
|---|---|
| requests | 40 |
| succeeded | **0** |
| failed | **40** |
| latency | p50 15007ms, p95 15012ms — every single one hit the cap |

A separate single-request probe got no response after **120 seconds**.

`backend-django/apps/relationships/views.py:66` calls `send_mail` inline in the
request handler, and `EMAIL_TIMEOUT` is set nowhere in the repo. Django passes
that straight through to `smtplib.SMTP(timeout=None)` — the socket has no
deadline at all.

The local stack cannot reach Resend's SMTP, which is why it hangs here rather
than merely being slow. That does not make the finding local: the defect is the
absent timeout, and the consequence is that any degradation of the mail path
becomes a total Django outage. Production is two synchronous gunicorn workers.
Two invites.

Three more request-path `send_mail` calls share the shape:
`apps/accounts/views.py:156` (signup verification), `:495` (forgot password),
`apps/accounts/email_views.py:55` (resend verification).

### 3.3 Database concurrency — falls over at 8

`GET /api/v1/relationships/{id}/context` on FastAPI: touches Postgres, no LLM,
so the connection behaviour is not hidden behind model latency. The driver has
no relationship, so a `404` here means a completed database round trip — which
is what is being measured. A `500` means it never got one.

| concurrency | requests | reached the DB | 5xx | p95 | **pg peak** |
|---|---|---|---|---|---|
| 1 | 3 | 3 | 0 | 153ms | 74 |
| 2 | 6 | 6 | 0 | 249ms | 84 |
| 4 | 12 | 12 | 0 | 440ms | **99 / 100** |
| 8 | 24 | **2** | **22** | 676ms | 88, then Postgres stopped answering |
| 16 | 48 | **0** | **48** | 390ms | Postgres unreachable |

The FastAPI logs during the concurrency-8 step:

```
asyncpg.exceptions.TooManyConnectionsError: sorry, too many clients already
```

Note the baselines rising down the table. That is the leak in §3.4 accumulating
across the sweep.

**Forty-five seconds after all load stopped**, with the stack idle:

```
$ psql -tAc "select count(*) from pg_stat_activity"
105

$ psql -tAc "select state, count(*), max(now()-state_change) from pg_stat_activity group by 1"
idle    | 99 | 05:00:06
active  |  1 | -00:00:00

$ psql -tAc "select client_addr, count(*) from pg_stat_activity group by 1"
192.168.97.5 | 97      <- relationshipai-fastapi-1
```

99 idle connections, the oldest five hours old, 97 held by one FastAPI replica,
all with a NULL query — opened and never used. Postgres was refusing new
connections. `GET /health` was returning `{"status": "healthy"}` throughout.

### 3.4 The leak, isolated

From a freshly recreated FastAPI container, five **serial** counselling turns —
no concurrency at all:

| | pg connections |
|---|---|
| baseline | 8 |
| after turn 1 | 18 |
| after turn 2 | 28 |
| after turn 3 | 38 |
| after turn 4 | 48 |
| after turn 5 | 58 |
| **after 60 seconds idle** | **58** |

Exactly +10 per turn. Zero recovery.

`backend-fastapi/app/memory/vector_store.py:35-38` caches an asyncpg pool on the
*instance* and never closes it; `backend-fastapi/app/api/chat_router.py:243`
constructs a fresh `SessionMemoryRetriever` on every turn, so the cache never
hits and each turn opens a new pool. `asyncpg.create_pool` defaults to
`min_size=10` and opens all ten eagerly.

**100 ÷ 10 = 9 turns after the ~8-connection baseline.** That is the capacity
number.

By contrast, the *correctly closed* pools drain fine — 20 requests at
concurrency 5 against `get_db_pool` returned connections to baseline 8 and held
there for a full minute. The pattern is not inherently broken; one call site is.

### 3.5 Counselling turns — the failure is silent

20 turns, concurrency ramping 1 → 2 → 4 → 8:

| concurrency | turns | HTTP 200 | p50 | p95 | pg peak |
|---|---|---|---|---|---|
| 1 | 2 | 2 | 8510ms | 12015ms | 78 |
| 2 | 4 | 4 | 2244ms | 3982ms | **98 / 100** |
| 4 | 8 | 8 | 1805ms | 2212ms | **100 / 100** |
| 8 | 6 | 6 | 1721ms | 1746ms | Postgres unreachable |

**Every single turn returned HTTP 200 with a real model reply, including the
ones served while Postgres was completely unavailable.**

That is by design, and the design is half right. `get_optional_pool`
(`chat_router.py:39-58`) and every consumer of it — `fetch_personalization`,
`fetch_shared_context`, `fetch_memories`, `persist_turn` — swallow database
failures so that counselling never breaks for someone who may be distressed.
Sound instinct.

The half that is wrong: when it degrades, the user gets a counselling reply with
**no personalization, no memory of past sessions, no shared context, and no
persistence to history** — and there is no log line, no metric and no Sentry
event to say so. The product silently becomes a generic chatbot and reports
success. Nobody would find out.

The first turn's 8.5s p50 is cold-start on the counselling path; warm turns are
1.7–2.2s, which is fine.

Separately measured: **0 of 20 turns returned `FALLBACK_REPLY`**, so the provider
itself was healthy throughout.

## 4. LLM cost per turn and per cohort

`tiktoken` is not installed in either venv, and a chars/4 approximation is not
good enough to price a fixed-margin SKU against. So the cost phase builds the
**real** system prompt with `build_system_prompt` and makes three direct gpt-4o
completions, reading `usage.prompt_tokens` and `usage.completion_tokens` off the
responses. These are the provider's own counters.

| | measured |
|---|---|
| system prompt | 1440 chars |
| input | **317 tokens/turn** (316, 320, 316) |
| output | **56 tokens/turn** (50, 56, 57) |
| retrieval embedding | 15 tokens (`text-embedding-3-small`) |
| pricing used | gpt-4o $2.50/1M in, $10.00/1M out |
| **cost per counselling turn** | **$0.001349** |

### `go-to-market.md` §3.1 is wrong, in the safe direction

§3.1 estimates *"Counselling reply (3k in / 400 out) ~$0.012"* and lands on
~$0.60–1.20 per couple per month. **Measured is $0.00135 — roughly 9× cheaper**,
which puts a 20–60 turn month at **$0.03–0.08 per couple**, not $0.24–0.72.

But the reason it is cheap is a defect, and correcting it moves the number back.

### The caveat, and it is large

Input is only 317 tokens because `chat_router._initial_state`
(`chat_router.py:264-289`) puts **exactly one message** in `short_term_buffer`,
and `persist_turn` stores only a 200-character preview. **The FastAPI counsellor
is stateless within a session — it never sees the conversation so far.**

Thread the history, as any real counselling product must, and input grows
roughly linearly with the turn number. Modelling turn *n* as prompt + *n* ×
(user turn + assistant turn):

| turns/couple | stateless $/couple | with history $/couple | $/30-couple cohort | gross margin at $39 |
|---|---|---|---|---|
| 20 | $0.027 | $0.07 | $2.17 | 99.8% |
| 50 | $0.067 | $0.36 | $10.81 | 99.1% |
| 100 | $0.135 | $1.32 | $39.56 | 96.6% |
| 200 | $0.270 | $5.03 | $150.87 | 87.1% |
| 500 | $0.674 | $30.51 | $915.31 | **21.8%** |

**The cost column is measured. The turns-per-couple column is an assumption** —
there is no usage data at 0 users, and this is the number to replace first once
the first cohort is live.

### What this means for the $39 one-off

D2 makes COGS a fixed-margin question rather than a subscription question, and
the honest answer is:

1. **At today's stateless implementation, COGS is irrelevant.** Even 500 turns
   is 67 cents.
2. **Once conversation history is threaded — which it must be — COGS becomes a
   real function of engagement**, and a heavy couple at 500 turns costs $30 of a
   $39 one-off.
3. `go-to-market.md` §4 already recognises this and bounds the counsellor at 12
   months (D3.11a). That bound caps duration, not intensity. **The missing
   control is a per-couple turn budget or a context window cap**, and it is
   cheap to add now and awkward to add after somebody has paid.

A sliding context window of, say, the last 10 turns would flatten the "with
history" column back to near the stateless one at any volume, and is almost
certainly better counselling than either extreme.

### Not counted here

The counselling turn is not the whole COGS picture. Also per-message, on other
paths: safety layers 2 and 3 (`gpt-4.1-nano`, only for messages scoring
0.3–0.8), post-session memory extraction (`gpt-4.1-nano`, via Celery), and the
Django chat-assist path in `apps/chat/assist.py` (tone coach, rephrase, read
coach — `gpt-4.1-nano`, with its own call counter already built in). All are
nano-tier and an order of magnitude below the counselling reply, but a full
per-couple COGS number should measure them rather than assume them. `assist.py`
already counts its own calls, which is the right place to start.

## 5. Where it falls over first, in order

1. **Postgres connections, at 9 counselling turns per process.** Not concurrency
   — cumulative. This is the wall.
2. **Postgres connections again, at ~4 concurrent requests** to any DB-backed
   FastAPI endpoint, from the per-request `create_pool` pattern.
3. **Django, at 2 concurrent partner invites**, from the untimed inline SMTP
   call and two synchronous gunicorn workers.
4. **Silent degradation before any of the above is visible**, because the
   counselling path swallows database failures and the health check is a
   hardcoded literal.

Nothing in the top four is throughput. Django's request handling and the LLM
provider both had headroom in every phase. Every wall is a resource-lifecycle
bug.

## 6. What to re-measure after the fixes

Re-run all three phases and expect:

- `--phase db` at concurrency 16: 0 × 5xx, connections back to baseline within
  seconds of the run ending.
- Five serial counselling turns: connection count **flat**.
- `--phase onboard`: invites succeed, p95 under 1s.
- Then raise the phases past these levels, because the current numbers stop
  being informative the moment the leak is gone — they are measuring the leak,
  not the system.

And re-run `--phase onboard` against **gunicorn with two sync workers**, not
runserver, before believing the Django numbers.
