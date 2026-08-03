# Report page 4 — "Where you meet"

Owner: product/design (`local_81faf803`). Copy for `facilitator-report.md` §5.
Unblocked by D3.23. Built by: engineer.

**It is ten blocks, not nine.** See §2 — one cell of the 3×3 holds two
meaningfully different couples and must not share copy.

---

## 1. Selection

Two axes, derived per D3.23 from the four prototype scores:

```
model_of_self  = (secure + dismissing) − (fearful + preoccupied)
model_of_other = (secure + preoccupied) − (fearful + dismissing)
```

Verified against the four canonical prototypes: every one lands in its correct
quadrant, and a fully neutral responder lands on exactly `(0.00, 0.00)`.

**Threshold is zero, and it is principled rather than chosen.** Positive vs
negative model-of-self / model-of-other *is* the four-category model's own
boundary, and it is empirically our scorer's neutral point. A partner is on one
side or the other; the pair is aligned or differing.

| Axis | Reader-facing name | Pair states |
|---|---|---|
| `model_of_other` | Closeness | `both_open` · `both_guarded` · `differing` |
| `model_of_self` | Reassurance | `both_settle` · `both_need_signal` · `differing` |

### Two engineering constraints

**Never compare a self value to an other value.** The subscales have different
item counts and reversals, so the axes are not on a common scale — SECURE scores
+1.90 on self and +6.10 on other. Only ever compare **the two partners on the
same axis**. Do not render both axes on one chart.

**Never print a number, and never plot the positions.** Positions select copy;
they do not appear, as digits *or as dots*. A printed number invites couples to
compare scores; a 2×2 with two dots on it is the same failure with better
graphic design — two numbers plus a third the couple invents, the distance
between them. **D3.42**, and it is the version most likely to be proposed by
someone who has read and agreed with the no-numbers rule.

---

## 2. Why ten blocks

Eight of the nine cells are unambiguous: with one axis aligned, both partners
share that position, so there is one couple to describe.

**The differing × differing cell holds two different couples**, because "both
axes differ" does not say who holds which:

| | |
|---|---|
| **9a — aligned within person** | One partner is open *and* settles; the other is guarded *and* needs reassurance |
| **9b — crossed** | One partner is open *and* needs reassurance; the other is guarded *and* settles |

9b is the classic reach-and-withdraw mismatch; 9a is a steadier-and-steadied
pairing. Sharing copy between them would produce a paragraph true of neither.

**Selection rule:** within the differing × differing cell, if the partner who is
`open` is also the one who `settles`, render 9a; otherwise 9b.

---

## 3. The blocks

Each renders four parts: **what this looks like** · **the strength in it** ·
**where it costs you** · **what usually helps**.

Every sentence obeys §2.2 reversibility — true with the names swapped. QA checks
by swapping names in a generated PDF and re-reading.

### 1 · both_open × both_settle

**What this looks like.** You both move toward each other easily, and neither of
you stays rattled for long. Disagreements tend to end the day they start.

**The strength in it.** You recover quickly, and neither of you has to manage the
other's alarm. That is genuinely uncommon.

**Where it costs you.** You may never have built a repair habit, because you have
not needed one. The first thing that does *not* resolve in a day can be
disproportionately frightening — not because it is worse, but because you have no
practice.

**What usually helps.** Decide now what you would do if something stayed
unresolved for a week. Not because it is likely; because deciding it while calm
is free, and deciding it in the moment is not.

### 2 · both_open × both_need_signal

**What this looks like.** You both reach for each other, and you both want to
know things are alright. Little goes unsaid between you.

**The strength in it.** You stay current. Neither of you is left guessing, and
things rarely go quiet long enough to fester.

**Where it costs you.** When you are both activated, nobody in the room is calm.
A small rupture can get loud quickly — not because either of you is escalating on
purpose, but because you are both reaching at once.

**What usually helps.** Agree a phrase either of you can use to pause, in
advance. The point is that stopping is not the same as leaving — and in a hard
moment, that difference has to be pre-agreed rather than argued.

### 3 · both_open × differing reassurance

**What this looks like.** You both move toward each other, but afterwards one of
you is settled while the other is still checking.

**The strength in it.** One of you can be the steady one. Not every couple has
somebody who can do that.

**Where it costs you.** The one who settles quickly tends to think it is over.
The other is often still in it an hour later. *"We sorted that out"* and *"we
never finished"* can both be honestly said about the same conversation.

**What usually helps.** End hard conversations on purpose rather than drifting
out of them. One sentence — *are we done, or do you need more?* — costs nothing
and catches most of it.

### 4 · both_guarded × both_settle

**What this looks like.** You are both fairly self-contained, and neither of you
rattles easily. There is little drama between you.

**The strength in it.** Real respect for each other's independence. Neither of
you manufactures a crisis to get attention, and you both have room to be
yourselves.

**Where it costs you.** Distance can grow without either of you raising it,
because neither of you is the type to. Nothing sounds an alarm — the drift is
quiet, and by the time it is obvious it has usually been there a while.

**What usually helps.** A standing time to check in that does not depend on
either of you feeling the need. Put it in the diary. This pairing does not need a
rescue mechanism; it needs a routine one.

### 5 · both_guarded × both_need_signal

**What this looks like.** You both want to know you matter to each other, and you
both find it hard to ask.

**The strength in it.** Neither of you underestimates what it costs to reach out.
So when either of you does, you both know exactly what it meant.

