# What we keep from a session — the wording, and what has to be true first

Owner: product/design (`local_81faf803`). Execution-plan **D3.13**.

The instruction was: fix the promise, not the feature, and keep the two halves
distinct — raw transcripts not retained, derived memories retained with consent.

**I can write the first half today. I cannot write the second half, because the
consent it refers to is not enforced anywhere in the code.** Writing it would be
the fourth false capability claim in four days, and it would be one I made.

So this document is in two parts: what has to become true (§1–2), and the wording
that is honest once it is (§3).

---

## 1. What is actually stored — verified, not read off a design doc

There are **three** separate stores, in three different states. Any wording that
treats "session data" as one thing will be wrong about at least one of them.

| # | Store | Contents | Encrypted? | Rows | Written by |
|---|---|---|---|---|---|
| 1 | `counseling.Session.transcript` | **"Encrypted full transcript"** | Yes, per-user key | **0** | nothing — designed, built, never wired |
| 2 | `sessions.Session` (`langgraph_sessions`) | `state_payload` (`{}`) + `summary_preview` — 200 chars of the assistant's reply | **No. Plaintext.** Model comment: *"encrypt at the DB layer in prod"* | **0** | `persist_turn()`, currently failing silently |
| 3 | `memory.Memory` | Derived memories — "Encrypted memory content" | Yes | **0** | `extract_memories_task` → `MemoryExtractor` |

And the control the user is shown:

| Field | Surfaced to user | Read by the retention path |
|---|---|---|
| `UserConsent.session_transcript_retention` | **Yes** — the "Session storage" row with an **Edit** link, in the sheet that blocks every session | **No** |

I checked `persist_turn()`, `extract_memories_task()` and the FastAPI
`/internal/extract-memories` endpoint. **None of them contains the string
`consent`.** The extraction endpoint is gated by `require_internal_token` —
service authentication, not user consent.

### 1.1 The part that is worse than the copy contradiction

The app presents a consent control for session-transcript retention, with an
Edit affordance, on a sheet a user must pass through to reach the counsellor —
**and the retention paths do not consult it.**

A missing feature is a gap. A control that appears to work and does not is a
different category of problem, and it is the one a clinician or a regulator asks
about specifically. It is currently masked by all three tables being empty; it
stops being masked the moment `persist_turn` is fixed.

`product-assessment.md` §2.11 called this a copy contradiction. It is a consent
defect with a copy contradiction on top.

---

## 2. Three decisions the wording depends on

None is large. All three are decisions rather than code problems, which is why
they are here rather than in the engineer's queue.

**D-a — Leave `counseling.Session.transcript` unwired, and make that explicit.**
It is built and writes nothing. Per D3.13 we are not building transcript storage,
so unwired is now the *intent* rather than an accident. Add a comment on the
field saying so, or delete it. Otherwise a future engineer finds an unused
encrypted-transcript field and helpfully connects it, and the promise breaks with
no decision having been taken.

**D-b — Drop `summary_preview`, or make it metadata-only.**
This is the field that makes "we don't keep what you said" false. It is 200
characters of counselling content, in plaintext, and the mitigation is a comment
deferring encryption to production. Session history is Tier 3 frozen
(`feature-kill-list.md`) and the You-tab entry is being corrected anyway, so
nothing needs it. Keep `turn_count` and timestamps if a session list is ever
wanted; drop the text.

**D-c — Gate memory extraction on `session_transcript_retention`, or drop the
consent claim.**
I recommend gating. The field exists, the UI already promises the control, and
the check is one lookup at the top of `extract_memories_task`. Without it we have
a consent toggle that does nothing — and we cannot say "with consent" in any
register, to anyone.

Once D-a, D-b and D-c are done, everything in §3 is true and testable. Until
then, only §3.1 is safe to use.

---

## 3. The wording

### 3.1 Consumer register — in-app, App Store, landing page

Safe to use once D-b lands.

