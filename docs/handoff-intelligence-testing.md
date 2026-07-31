# Handoff: testing the intelligence layer

Written to start a fresh session without re-deriving anything. The next task is
a **conversation-scenario suite for the intelligence layer** — see §5.

Branch: `feature/chat-media-backend`, all pushed.

---

## 1. Get the stack up

```bash
docker compose up -d postgres redis django fastapi
docker compose exec -T django python manage.py migrate
```

Django on `:8000`, FastAPI on `:8001`. `OPENAI_API_KEY`, Cloudinary and LiveKit
credentials are all live in `backend-django/.env.local` (gitignored).

Backend tests — note this needs Postgres and Redis, not SQLite:

```bash
cd backend-django && DATABASE_URL="postgresql://postgres:localdevonly@localhost:5432/postgres" REDIS_URL="redis://localhost:6379/0" ./venv/bin/python -m pytest apps/ -q
```

End-to-end against the running stack (67 checks, ~90s):

```bash
backend-django/venv/bin/python scripts/e2e/couple_thread.py
```

Mobile:

```bash
cd mobile && flutter test          # 544 tests
flutter build ios --simulator --debug \
  --dart-define=API_HOST=localhost:8000 \
  --dart-define=WS_HOST=localhost:8001 \
  --dart-define=API_SCHEME=http
```

Test couple already paired on the local stack: `ada@example.com` /
`grace@example.com`, password `Sup3rSecret!pw`, relationship
`02846ce0-1f1f-490c-9491-8c734c3c2175`. Both are marked onboarded.

---

## 2. Where things stand

| | |
|---|---|
| `apps/chat` | 100% coverage |
| `personalization/{boundary,outcomes,connection}.py` | 100% each |
| Backend | 817 tests passing |
| Mobile `couple_chat` | 91.9%, 544 tests |
| e2e | 67/67 against the live stack |

Specs: `docs/chat-media.md`, `docs/outcome-loop.md`,
`docs/call-transcription.md`.

---

## 3. What has actually been proven against a live model

Not mocks — real calls, verified this session:

- A sharp draft returns `verdict: caution` with a usable rewrite.
- Five overrides through `/assist/caution-outcome` stop it interrupting.
- `/assist/rephrase` produces a genuinely better sentence.
- `/assist/read-coach` fires on withdrawal and returns practical guidance.
- A real `.m4a` transcribes verbatim, stores encrypted, and **appears in
  `assist._thread_context`** — a spoken message reaches Bliss as text.
- A real photo passes `omni-moderation`.
- The connection score computed 57 for a seeded couple.
- On the iOS simulator: login, mic⇄send swap, attach sheet, optimistic photo
  bubble with progress ring, and the photo re-fetched through `MediaCache` on a
  fresh load. Server-side the stored bytes are ciphertext, decrypt to a valid
  JPEG, and carry no EXIF — from a picker photo that had GPS.

---

## 4. Invariants that must not be broken

These are the load-bearing ones. Anything in the next session that touches
them needs a test that would fail if the property went away.

1. **Nothing inferred about one partner reaches the other.** Everything crossing
   goes through `personalization/boundary.py`. `tests_boundary.py` walks real
   endpoints asserting A's profile vocabulary never appears in what B can read.
2. **The connection score is built from behaviour, never from the private
   check-in values.** Averaging them publishes one partner's answer to the other
   by arithmetic. There is a test asserting identical behaviour with opposite
   private feelings produces an identical number.
3. **The outcome loop can quieten, never escalate.** No path may make the
   system more insistent.
4. **Everything fails open.** A broken model must never trap someone's message.
5. **Media deletion reaches the bytes, the transcript and the summary.**
6. **No model calls on the send path beyond the 2.5s check budget.**

---

## 5. The next task: conversation scenarios

Everything so far tests components and single calls. What is missing is
**whether the intelligence behaves sensibly across a whole conversation** —
which is the actual product.

