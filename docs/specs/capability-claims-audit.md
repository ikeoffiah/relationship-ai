# Capability claims audit — `marketing-copy.md` §§1, 7, 8

Owner: product/design (`local_81faf803`). Execution-plan **D3.12**.
Audited 2026-08-03 against the repo at `59362ee`, App Store description first.

Every claim below was checked against code or the database, not against docs.
Verdicts: **TRUE** (verified) · **FALSE** (contradicted) · **UNSUPPORTED**
(describes something that does not exist) · **RISKY** (true today, fragile).

**Headline: four must change before outreach. One of them is on the page we
show to clinicians and it is the most dangerous sentence in the copy set.**

---

## 1. Must change before any outreach or submission

### 1.1 "a **validated** attachment and communication assessment" — §8, facilitator page

**FALSE, and it is the worst one.**

The scorer is not the published Griffin & Bartholomew scoring. It uses ad-hoc
subscales assembled in-house:

```python
secure_score     = (r[3] + (6-r[9]) + r[10] + r[15] + (6-r[28])) / 5.0
dismissing_score = (r[2] + r[6] + r[19] + r[22] + (6-r[28])) / 5.0
```

Item 28 appears in both with the same sign and denominator, so it cannot
discriminate between the two scales it appears in. No validation study, no
norming sample, no reliability figure exists.

**Correction, 2026-08-03.** This entry originally also cited *"14 of 30 items
are never read"* as evidence. **Withdraw that bullet — it was wrong.** P0.1
shipped and the scorer now reads 17 of 30, and the engineer's comment at
`tasks.py:18` gives the reason the remainder are unread: the RSQ embeds Collins
& Read AAS material belonging to subscales this product does not compute. That
is correct by design, not a defect.

The item-28 collision was real and is now fixed (`[2, 6, 19, 22, 26]`, plain).
**The "validated" verdict is unchanged** — it rests on ad-hoc subscales, no
norming and no reliability figures, none of which the fix touches. But the
unread-items bullet was a bad argument and removing it makes the remaining case
stronger, not weaker.

To a general audience "validated" is marketing filler. **To the clinicians and
counsellors this page is written for, it is a term of art** meaning
psychometrically validated with published properties. They will ask for the
figures, and the honest answer is that there are none.

`facilitator-report.md` §7 already requires the report itself to say "adapted
from" and to name the adaptation as an adaptation. The website cannot claim more
than the artefact does.

> **Replace with:** *"a structured attachment and communication assessment,
> adapted from the Relationship Scales Questionnaire."*

Volunteering the adaptation converts a discovered weakness into demonstrated
candour. Claiming validation converts it into a discovered misrepresentation, in
front of the exact audience equipped to discover it.

### 1.2 "Call audio is never stored… what persists is talk-time balance, interruptions, whether either partner reached for repair" — §8

**UNSUPPORTED. The capability does not exist.**

`apps/chat/transcription.py` (115 lines) implements exactly one function —
`transcribe_voice_note(media_id)`. There is no call transcription, no
talk-time analysis, no interruption counting, no repair detection.
`docs/call-transcription.md` is headed **"Status: proposed."**

The first clause is technically true — no call audio is stored, because nothing
processes calls. But the sentence as a whole reads as *"we do this, and here is
how carefully we do it."* That is the third false capability claim caught in
three days.

Compounding it: joint video is Tier 3 in `feature-kill-list.md` — frozen, zero
usage even in simulation, and the heaviest dependency in the app. **We would be
describing sophisticated analysis of a feature we have frozen.**

> **Strike the paragraph entirely.** Do not soften it. If the derived-insight
> design ships later it is a genuinely strong differentiator and can be claimed
> then, in the present tense, honestly.

### 1.3 "support resources are one tap from every screen" — §1 description **and** §7 landing page

**FALSE as written, and it is a safety gap as well as a copy problem.**

`SupportAction` appears in 11 screens plus `HubScaffold`, out of **53 screens**.
Covered: the four tabs, AI chat, couple chat, calendar, consent, history,
notifications, settings, about, security.

**Not covered — the notable ones:**