> **We don't keep a record of what you say in a private session.**
> Your conversation with Bliss isn't stored as a transcript — not for you to
> re-read, not for anyone to review, not for us.

Deliberately **not** claiming "nothing is kept" — see §3.2, and never make a
blanket claim we would have to qualify the moment memories ship.

### 3.2 The second half — derived memories

Only usable **after D-c**.

> **Bliss remembers a little, so you don't have to start over.**
> After a session, Bliss keeps a few short notes to itself — the things worth
> carrying into next time, like what you're working on. Not what you said, and
> never the conversation itself. They're encrypted, they're yours alone, your
> partner never sees them, and you can turn this off or delete them whenever you
> want.

The distinction that must not blur, stated once so the difference is legible:

| | Transcript | Derived memory |
|---|---|---|
| What | The words you said | A short note about what matters to you |
| Kept | **No** | Yes, encrypted |
| Who can see it | — | You. Never your partner. |
| Off switch | n/a | Yes, and delete |

### 3.3 Professional register — facilitator page, clinician outreach

Per D5. Only after D-a, D-b and D-c.

> **Session transcripts are not retained.** A private session between a user and
> Bliss is not written to storage as a conversation. What persists is a small set
> of derived, encrypted notes — scoped to that individual, never surfaced to their
> partner, subject to a consent setting they control and can revoke, and deleted
> with their account.
>
> This is deliberate. A word-for-word record of what someone said in a
> counselling session is discoverable in a separation and re-readable by a partner
> who wants to re-litigate it. We would rather not hold it.

That last paragraph is the strongest version of the PM's point — the accident is
a better position than the intention — and it is the register where it lands.

Note the reasoning is lifted from `call-transcription.md` §1, which argues
exactly this for call audio. **The argument transfers; the capability does not.**
Per `capability-claims-audit.md` §1.2 the call feature does not exist and must
not be claimed. Use the reasoning, not the feature.

### 3.4 Do not say

| Never | Why |
|---|---|
| "Nothing is stored" / "we keep nothing" | False once memories ship. A blanket claim we must later qualify is worse than a precise one now. |
| "End-to-end encrypted" | It is not. Encrypted at rest with a server-held per-user key. Different property, and the difference is exactly what a technical reader checks. |
| "Deleted when the session ends" | The current consent-sheet wording. It implies something is written and then removed; nothing is written. Correct it to §3.1 — this is the sentence in the D3.13 contradiction. |
| "We never look at your sessions" | Unqualifiable — safety classification reads every message in flight, by design and correctly. Do not make a claim the safety system contradicts. |

---

## 4. Also required — the general defect

Per D3.13, `persist_turn` keeps failing open and stops failing silent:

```python
except Exception:
    # History is a convenience; never let it interrupt counseling.
    return
```

Fail-open is right and stays. Add a `log.warning` with the exception and a
counter. **This is not about history** — history is being retired. It is that a
bare `except: return` on a write path let a feature be completely non-functional
with nothing anywhere reporting it, and that shape exists elsewhere. A grep for
bare `except` on write paths is worth someone's afternoon.

---

## 5. Acceptance criteria

| # | Criterion |
|---|---|
| 5.1 | No session write path stores message text. `summary_preview` is removed or metadata-only. |
| 5.2 | `extract_memories_task` is a no-op for a user whose `session_transcript_retention` withholds it — asserted by test, both directions. |
| 5.3 | A user can delete their derived memories, and deletion removes both `Memory` and `MemoryVector` rows. |
| 5.4 | No derived memory is reachable by the partner — extend the `tests_boundary.py` assertion to memory content. |
| 5.5 | The consent sheet no longer says "deleted when the session ends"; it says §3.1. |
| 5.6 | The You-tab "Past sessions" entry is removed, or reflects what actually persists. |
| 5.7 | `persist_turn` logs and increments a counter on failure. |
| 5.8 | `counseling.Session.transcript` is documented as intentionally unwired, or deleted (D-a). |
