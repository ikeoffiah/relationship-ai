# The AI session surface — chrome and first turn

Owner: product/design (`local_81faf803`). Execution-plan **P0.10**.
Built by: engineer. **Blocked on the counsellor-memory fix — see §3.0.**

Two defects from the 2026-08-03 live walkthrough, both on the screen where a
facilitator forms their judgement of whether this is a real product.

---

## 1. What is there now

Opening a private session renders, top to bottom:

1. **App bar** — "Private session" · support icon · "Consent" pill
2. **Pink bar** — "Private session · Nothing shared  **Change**"
3. **White bar** — 🔒 "Your private session"
4. **Grey bar** — "You are talking to an AI, not a licensed therapist. **What that means**"
5. ~1100pt of empty cream
6. "Type a message…"

**"Private session" appears three times on one screen.** Four bars of disclosure,
three tap targets that lead to two destinations, and no product.

Nothing here is wrong individually — each bar was added by someone doing the
right thing. The failure is that nobody has looked at them together since.

---

## 2. Chrome — three bars become one

### 2.1 The line

Keep the **app bar** (title, support icon, consent pill). Replace bars 2–4 with a
single persistent line beneath it:

> 🔒 **Private — nothing here is shared with your partner. You're talking to an
> AI, not a licensed therapist.**  **Details**

One line, one affordance. **Details** opens a sheet carrying the full text that
bars 2–4 currently spend vertical space on:

- What "private" means here, and what is and is not retained — this must match
  `session-retention-wording.md` §3.1 exactly, and it is the sheet that fixes the
  §2.11 contradiction at the point a user actually asks
- What "not a licensed therapist" means, in the plain wording bar 4's "What that
  means" already links to
- A route to support, which is *also* still in the app bar (D3.17 — never fewer
  than one)
- A link to the consent settings, the same destination as the pill

### 2.2 Rules

- **The AI disclosure stays visible on the screen itself**, not only in the
  sheet. It is the one thing here with a regulatory reason to be persistent, and
  `marketing-copy.md` §1.5 is right that it helps in App Store review. Shortening
  it is fine; hiding it behind a tap is not.
- **The consent pill and "Change" are one destination.** Two controls that do the
  same thing read as two different things.
- **Do not remove the support icon.** It is load-bearing, tested, and named in
  D3.17.
- **Nothing gains a lock icon that implies encryption we do not have.** Per the
  audit's do-not-say list: at rest with a server-held key, not end-to-end.

### 2.3 While here — the banner on the four tabs

Separate from this screen and worth doing in the same pass. `MainNavigationScreen`
renders the AI-disclosure banner in a `Column` **outside any `SafeArea`**, so on
a device with a Dynamic Island it renders clipped — *"You are talking to a[…]l
therapist."* — on Today, Us, Talk and You.

It is the most-seen pixel in the app and it has been broken the entire time.
One-line fix.

**Decided — D3.36.** The banner comes off **Today, Us and You**. It stays on
**Talk** and inside every session.

Narrower than the "remove from all four tabs" version originally proposed, and
better: keeping it on Talk means the disclosure is present wherever an AI
conversation is happening *or is one tap away*, which is what makes the claim
true rather than merely frequent. Banner blindness was making it *less* effective
on the surface where it matters.

Recorded as **reversible on a single reviewer objection**. The in-session
disclosure — the one that actually matters in App Store review — is untouched by
this and stays visible without interaction per §2.2.

---

## 3. The first turn

### 3.0 Do not build this before the counsellor has memory

`_initial_state` puts a single message in the buffer — 317 input tokens per turn,
measured. Every turn is effectively turn one.

**The blank screen is a symptom of that, not a separate defect.** A counsellor
with no memory of the conversation has nothing to open with, and nothing to
follow up. If the empty state is decorated before the memory lands, the screen
looks better, the product is exactly as broken, and **the visible symptom that
would have led someone to the cause is gone.**

That is a fix that removes the evidence rather than the fault, and it is worse
than leaving the screen blank.

**Precondition: both halves of the memory fix shipped** — in-session conversation
memory and the cross-session memory job. Either alone leaves this spec
un-buildable as written.

### 3.1 First-ever session

Bliss opens. Not a system placeholder, not an illustration — an actual first
turn, in the counsellor's own voice.

> Take your time. What's on your mind?

Beneath it, three starters as tappable chips. These are not suggestions of what
to say; they are permission to start somewhere:

- *Something that happened this week*
- *A conversation I'm dreading*
- *Something I want to appreciate about them*

Tapping one puts its text in the composer, **editable, not sent** — same
behaviour as the existing `SuggestionStrip`. Nobody should send a sentence they
did not choose to send.

### 3.2 Returning session — the part that needs the memory

> Last time you were thinking about **how to bring up the money conversation**.
> Where did that get to?

This is the whole reason to wait for the fix. A returning user who is greeted
with the same generic opener has been told, plainly, that nothing was retained
and nothing was understood — which makes the "private space to think out loud"
claim (`capability-claims-audit.md` §1.5) visibly false on the second visit.

**Constraints:**

- The reference comes from a **derived memory**, never from stored message text.
  There is no stored message text (`session-retention-wording.md` D-b) and there
  must not be.
- **Honour the consent gate.** A user whose `session_transcript_retention` setting
  withholds extraction has no memories, so they get §3.1's generic opener every
  time. That is correct, not degraded — they asked for it — and it must not be
  worked around.
- **Never surface anything about the partner.** The boundary import rule applies
  to this opener exactly as it does to the report.
- **Fail to the generic opener.** No memories, memory job failed, retrieval slow
  — open with §3.1. Never a spinner, never an error, never an empty screen.

### 3.3 What must not be built

| Not this | Why |
|---|---|
| An illustration or empty-state graphic | Decoration. §3.0. |
| "Bliss is typing…" before any turn | Theatre; implies work that is not happening |
| Starters that reference the partner by name | The private session is the one place the partner is not present |
| More than three or four starters | A menu of feelings is harder to answer than an open question |
| An opener that asks a question the counsellor cannot follow up | Worse than the blank screen — it promises attention and then forgets |

---

## 4. Acceptance criteria

| # | Criterion |
|---|---|
| S.1 | The session screen renders **one** disclosure line above the message list, not three. |
| S.2 | The AI disclosure is visible on the screen without any interaction. |
| S.3 | The consent pill and the disclosure line's link reach the same destination. |
| S.4 | The support icon remains in the app bar (D3.17, tested). |
| S.5 | The disclosure sheet's retention wording matches `session-retention-wording.md` §3.1 verbatim. |
| S.6 | The four-tab banner is inside a `SafeArea` and renders unclipped on a Dynamic Island device. |
| S.7 | A first-ever session opens with a Bliss turn and three starters; no blank screen in any state. |
| S.8 | **A returning session's opener references something from the previous session.** Asserted with a seeded memory — this is the criterion that proves the memory fix, and the one that fails if the screen was decorated instead. |
| S.9 | A user who has withheld retention consent gets the generic opener on every session, with no error and no degraded state. |
| S.10 | No opener contains anything about the partner. |
| S.11 | Tapping a starter fills the composer without sending. |

**S.8 is the one that matters.** Every other criterion here can be satisfied by
making the screen look better. Only S.8 can tell the difference between the
defect being fixed and the evidence being removed.