**Where it costs you.** You can both be waiting for the same thing at the same
time. A silence that is caution on one side reads as rejection on the other — and
you can sit in the same room drawing opposite conclusions from it.

**What usually helps.** Make reaching out smaller, so it costs less. Not a
conversation — a message, a hand, some specific and unremarkable gesture you both
agree counts. The aim is to lower the price of asking, not to require more
courage from either of you.

### 6 · both_guarded × differing reassurance

**What this looks like.** Neither of you leads with what you need, and one of you
needs more reassurance than the other.

**The strength in it.** Neither of you crowds the other. There is a lot of room
in this, and for two people who value that, it is worth something.

**Where it costs you.** The one who needs more signal is the least likely to ask
for it, and the other is not the type to offer it unprompted. So the need is real
and the request never quite happens.

**What usually helps.** The one of you who needs less reassurance is the only one
who can start this, because here an unprompted offer is the only kind that ever
arrives. That is not a burden — it is simply which of you is holding the easier
end.

### 7 · differing closeness × both_settle

**What this looks like.** One of you moves toward connection readily; the other
takes longer to open. Neither of you stays rattled for long.

**The strength in it.** Complementary pace. One of you draws the other out; the
other gives the pair some ballast. Because neither of you escalates easily, this
difference has room to be worked out rather than fought over.

**Where it costs you.** Reserve can read as disinterest, and warmth can read as
pressure. Both readings are usually wrong, and both are very easy to make.

**What usually helps.** Say the reason out loud, once, while things are calm.
*I go quiet because I am thinking, not because I am leaving.* *I come toward you
because I want to, not because I need you to respond.* Said once, it gets
remembered in the moments that matter.

### 8 · differing closeness × both_need_signal

**What this looks like.** When something is wrong, one of you moves toward the
other and one of you needs space first — and you both want reassurance that
things are alright.

**The strength in it.** Neither of you is indifferent. You both care what the
other thinks, which is the raw material repair is made of. The difficulty here is
timing, not caring.

**Where it costs you.** This is the pattern that escalates fastest. One reaches,
one steps back; the reaching gets more urgent, the stepping back goes further.
And because you both need reassurance, neither of you is getting any while it
happens.

**What usually helps.** Agree a number. How long is the space, and who comes
back. Not *"we'll talk later"* — an actual time. The one who steps back returns
at it; the one who reaches waits until it. For a couple who work this way, this
is the single most useful agreement available.

### 9a · differing both — aligned within person

**What this looks like.** One of you finds closeness fairly easy and does not
stay rattled; the other is more careful about closeness and needs more
reassurance.

**The strength in it.** One of you has capacity to spare, and that is not
nothing. This works well as long as it stays a pairing rather than hardening into
a role.

**Where it costs you.** It can quietly become one of you doing the emotional
steadying and the other being steadied. Unremarkable in a good week, heavy over
years — and the person carrying it often does not say so, because it does not
feel like a complaint.

**What usually helps.** Check the balance out loud a few times a year. Not
whether you are both happy — whether it is always the same one of you doing the
reaching. It is also worth finding things where the other one leads, so the
pattern stays something you do rather than something you are.

### 9b · differing both — crossed

**What this looks like.** One of you moves toward connection and wants to know
things are alright; the other is more self-contained and does not need much
reassurance.

**The strength in it.** You balance each other's extremes. One of you keeps
things from going unsaid; the other keeps them from being over-processed.

**Where it costs you.** This is the combination that most easily reads as a
mismatch in caring. Needing reassurance can look like too much; not needing it
can look like not enough. Neither is true, and both are extremely easy to
believe.

**What usually helps.** Separate the request from the reading. When one of you
asks for reassurance, it is a request and not an accusation. When the other does
not offer it unprompted, it is a habit and not a verdict. Naming those two things
once, while calm, prevents most of what goes wrong here.

---

## 4. What page 8 must say about this page

Per D3.23's stated limits — and per the flat column of D3.31, where a limitation
is stated plainly rather than dressed as a choice:

> The two dimensions on page 4 — how readily each of you moves toward closeness,
> and how much reassurance each of you looks for — are **derived from the four
> prototype scores rather than measured directly**. The two-dimensional model
> they rest on is the one the questionnaire was designed around (Griffin &
> Bartholomew, *Models of the Self and Other: Fundamental Dimensions Underlying
> Measures of Adult Attachment*). The particular combination used here follows
> from that model; it is not a published formula.
>
> The positions are **relative, not normed** — they place the two of you next to
> each other, not against any wider population. The point at which we call two
> people "different" is a principled choice rather than a measured one.

**Do not soften this.** A professional reader who sees *derived, relative, not
normed, threshold chosen* trusts the rest of the document more, not less — and
every one of those four words is checkable, which is exactly why volunteering
them is worth more than they cost.

## 5. Acceptance criteria

| # | Criterion |
|---|---|
| P4.1 | Exactly one block renders. Ten cases; no couple falls through. |
| P4.2 | The differing × differing cell selects 9a or 9b by the §2 rule. |
| P4.3 | No numeric value appears anywhere on page 4. |
| P4.4 | Self and other positions are never compared to each other, and never charted together. |
| P4.5 | Name-swap test passes for all ten blocks. Manual, QA-owned. |
| P4.6 | No block contains advice addressed to one partner about the other. |
| P4.7 | Every block has a non-empty "strength" that is a real strength, not consolation. Reviewed manually. |
| P4.8 | Page 8 carries the §4 wording verbatim. |