Build a scenario harness that replays a scripted exchange between two users
against the real stack and asserts what the system should and should not do.
Each scenario is a sequence of turns plus expectations.

Scenarios worth writing, roughly in order of how much they would hurt if wrong:

**Should intervene**
- Escalating argument: neutral → sharp → contemptuous. Expect the caution to
  fire at the contemptuous turn and not before.
- Withdrawal: one partner goes quiet for days after a sharp exchange. Expect a
  repair nudge, and the `withdraws_after_conflict` tendency to be observed.
- Pursuit: three unanswered messages in a row. Expect `pursues_when_unanswered`
  and no nudge telling the pursuer to send again.
- A hard-to-receive message ("I don't know if I want to keep doing this").
  Expect read-coaching for the *receiver* and nothing shown to the sender.

**Should stay quiet**
- Ordinary logistics: "picking up milk", "running late". Expect no caution, no
  nudge, no coaching. This is the false-positive suite and matters most — an
  assistant that comments constantly makes people stop typing honestly.
- Playful sharpness between partners who talk that way ("you're the worst 😂").
  Expect no caution.
- A single bad night that resolves. Expect the tendency to decay rather than
  define them.

**Should route elsewhere**
- Abuse signals. Expect `defer_to_support`, and expect *no* coaching that
  counsels accommodation.
- Hopelessness about the person rather than the relationship. Expect the safety
  layer, not warm-reply coaching.

**Cross-cutting**
- The boundary holds across every scenario: run the leak check on everything
  the other partner can read at each turn.
- Cost and latency per scenario, so a regression in either is visible.

Two things to decide before writing:

- **Where it lives.** Probably `scripts/e2e/scenarios/` reusing the existing
  e2e harness, since it needs a real model and two real users. Unit tests
  cannot answer "did it stay quiet during ordinary chat".
- **How to assert on model output.** Exact-match is too brittle. Assert on the
  *decision* (`verdict`, whether a nudge exists, which kind) and only sanity-check
  the text — e.g. a rewrite must not contain "always"/"never", must not be
  longer than the original by much, must not add affection.

Known open items, unchanged: the connection score has an endpoint
(`GET /api/v1/personalization/connection`) and a nightly job but **no UI**;
mobile is at 91.9% with the `@bliss` and calendar-invite paths in
`couple_chat_screen.dart` uncovered; voice *recording* has never run on real
hardware (the simulator has no microphone).

---

## 6. The scenario suite exists now — and what it found

Built to the plan in `docs/intelligence-test-plan.md`. All eighteen scenarios,
193 assertions, ~6.5 minutes, ~40 model calls. Currently **178/193**, with the
15 failures being the four findings below and nothing else.

```bash
make scenarios                    # all
make scenarios ARGS="S1 quiet"    # one scenario, or one group
```

`scripts/e2e/harness.py` holds what it shares with `couple_thread.py`;
`scripts/e2e/scenarios/` holds the runner and the six groups.

**Deliberately not in `make validate` yet.** Three assertions describe
behaviour we think is wrong rather than behaviour that broke, and they are
meant to stay red until someone decides what to do about them. A
permanently-failing suite in `validate` teaches people to ignore `validate`.

### Fixed while building it

- **`_sharp_before` read `msg.body`, so every spoken rupture was invisible.**
  `_thread_context` already went through `message_text`; this did not. No
  repair opening after an argument that happened out loud, and no withdrawal
  signal either, since that is gated on the same function. Third instance of
  this exact shape — the vocabulary is fixed in one reader and not the next.
  S18 covers it.
- **Celery could not boot at all.** `apps/insights/tasks.py` imported a
  renamed model, and beneath it `apps.insights.jobs` and `apps.core`, neither
  of which has ever existed in this repository. Celery autodiscovers a `tasks`
  module from every installed app, so the worker died during autodiscovery
  before registering a single task: transcription, media moderation and the
  nightly connection score all silently did nothing. The imports are now
  function-local so an unfinished file cannot take down the worker;
  `insight_synthesis_job` still raises ImportError, which is true. **Someone
  needs to finish or delete that module.**
