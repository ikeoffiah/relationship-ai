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
cd mobile && flutter test          # 558 tests
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
| Backend | 844 tests passing |
| Mobile `couple_chat` | 558 tests |
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

Built to the plan in `docs/intelligence-test-plan.md`. All nineteen scenarios,
201 assertions, ~9 minutes, ~40 model calls. Currently **200/201** — one
failure left, S2.5, and §7 explains why it is a model limit rather than a bug.

```bash
make scenarios                    # all
make scenarios ARGS="S1 quiet"    # one scenario, or one group
```

`scripts/e2e/harness.py` holds what it shares with `couple_thread.py`;
`scripts/e2e/scenarios/` holds the runner and the six groups.

**Deliberately not in `make validate` yet.** S2's six assertions describe
behaviour we think is wrong rather than behaviour that broke, and they are
meant to stay red until someone decides what to do about them. A
permanently-failing suite in `validate` teaches people to ignore `validate`.
Wire it in the day S2 is settled — it is the last one.

Run it against the stack the containers are actually serving. `docker-compose`
mounts `./backend-django` relative to wherever compose was invoked, and the
project name is fixed (`relationshipai`), so in a repo with two git worktrees
whichever ran `docker compose` last owns the containers — silently, and the
suite will happily test the other worktree's code. `make scenarios` runs from
the checkout it lives in; if results look impossible, check
`docker inspect relationshipai-django-1 --format '{{range .Mounts}}{{.Source}}{{end}}'`
before you believe them.

### Fixed while building it

- **`_sharp_before` read `msg.body`, so every spoken rupture was invisible.**
  `_thread_context` already went through `message_text`; this did not. No
  repair opening after an argument that happened out loud, and no withdrawal
  signal either, since that is gated on the same function. Third instance of
  this exact shape — the vocabulary is fixed in one reader and not the next.
  S18 covers it.
- **Pursuit re-fired on every message of a run**, so one unbroken run of seven
  banked four observations in a minute against a `MIN_OBSERVATIONS` of four.
  Now observed once, when the run reaches the threshold. Four observations
  means four occasions, which is what the constant was always for. This also
  settled an off-by-one: the old condition fired on the third message of a run
  at the start of a thread but the fourth mid-thread, because mid-thread the
  partner's message was still inside the window it examined. Three in a row is
  what it means now, wherever it happens. S6 covers it.
- **`_ABUSE_SIGNALS` did not contain coercive control.** Threats, isolation
  and discrediting only — so "I went through your phone last night" produced
  nothing at all: no referral, and no coaching either, since it does not look
  sharp to the gate. Surveillance, control of movement and appearance,
  financial control and enforced secrecy are in now, grouped by which part of
  the pattern they belong to. `"check your phone"` is gone; it was nobody's
  sentence and looked like coverage while catching nothing.

  Monitoring pressure is deliberately still out — "why did it take you two
  hours to answer me" is ordinary friction at least as often as it is control,
  and no phrasing separates the two. S9 now asserts *both* sides, so widening
  the list again cannot quietly sweep a normal row about phones into a support
  referral.
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

### Left failing, on purpose

1. **S2.5 only.** The prompt change landed and took S2 from six failures to
   one; §7 has what changed and the measurement showing the last one is a
   model limit rather than a prompt one. Per-couple calibration (§8) is a
   complement, not a rescue: it needs history, and S2 fails on turn two of a
   brand-new couple.

### Since fixed

- **S7 — `/assist/read-coach` would coach the sender on their own message.**
  It took a free string and had no idea who sent it, so it could not
  distinguish "help me receive this" from "show me what my partner would be
  told". It now takes `{"message_id": ...}`: 404 if that is not a message in
  this couple's thread, nothing at all if the caller sent it, and the text is
  read from the row via `assist.message_text` rather than from the body —
  which also means a voice note is coached on its transcript, where a caller
  passing a string would never have found it. Never a leak, before or after:
  the guidance is built from the incoming text and the shared thread, never
  from the partner's profile. What it fixes is a load-bearing contract that
  only the client was enforcing, and a model call that any caller could spend
  on any string. The old `message` key still answers for one release so a
  mobile build that has not shipped the id yet keeps working; the branch in
  `assist_read_coach` says when to delete it.

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

## 7. S2: what the prompt fixed, and what it did not

Five of S2's six assertions now pass. The sixth is a model limit, not a prompt
one, and the evidence for that is below.

### What changed

**The check prompt.** Three additions, each answering an observed failure
rather than general good practice:

- *"Almost every message you see is fine. The normal answer is ok."* The
  previous version described what to flag and left the majority case implicit —
  and a model with a REASON and a SUGGESTION field to fill has an incentive to
  find something to put in them.
- *An affection paragraph.* The vocabulary had no concept of a couple who tease
  each other, so "you're the worst 😂" was textbook second-person-plus-negative
  -word and nothing said otherwise.
- *"Judge what will happen, not what could"*, and *"a reason that argues
  against your own verdict means the verdict is ok"*. Both are transcriptions
  of what it actually did: every wrong flag came back hedged — "Could be
  hurtful", "Expresses strong emotion but not outright contempt".