| Missing | Why it matters |
|---|---|
| **All 6 onboarding screens** | The longest continuous stretch a new user spends in the app — 40+ taps — and the one where they are answering questions about attachment, abandonment and closeness. This is the single worst place to have no route to help. |
| Games, game play | — |
| Faith, Focus, Commitments, Two Truths | — |
| Daily ritual | — |
| Relay compose / inbox | Where someone writes the hard message |
| Our story, invite, accept, dissolve | Dissolve especially |
| Joint session entry / video | — |
| All auth screens | — |

Two fixes, and I recommend both:

1. **Make the claim true** — add `SupportAction` to the remaining screens'
   app bars. It is one line each and it is the cheapest safety win available.
   RSQ items 9, 21, 23 and 28 are explicitly about abandonment and rejection;
   answering thirty of those with no visible route to help is a gap
   independent of what the copy says.
2. Until then, soften to *"support resources are always reachable"* — but
   fixing it is better than describing it accurately, and it is P0.10-sized.

### 1.4 "No reports about your partner, to you or to anyone else." — §1, App Store description

**Becomes FALSE the day the Premarital Pack ships.**

We are building a per-couple report and sending it to a facilitator.

The distinction in `facilitator-report.md` §2 is real and defensible — the
report is *self-report, symmetric, consented and dated*, and both partners
receive the identical document, which is categorically not the inferred
asymmetric profile `boundary.py` prevents. But that distinction takes a
paragraph, and this sentence does not make it. A reviewer, a journalist, or a
facilitator reading the App Store description next to the $39 Premarital Pack
sees a flat contradiction.

> **Replace with:** *"We will never show one of you a profile of the other built
> from your private activity — not to you, not to anyone. The only thing anyone
> else ever sees is the assessment you both chose to take, in a report you both
> receive."*

Longer, still strong, and it survives contact with the thing we are selling.

---

## 1.5 Pending verification — not false, not yet true

### "A private space to think out loud" / "work through the conversation you're dreading" — §1 description, §7 landing page

**PENDING.** Added 2026-08-03 after production QA found the counsellor is
stateless within a session: `_initial_state` puts a single message in the
buffer, measured at 317 input tokens per turn.

If every turn is effectively turn one, then *"think something through"* and
*"work through the conversation you're dreading"* claim a continuity the product
does not have. Neither phrase is false about a single exchange; both are false
about the thing a user would understand them to describe.

This is the D3.16a class — **a claim invalidated by what the product turned out
to be, rather than by anything anyone wrote.** Nobody overstated. The copy
described the intended product and the intended product was not shipping.

**It becomes true when the fix lands, and both halves are needed** — conversation
memory within a session, and the memory job across sessions. Either alone leaves
the claim broken in a way a user would notice within two turns.

Related and downstream: `product-assessment.md` §2.9 complained about the blank
first-run screen in the AI session. That was a symptom, not the defect. A
counsellor with no memory of turn one has nothing to open with, so decorating
the empty state would have hidden the actual problem.

**Do not use either phrase until the walkthrough in §5 confirms it.**

---

## 2. Verified true — cite these freely

| Claim | Evidence |
|---|---|
| **Two-sided reveal**: neither sees the other's answer until both have replied | Enforced server-side in `engagement/views.py`; `revealed = i_answered and partner_answered` |
| **"a test that tries to break it and fails"** (§8) | `tests_boundary.py` — **18 tests, all passing**, run today. Strongest verifiable claim in the copy set. |
| **Connection score built from behaviour, can fall, quiet on a bad week** | `personalization/connection.py`; `presentation` returns prominence; 167 `ConnectionScore` rows |
| **No streaks in the product** | `_StreakHeader` replaced with the rolling 30-day count. See §3.1 for a caveat. |
| **Daily question / reveal / check-in / games / plans** | 121 questions, 9 game packs, 61 game questions, `BlissItem` working with beat-driven reminders |
| **Two Truths** | Endpoints exist and are wired (`two-truths`, `/author`) |
| **Daily reading** (§1) | `faith/today` endpoint live, 8 `DailyReading` rows, 6 practices |
| **Private space + help saying it more kindly** | Verified live on device — real AI reply, tone coach present |
| **Not therapy / AI disclosure** | In-app disclosure present. §1.5's advice to keep clinical terms out of metadata is correct. |