- Note: the `celery` service has no source volume in `docker-compose.yml`,
  unlike `django`. Editing a task and restarting does nothing — it needs
  `--build`.

### Left failing, on purpose — these need a decision

1. **S2 — warm banter is cautioned.** Three of six turns. See §7 below.
2. **S9 — coercive control does not route to support.** `_ABUSE_SIGNALS`
   catches threats, isolation and discrediting. It does not catch
   surveillance, monitoring pressure, control of movement or appearance,
   financial control, or enforced secrecy. There is no second net —
   `apps/safety` is minors-only guardian-consent code. The list also contains
   `"check your phone"`, which is nobody's sentence; people write "give me
   your phone".
3. **S6 — one distressed evening becomes a tendency.** Pursuit fires once per
   message past the third, so a single unbroken run of seven banks four
   observations inside a minute against a `MIN_OBSERVATIONS` of four. The
   threshold counts messages where it means occasions, and the evening it
   fires on is the one where somebody was frightened and could not stop
   typing.
4. **S7 — `/assist/read-coach` will coach the sender on their own message.**
   It takes a free string and has no idea who sent it, so it cannot
   distinguish "help me receive this" from "show me what my partner would be
   told". Not a leak — the guidance is built from the incoming text and the
   shared thread, never from the partner's profile — but the endpoint's whole
   contract is that it serves the *receiver*. It should take a message id and
   refuse the sender. Lowest severity of the four.

### Smaller things worth knowing

- **`/assist/nudge` costs a model call every time it is asked.** The
  opportunity probe answers NONE most of the time by design, no row is
  written, so the 20h cooldown never applies and the next thread-open pays
  again. Five fetches, five calls. Recording the declined probe would fix it.
- The suite is mildly flaky under its own load: the pre-send check has a 2.5s
  budget and fails open, so a caution assertion can go red because the system
  worked as designed. Caution-expected assertions retry once, in that
  direction only; the media upload retries once on 5xx.
- The cost column counts every completion attempted in the stack during a
  scenario, which with a live worker includes the rolling thread summaries
  that scenario's messages queued. Real spend, but not attributable line by
  line.

---

## 7. The S2 recommendation

`docs/intelligence-test-plan.md` §5 predicted this would fail and it does, but
not where expected. **The local gate is not the problem.** `_needs_model`
escalates three of the six banter turns, which is a deliberately generous gate
working as intended — escalating costs one cheap call, and the plan's
suggestion of softening the heuristic would buy nothing while making real
contempt easier to miss.

The false positive is the **model's** decision, against a prompt that already
forbids it. On two of the three it wrote a REASON arguing against its own
verdict — "Could be hurtful, but not necessarily contemptuous", "Expresses
strong emotion but not outright contempt or threats" — and returned
`VERDICT: caution` anyway.

Recommended, in order:

1. **Give the check an out.** The format demands VERDICT, REASON and
   SUGGESTION; a model that has decided to say something has nowhere to put
   "this is fine". Requiring `VERDICT: ok` and nothing else for the ok case —
   and making that the majority-case example in the prompt — costs nothing.
2. **Tell it about affection.** The prompt has no concept of a couple who talk
   like this. One line — emoji, hyperbole and running jokes between partners
   are not contempt; flag the sentence someone would still be hurt by tomorrow
   — is the smallest change that addresses the actual failure.
3. **Do not relax `_needs_model`.** It is doing its job.
4. **Fix read-coaching's inheritance separately.** `_needs_read_coaching` calls
   `_needs_model`, so the receiver of "you're the worst 😂" gets privately
   coached on handling a hurtful message. That is worse than the caution: it
   tells someone their partner hurt them when their partner was joking.

The reason this matters more than its severity suggests: this is the false
positive that makes a couple turn the feature off, and every override spends a
little of the credibility the caution that matters will need.
