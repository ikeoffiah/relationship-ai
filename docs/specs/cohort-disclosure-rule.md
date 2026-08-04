# What a facilitator may see about their cohort

Owner: product/design (`local_81faf803`). Execution-plan **D3.10**, incorporating
marketing's two additions.

**The rule is not a threshold. It is a category allowlist plus a ban on
comparison.** Marketing's framing — *the shape of the rule matters more than the
number* — is right, and following it to its conclusion removes the need to pick a
number for almost everything.

---

## 1. Why a minimum-N floor is the wrong primary control

A per-report N was the obvious design and both of marketing's objections break it:

- **Across time.** The same couple being lowest in three consecutive reports
  identifies them to a facilitator who knows the room, while every individual
  report clears any floor you choose. N is computed per report; the leak is
  longitudinal.
- **Across categories.** Completion rate and an item-level low on sex are not the
  same kind of fact. One N cannot be right for both.

There is a third failure neither named, and it is the worst in this setting:
**the facilitator is not a stranger.** Statistical disclosure control assumes an
analyst who cannot see the subjects. A pastor running a 12-couple cohort knows
every couple by name, watched them in the room, and knows who was quiet. Their
side information is enormous, so k-anonymity arguments that hold for a public
dataset do not hold here at any k.

A single N would have looked rigorous and leaked anyway.

---

## 2. The rule

### Rule 1 — Category allowlist. Nothing outside it, ever.

A facilitator may see, in aggregate:

- **Completion** — how many couples started, how many finished, how many are
  waiting on one partner
- **Participation** — how many generated a report; how many are still active at
  week 4
- **Programme operations** — codes issued, redeemed, unredeemed

That is the whole list. Everything else is outside it by default, including
anything anyone later thinks of. **Additions require a decision recorded here**,
not a judgement at the call site.

Never, at any N, in any aggregation:

- Attachment placements, styles or archetypes — individual or distributional
- Any axis position, score or numeric assessment output
- Item-level responses or distributions, on any topic
- Connection scores, check-in scores, engagement depth
- Anything derived from private sessions, chats, or behaviour — already excluded
  by `facilitator-report.md` §2, restated here because a cohort summary is
  exactly where someone would reintroduce it as "just an aggregate"

This answers marketing's second point by removing the question rather than tuning
it. If no sensitive category is ever reported, no category-specific floor is
needed. A per-category threshold is a promise to publish sensitive data carefully;
this is a decision not to publish it.

### Rule 2 — No rankings, no extremes, no ordering.

No "lowest", no "highest", no "most improved", no "couples needing attention", no
sorted list, no percentile, no outlier flag.

This is the whole of marketing's first point. **Re-identification across time is
created by reporting extremes and positions.** Counts do not accumulate into an
identification; ranks do. Ban the shape and the longitudinal leak disappears
without any cross-report bookkeeping.

### Rule 3 — Cohort-scoped, never per-couple, never longitudinal per couple.

Every statistic is computed within one cohort, over that cohort, at one time.
No statistic follows a named couple across reports or across cohorts.

The **cohort view** may continue to show per-couple *operational* status —
`not started` / `one partner done` / `ready` / `report generated`
(`facilitator-report.md` §8.5). That is not an exception: it is completion, it is
in the allowlist, and the facilitator needs it to run the programme. **No
statistic, score or content may be attached to those rows.**

### Rule 4 — Minimum N as a backstop, not a control.

For any count that could be zero or near-zero in a way that identifies —
for example "1 of 12 couples has not started" in a room where the facilitator
knows who — report **bands rather than exact counts** below N = 5:
"most couples", "about half", "a few", "none yet".

N = 5 is chosen to be defensible rather than derived, and it barely matters,
because Rules 1–3 mean almost nothing distributional survives to reach it. That
is the intended outcome: the floor is the last line, not the first.

### Rule 5 — Nothing here weakens the couple's own view.

Everything a facilitator sees, both partners can see. Same principle as
`facilitator-report.md` §2.1 — no view exists that the subjects cannot.

---

## 3. What this costs, and why it is still worth building

The summary a facilitator gets is deliberately thin: how many finished, how many
are waiting, how many are still using it a month later.

That is genuinely less than they could have. It is also:

- **What they actually need** — to chase the two couples who haven't finished and
  to know whether the programme worked
- **What they can already see** — they ran the room
- **The version we can defend on a call**, which matters more than richness in a
  channel built on trust

The line I would say out loud to a facilitator, because it sells rather than
apologises:

> *"I can tell you who has finished and who hasn't, so you can chase them. I
> can't tell you what any couple answered — not to you, not to anyone. If I'd
> build that for you, you'd be right to wonder what I'd tell someone else about
> your couples."*

That converts. A facilitator staking their reputation on a tool wants the tool to
be the kind that refuses.

---

## 4. Acceptance criteria

| # | Criterion |
|---|---|
| 4.1 | The cohort summary endpoint returns only allowlisted categories (Rule 1). Asserted against an explicit field allowlist, so adding a field fails the test. |
| 4.2 | No response contains an attachment style, archetype, axis position, score, or item response — asserted on the serialised payload. |
| 4.3 | No endpoint returns a sorted, ranked, or extreme-valued couple list (Rule 2). |
| 4.4 | Counts below N = 5 render as bands, not exact numbers (Rule 4). |
| 4.5 | No cohort statistic is computed across more than one cohort or across time for a named couple (Rule 3). |
| 4.6 | Per-couple rows in the cohort view carry status only — no numeric or content field, asserted. |
| 4.7 | The facilitator-visible payload is a subset of what both partners can see (Rule 5). |

---

## 5. Note on the instruction

The PM's steer was to err toward showing less rather than being clever about what
is technically anonymous. Rules 1 and 2 are that instruction made mechanical: the
allowlist means we never have to decide whether an aggregate is safe, and the
ranking ban means we never have to reason about how many reports it takes to
identify someone.

Both are checkable in CI, which is the property that matters — a disclosure rule
enforced by the judgement of whoever writes the next endpoint is not a rule.

---

## 6. Re-cut for D3.49 — this rule does not transfer cleanly to therapists

*Added 2026-08-03 when couples therapists became the primary channel and
programmes the secondary one.*

Rules 1–3 survive unchanged and matter more, not less. **Rule 4 and the framing
around it do not, and the reason is worth stating rather than patching.**

### 6.1 The threat model inverts

This document was written against a facilitator: someone who knows a cohort
socially, needs completion data to chase people, and must not learn what any
couple *answered*. §1 argued that the facilitator's side information is enormous,
so k-anonymity fails at any k — hence the allowlist.

**A therapist's side information is not merely large. It is the point.** They sit
with the couple weekly. Anything a summary could tell them about their own
clients, they already know better, from the source, with context we do not have.

So the disclosure risk we designed against is close to zero here — and a
different risk takes its place:

> **We would be creating a written record about a therapist's clients, held on
> our servers, that neither the therapist nor the couple asked us to keep.**

That record is discoverable, breachable, and subject to a duty of confidentiality
that is *theirs* rather than ours. A therapist evaluating us will ask what we
retain about their clients long before they ask what we show them.

### 6.2 What that changes

**Rule 4's N = 5 banding is now almost always active** — a therapist with three
client couples trips it on every statistic — which is a signal the mechanism is
wrong for this channel rather than merely conservative. Bands over three couples
are noise dressed as caution.

**The right answer for the therapist channel is less, not banded.** Per-couple
status only — `not started` / `one partner done` / `ready` / `report generated` —
which is the operational minimum a therapist needs to know whether to expect a
report before Thursday's session. **No aggregate at all.** With three couples an
aggregate is a rounding of three facts they already have.

That is simpler than the cohort rule and strictly safer, and it means:

- Rules 1–3 stand as written and govern the **programme** channel from ~month 6.
- The **therapist** channel gets §6.3, which is a subset, not a variant.

### 6.3 The therapist rule

1. **Per-couple status only.** The four states above. Nothing numeric, nothing
   distributional, nothing aggregated.
2. **No cohort summary is generated at all** for a therapist account.
3. Everything in §2 Rule 1's *never* list continues to apply, unchanged.
4. **Say what we retain, unprompted.** The one thing a therapist will ask that a
   facilitator would not. The honest answer is already true and already strong —
   we hold no session transcripts (`session-retention-wording.md` §3.3), the
   report contains only what each partner said about themselves, and both
   partners hold the identical document.

### 6.4 Why this is the refusals pattern again, and a better version of it

The line in §3 was written for a facilitator: *"if I'd build that for you, you'd
be right to wonder what I'd tell someone else about your couples."*

For a therapist it becomes stronger, because their duty is professional rather
than pastoral:

> *"I can tell you whether a report is ready. I don't build anything that
> aggregates your clients, because a summary of your caseload sitting on my
> server is a liability you didn't agree to and I'd rather not hold."*

That answers the question they were going to ask anyway, in the register they ask
it in — and unlike the facilitator version, the refusal removes a risk that is
**theirs**, not ours.