Plus four worked examples, deliberately not the phrasings the suite tests, so
the line is what is being taught rather than the strings.

**Read-coaching's gate.** This was three of the six failures and a worse bug
than the caution. `_needs_read_coaching` inherited `_needs_model`, the
send-side contempt vocabulary, so the receiver of a joke was privately coached
on handling being hurt. The caution merely interrupts you; this reinterprets
your relationship for you. It now checks withdrawal first and unconditionally
— nothing may talk `_HARD_TO_RECEIVE` out of firing — then leaves playful
register alone, then falls through to the old gate. Its prompt also leads with
the decision instead of the assumption; it used to open "a partner has just
received the message below and it *may be hard to take*", which answers the
question it was meant to ask.

### The one still failing, and why

`S2.5 — "you're ridiculous and I'm telling everyone"` still cautions. Four
rounds of prompt work moved it from flagging with a flat reason to flagging
with *"Could be seen as a harsh joke, might hurt if taken seriously"* — the
model naming it as a joke and hedging, in exact defiance of two explicit
instructions. That is not a prompt that needs more words.

Measured directly, same prompt, same thread context, six drafts spanning both
classes:

| model | correct | latency |
|---|---|---|
| `gpt-4.1-nano` (current) | 5/6 | 714ms |
| `gpt-4.1-mini` | **6/6** | 782ms |

**+68ms, inside a 2.5s budget.** The check already reads its model from
`OPENAI_FAST_MODEL`, so this is an env var, not a code change. It is left as a
decision rather than taken, because it is recurring spend on every draft that
clears the local gate — roughly 4× per call at list prices. The tiering exists
precisely so that number stays small, and S1 is the assertion that keeps it
honest.

If the answer is no, the alternative is to accept that one borderline line and
change S2.5's expectation. It is genuinely the most ambiguous of the three, and
"I'm telling everyone" does read as a threat to embarrass outside a thread that
is visibly a joke.

---

## 8. Per-couple calibration of what counts as sharp

Sharpness is couple-relative. "You're the worst 😂" between two people who talk
that way is affection; the same words elsewhere are contempt. One global
threshold cannot be right for both, and the couple it is wrong for turns the
feature off.

The loop that learns this already existed — `outcomes.py`, per-couple, decayed,
one-directional — it just ran at a single level per couple, so overriding the
caution on banter also quietened it for genuine contempt. It now splits by
**register**.

**How.** `assist.register_of(draft)` returns `playful` or `plain`, locally and
free: emoji or laughter markers make it playful, *unless* the draft contains
name-calling, a threat, or an absolute aimed at the partner. Those
disqualifiers are the point — an emoji after "you always do this" does not make
it a joke, and letting it would hand couples a way to calibrate away the exact
patterns the check exists for. The most a couple can teach this is to stop
commenting on their banter.

`/assist/caution-outcome` takes an optional `draft`, derives the register from
it, and records under `caution@playful` / `caution@plain`. Only the register is
kept — the draft is not stored, logged or forwarded, and `CouplePolicy` still
records that a kind of help was offered in a kind of moment, never what was
said.

**Why the sender rather than the receiver.** The obvious design is to ask the
partner who received a borderline message whether they minded. Two reasons not
to. It tells the receiver that the system had doubts about their partner's
message, which is a leading question that manufactures injury where there was
none — the inverse of the S7 property. And it is biased in the worst possible
direction: in a couple with a controlling dynamic, the partner being asked will
say it was fine, so the feature would learn to go quiet exactly where it should
stay loud. Any feedback channel routed through the person with less power in
the relationship has this property. The sender's own override is supervised,
already collected, and comes from the person who knows what they meant.

If receiver input is wanted later, the safe shape is a *preference* asked once
in settings ("when you two are joking, should Bliss stay out of it?"), never a
verdict on a specific message.

**Both keys are read.** `_caution_is_wanted` checks the register bucket *and*
the bare `caution` key. Reading only the register key would have been the
write-here/read-there bug that took this loop out once already — silently, for
every couple who had taught it something before today.

**S19** covers it: banter cautions, five overrides, banter goes quiet including
a joke never sent before, and contempt still cautions for that same couple.
Plus unit tests in `tests_assist.py` for the disqualifiers.

**The loop is connected now.** Until this landed, mobile never called
`/assist/caution-outcome` at all — so this calibration, the suppression in S11
and the `accepts_rephrasing` tendency all received nothing from real users and
were exercised only by this suite. The caution sheet's three buttons now report
through `CoupleChatViewModel.reportCautionOutcome`, with the flagged draft
attached so the register can be derived.

Three details worth keeping:

- It reports the draft that was **flagged**, not what ends up being sent. On
  "send this instead" those differ, and filing the lesson against Bliss's own
  rewrite would calibrate the system on its own prose.
- A **dismissed** sheet reports nothing. The three outcomes are things somebody
  chose; backing out is not one of them, and guessing which it resembles would
  put a made-up signal into the only supervised evidence this system gets.
- Reporting is fire-and-forget in both directions — not awaited, errors
  swallowed at the service, at the future, and around the call. The caller is
  one statement away from sending somebody's message.