---

## 3. Risky but not false

### 3.1 "There is no streak" — §1 and §7

True of everything a user can see: no UI path surfaces it, and
`pointsBalance`/`currentStreak` are parsed by `engagement_models.dart` and
referenced **nowhere else in the app**.

But `EngagementStreak` (121 rows) and `PointsLedger` (187 rows) are still
computed and still accumulating server-side. The claim is safe today and breaks
the moment anyone surfaces a field that is already populated and sitting there.

> Not a copy change. A note for the engineer: if streaks are gone as a product
> decision, stop computing them. A promise held only by nobody having written
> the widget is not held.

### 3.2 "Each couple's report reaches you before the session" — §8

Forward-looking; the report is P0.3, in build, gated on P0.1. Acceptable on a
call *if stated as what will happen*. It must not appear on a live page before
the artefact exists, and per the P0.3 gate it may slip.

### 3.3 "$39 per couple, once. **Nothing for you, ever — no licence, no per-year fee.**" — §8

**Contradicts our own sales motion**, and this one is marketing's to resolve
rather than mine.

**RESOLVED 2026-08-03 — no longer a finding.** The one-SKU pricing decision
killed the tiered Cohort License outright (`go-to-market.md` §5: *"dead as of
that decision… the tiered Cohort License"*). So the facilitator page's *"no
licence, no per-year fee"* is now simply **true**, and there is no sales motion
that contradicts it.

Recorded rather than deleted, because the shape recurs: this finding was correct
when written and was resolved by a decision elsewhere, not by anyone acting on
it. An audit entry that silently disappears teaches nobody.

*Original finding, for the record:* `go-to-market.md` §5.6 defined a Cohort
License ladder ($290–$2,400) and an
Annual Program, with rule 2: *"Quote at cohort two, when they have watched it
work."* D2.1 says the ladder is a negotiating reference and not published —
fine. But "no licence, no per-year fee" does not merely decline to publish a
price. **It promises the licence does not exist**, and then we quote one at
cohort two.

A facilitator who read that sentence and is then quoted $625 has been told two
different things by the same company. In a channel built entirely on trust, at
exactly the renewal moment the licence is designed to capture.

> Suggested: *"$39 per couple. Your first cohort costs you nothing."* True,
> generous, and it leaves cohort two open without promising it away.

---

## 4. Note on method

Marketing has had three false capability claims caught in three days, all by
reading code. The pattern is consistent: **a model or a design document exists,
and that gets read as "shipped."**

For §1.2 the doc was explicitly headed "Status: proposed" and was still written
into copy as a live capability.

A cheap standing rule that would have caught all three:

> A capability may be claimed in copy only if someone has **used it in the
> running app**, or a **passing test exercises it end to end**. A model, a
> migration, an endpoint, or a design document is not evidence of a capability.

The five specs in `docs/` marked *"spec, not an implementation report"* or
*"Status: proposed"* are the highest-risk source of claims in the repo and
should be treated as a do-not-quote list until each is verified individually:
`call-transcription.md`, `chat-media.md`, `daily-questions.md`,
`relationship-insights.md`, `outcome-loop.md`.

Two of those five have since partly shipped (`daily-questions`,
`relationship-insights`) and their documents still say otherwise — which is the
same trap in reverse, and the reason **claims need checking against code in both
directions**.

---

## 5. Pending re-verification — the post-fix walkthrough

Owed once the stateless-counsellor fix lands (both halves: in-session memory and
the cross-session memory job).

The original assessment's walkthrough was run on 2026-08-03 against the local
stack and is on record — a real session, a real reply, four chrome bars, a blank
first-run, and a purple "Validation" chip. That before-state exists nowhere else,
which is the only reason this re-run is worth doing rather than just reading the
diff.

**What it must answer, in order:**

1. **Does the counsellor remember turn one at turn four?** Three-turn probe:
   state something specific, change the subject, then refer back obliquely
   ("the thing I mentioned"). A counsellor that asks what I mean has not shipped.
2. **Does it remember across sessions?** Close, reopen, refer to the prior
   session. Requires the memory job *and* D-c's consent gate to be honoured —
   check the gate too, since it lands in the same area.
3. **Is §1.5's claim now true?** Specifically *"work through the conversation
   you're dreading"* — which implies a thread held over several turns, not one
   good reply.
4. **Did the first-run screen improve for the right reason?** If it was
   decorated rather than fixed, that is a worse outcome than leaving it blank.
5. **Do the P0.10 items still reproduce?** The four chrome bars, the "Validation"
   chip, the clipped disclosure banner.

**Verdict recorded here** as TRUE or FALSE against §1.5, not as an impression.
Per D3.16 the standard is *used it in the running app* — this is that check, and
it is the only claim in this document whose verification requires a person
driving the product rather than reading it.

---

## 6. The memory transparency panel — UNSUPPORTED, and worse than a stub

Audited 2026-08-03 at the design session's request. Consent-adjacent, so it sits
here rather than with them.

### 6.1 The pipeline is not stubbed. It is unwired.

I traced the whole chain rather than accepting "the writer is a stub":

```
AI session → FastAPI streams the reply, writes langgraph_sessions (failing silently)
POST /api/counseling/sessions/end/   ← NEVER CALLED
   └─ CounselingApiService.endSession() has ZERO callers in mobile/lib
counseling.Session never created                        (0 rows, confirmed)
   └─ process_post_session_async never fires
      └─ extract_memories_task never runs
         └─ Memory = 0, MemoryVector = 0 — structurally, not "not yet"
```

**And the one call site that does not exist would not work if it did.**
`endSession(String sessionId)` takes a session id; the endpoint requires
`relationship_id` **and** `transcript`. A solo user has no `relationship_id` at
all, so private-session memory could never work for them even once the call is
wired.

This is not "no real users yet." Every real user in the world would produce zero
memories.

### 6.2 What the panel tells a user

`features/consent/widgets/memory_transparency_panel.dart` (447 lines) renders:

- Title **"Memory Transparency"**
- Zone filter (private / shared), type filter, search
- Per-memory **Edit** and **Delete**
- Empty state: *"No memories found"* / *"No memories found in this zone"*

Every string is literally true. None of it is honest.

*"No memories found in this zone"* reads as **"nothing yet."** The truth is
**"nothing ever."** A user checking what Bliss has learned about them concludes
the system has been running and found little; in fact it has never run. Those
are different facts and the difference matters in both directions — someone
reassured today would have been told the wrong thing the moment the pipeline is
wired.

The panel also offers edit and delete controls for records that cannot exist,
and a zone filter partitioning nothing.

**This is D3.46 in its purest form.** The panel is well built — filters, search,
per-item controls, a tidy empty state — and the polish is exactly why a wholly
non-functional pipeline went unnoticed. A broken feature with a bad empty state
gets reported in a week.

### 6.3 It interacts with D-c, and not the way it looks

D-c gates extraction on `session_transcript_retention`. **That gate would
currently be gating a pipeline that never runs.**

Implement it anyway — the gate must exist before the pipeline is wired, not
after — but two things follow:

1. **The panel is not evidence that the consent gate works.** An empty panel
   under a working gate and an empty panel under an unwired pipeline are
   indistinguishable. Any test of D-c must assert on the extraction path
   directly, never on this surface.
2. This is the **third** surface built around a capability that does not run —
   with the consent control that reads nothing (§1.1 of
   `session-retention-wording.md`) and the therapist access row
   (`feature-kill-list.md` §7.2). The pattern is worth naming: *the further a
   surface is from the code that would make it true, the longer it survives
   being false.*

### 6.4 Recommendation

**Do not build the pipeline for v1** — that is a real feature with a consent
design attached, and D8 freezes it.

**Hide the panel** while `Memory` cannot be written, the same conditional-render
approach as the therapist row. Do not improve the empty state: per D3.46, a
better empty state here makes the breakage *more* invisible, not less.

If the panel must stay visible, its empty state has to say the true thing —
*"Bliss isn't keeping notes from your sessions"* — which is the §3.1 wording from
`session-retention-wording.md` and is a **stronger** privacy position than the
panel currently implies. That is the refusals pattern available here, and it
costs nothing.
