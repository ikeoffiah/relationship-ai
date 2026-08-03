# Writing the refusals

Owner: product/design (`local_81faf803`). A copy pattern, and the line where it
stops working.

Most of this product's real differentiators are things it refuses to do: no
streak, no partner profile, no compatibility score, no risk flags, no
transcripts, no facilitator-only annex, no cohort rankings, no gate on the
crisis path. Nearly all of them are currently written somewhere as an
**absence** — a bullet under "what you won't get", or a caveat.

An absence asks the reader to notice something missing. A refusal, written
properly, makes the reader want the thing we refused.

---

## 1. The construction

> **Take a place where we refuse to do something, and write it so the refusal
> demonstrates the property the buyer wants — rather than apologising for a
> missing feature.**

Three moves, in order:

1. **Name what we could have built**, so the refusal reads as a choice rather
   than a gap. "We could have given you a compatibility number."
2. **Say what it would have cost the reader**, not what it would have cost us.
   The reader has to be the one who loses.
3. **Leave the reader on our side of the refusal** — ideally wanting it applied
   to them, or glad it will be applied on their behalf.

The version that worked, from `cohort-disclosure-rule.md` §3:

> *"I can tell you who has finished and who hasn't, so you can chase them. I
> can't tell you what any couple answered — not to you, not to anyone. If I'd
> build that for you, you'd be right to wonder what I'd tell someone else about
> your couples."*

The last clause does the work. It moves the facilitator from *resenting a
missing feature* to *wanting the boundary*, because the same refusal now
protects them.

---

## 2. Where it stops working — the important half

**The construction is only honest when the absence is a choice.**

A limitation dressed as a principled refusal is worse than a plainly stated
limitation, because a professional reader can tell the difference and will
downgrade everything else we said.

| This is a refusal — use the pattern | This is a limitation — state it plainly |
|---|---|
| No compatibility score | The instrument is not psychometrically validated |
| No partner profile shown to the partner | It is self-report at one point in time |
| No risk flags to the facilitator | We have no norming data |
| No transcripts retained | The report can be wrong |
| No facilitator-only annex | We have not run this with real cohorts yet |
| No cohort rankings | |
| No gate on the crisis path | |

The right-hand column stays exactly as `facilitator-report.md` §7 has it: flat,
unhedged, volunteered. **"We could have called this validated" is not available
to us**, because we could not have — not honestly. Reaching for the pattern there
would be the same failure mode as the "validated" claim the audit struck, wearing
better clothes.

Rule of thumb: if the sentence would still be true had we tried harder, it is a
limitation. Only refuse things we could have shipped.

---

## 3. Applied — changes made

**`facilitator-report.md` page 1, the compatibility score.** Was a caveat ("It is
not a compatibility score and not a prediction"). Now names the incumbent
practice, says what the number would have cost *the couple*, and lands on the
reason the session is worth having. Read by both partners and the facilitator, so
it does triple duty.

**`facilitator-report.md` page 8, risk flags.** Previously refused only in the
spec's internal §9 table — invisible to anyone outside engineering, which is the
wrong place for our best material. Now stated on the page the facilitator reads,
including the reciprocal turn: *"not something we would want pointed at us
either."* This is the strongest refusal in the product and it was not being said
out loud to the one audience that would value it most.

**Already correct, no change:**

- `session-retention-wording.md` §3.3 — *"We would rather not hold it."* Names
  the cost to the user (discoverable in a separation, re-readable by a partner
  re-litigating an argument) and lands on a choice.
- `counsellor-paywall-copy.md` §3 — *"If you need help right now, you don't need
  to pay for it."* Already the construction, at the moment it matters most. It
  should not be made cleverer; at that moment plainness *is* the proof.

---

## 4. Two still written as absences, for whoever owns them

Both are marketing's files, so these are suggestions rather than edits.

**The streak** (`marketing-copy.md` §1, under "WHAT YOU WON'T GET"). Currently a
bullet in a list of negatives. It is one of the clearest choices this team made,
and the reasoning already exists in `daily_ritual_screen.dart`:

> Most apps like this give you a streak. We built one, then took it out. A
> number counting how many days in a row you have both opened an app is not a
> measure of a marriage, and the week one of you is ill it will tell you that you
> failed. We would rather show you what you did than what you broke.

**Nothing gated on the crisis path** (§8 facilitator page). Currently a
four-word bullet. It is the single most checkable promise we make and it is
being said in passing, in a list, on the page written for the audience most
likely to care whether it is true.

---

## 5. One caution

This pattern is load-bearing precisely because the refusals are real and
enforced — the boundary import test, the entitlement allowlist, the disclosure
rule, the D7 static assertion. **Every refusal written this way should have a
test behind it**, or it is a claim in the same category as the four the audit
struck.

Before using the construction on something new, check it against D3.16: has
someone used it in the running app, or does a passing test exercise it? A
refusal is a capability claim in the negative, and it fails the same way.
