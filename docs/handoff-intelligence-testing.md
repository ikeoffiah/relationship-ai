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
