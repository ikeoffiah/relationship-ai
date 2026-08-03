# Report page 5 — "Four conversations"

Owner: product/design (`local_81faf803`). Copy deliverable for
`facilitator-report.md` §6. Engineer builds against the selection keys in §1.

The teaching material. A facilitator runs a session from this page, so each
conversation is written to be read aloud, to take about twenty minutes, and to
survive a couple who arrive defensive.

---

## 1. Why these four survive whatever P0.1 returns

**Categorical fields need no threshold. Only continuous axes do.**

The pairing section (§5 of the report spec) compares two positions on two
continuous axes, so it needs a threshold for "differing" — which is why it is
blocked on P0.1's score distribution.

These four are keyed on **categorical self-report**, where "same" and "different"
are decided by equality rather than by a cut point:

| # | Conversation | Selection key | Source |
|---|---|---|---|
| C1 | How you each say a hard thing | `communication_style_self_report` ×2 | 5-item quiz, deterministic count |
| C2 | Whose family is in the room | `family_community_orientation` ×2 | Cultural screen |
| C3 | What faith means here, in practice | `religious_values` ×2 | Cultural screen |
| C4 | What you each think happens next | `relationship_stage`, duration, `cohabiting`, `children_count` | Relationship screen |

None touches the RSQ. **If P0.1 returns no usable model-of-other axis, page 5
ships unchanged** and page 4 is what gets replanned.

Per D3.6a these are also the likely first four sessions of a slot-in kit, so each
stands alone and none depends on the others having happened.

### Rules inherited from the report spec

- **Reversibility (§2.2).** Every sentence must read true with the names swapped.
  QA checks by swapping names in a generated PDF and re-reading.
- **Address the couple**, never one partner. "One of you… the other", never
  "Ada should".
- **Difference is never the problem.** It is the most common outcome and the one
  most likely to be read as a verdict three weeks before a wedding.
- **"Prefer not to say" is honoured.** If either partner declined a field, that
  conversation falls back to its neutral variant and **never** names the
  declining partner or the fact of the decline.

Each block renders as: **the question** · **why you two** · **what a good answer
sounds like** (facilitator note, italic on the page).

---

## 2. C1 — How you each say a hard thing

Selected by comparing both `communication_style_self_report` values.

### C1-a — Same style, both

> **The question.** Think of the last time one of you had something difficult to
> say. Who said it, how did it come out, and what did the other one hear?
>
> **Why you two.** You approach hard conversations in a similar way. That usually
> means you understand each other quickly — and it also means that when the way
> you both do it isn't working, neither of you has a different gear to reach for.
>
> *A good answer sounds like: both of them describing the same event and noticing
> they handled it the same way. Push gently on what happens when that shared
> approach fails — a couple who share a style often have never had to develop a
> second one.*

### C1-b — One tends to approach, one tends to step back

Selected when one partner is `assertive` or `expressive` and the other is
`avoidant` or `passive`. **The most common pattern, and the one most often
misread as a problem.**

> **The question.** When something goes wrong between you, one of you probably
> wants to sort it out now and the other probably needs a bit of time first. Which
> of you is which — and what does the waiting feel like from each side?
>
> **Why you two.** You said different things about how you handle a difficult
> moment. One of you moves toward it; the other needs some room before moving at
> all. Neither is the right way. The trouble only starts when the moving-toward
> reads as pressure and the stepping-back reads as not caring — and both readings
> are usually wrong.
>
> *A good answer sounds like each of them describing what the other's move feels
> like from the inside — not what it means. If it turns into who is at fault, ask
> instead: how long is "a bit of time", and how would you each know it was over?
> A couple who leave with an actual number have got something.*

### C1-c — One works it out by thinking, one by feeling out loud

Selected when one is `analytical` and the other is `expressive`.

> **The question.** When you disagree about something that matters, one of you
> probably reaches for reasons and the other reaches for how it felt. What happens
> in the gap between those?
>
> **Why you two.** You process differently. One of you gets to clarity by working
> the problem; the other gets there by saying it out loud and hearing how it
> lands. Each can experience the other as missing the point — the reasons can feel
> cold, the feeling can feel like it's avoiding the question.
>
> *A good answer sounds like both recognising the other is doing a real thing
> rather than being difficult. Watch for one of them conceding too quickly to end
> the exercise — that is the pattern, not the resolution.*

### C1-d — Different, other combinations

> **The question.** Describe how the other one lets you know something is wrong.
> Not what they say — how you can tell.
>
> **Why you two.** You each said something different about how you handle a hard
> conversation. Most couples never compare notes on this, and most of the damage
> in an argument happens in the gap between what was meant and what was heard.
>
> *A good answer sounds like specifics — a tone, a silence, a particular phrase.
> If it stays abstract, ask for the last actual example.*

---

## 3. C2 — Whose family is in the room

Selected by comparing `family_community_orientation`
(`individual` / `family_oriented` / `community`).

The highest-yield premarital topic that exists and the one most reliably skipped,
because both partners assume their own arrangement is the normal one.

### C2-a — Aligned

> **The question.** A big decision comes up — where to live, how to spend money,
> how to raise a child. Before you tell each other, who else do you tell?
>
> **Why you two.** You described a similar relationship to family and community.
> That usually means fewer arguments about *whether* to involve people — and it
> means the question of what stays between the two of you may never have been
> asked out loud.
>
> *A good answer sounds like them discovering they draw the line in slightly
> different places even while agreeing on the principle. Ask what neither of them
> would tell anyone, and watch whether the two answers match.*

### C2-b — Differing

> **The question.** After a hard week, one of you probably wants to talk it
> through with family, and one of you would rather it stayed between you. Which
> way does each of you lean — and how did you find that out about each other?
>
> **Why you two.** You described different relationships to family and community.
> This is one of the most common differences between two people getting married
> and one of the least discussed, because each of you grew up thinking your
> arrangement was simply how it is done.
>
> *A good answer sounds like each describing what the other's instinct costs them
> — feeling exposed, or feeling shut out. Neither is being disloyal. If it heats
> up, move to the concrete: name one decision that stays between you two, and one
> where involving family is welcome. Specific beats principled here.*

---

## 4. C3 — What faith means here, in practice

Selected by comparing `religious_values`.

Channel-critical, and it must be as good for a secular couple as for a devout
one — the same page ships to both.

### C3-a — Same tradition

> **The question.** You come from the same tradition. Where inside it do you
> actually differ — how often, how strictly, which parts matter most?
>
> **Why you two.** Shared faith is often assumed to be a solved question, so the
> differences inside it go unexamined until something forces them: a wedding, a
> parent, a child.
>
> *A good answer sounds like them finding a genuine difference of practice or
> emphasis. If they insist there is none, ask about a specific occasion — a
> holiday, a family expectation. Specifics find what principles hide.*

### C3-b — Different traditions, or one holds a faith and one does not

> **The question.** Name one thing from the other one's tradition — or from their
> not having one — that you want to understand better. Then ask them about it.
>
> **Why you two.** You described different relationships to faith. Couples who
> talk about this early do well; couples who assume it will resolve itself tend to
> meet it later, at a wedding or a christening or a funeral, with less time.
>
> *A good answer sounds like curiosity rather than negotiation. This is not the
> session to settle how children will be raised — if they go there, let them note
> it and come back. The goal today is that each can state the other's position in
> a way the other recognises.*

### C3-c — Neither holds a religious faith

> **The question.** What do you want your marriage to be *for*, beyond the two of
> you being happy?
>
> **Why you two.** Neither of you named a religious tradition, so the questions a
> tradition would have asked on your behalf are yours to ask. They are still good
> questions.
>
> *A good answer sounds like values named out loud — how they want to treat
> people, what they want a home to be. If it stays vague, ask what they would want
> said about their marriage in twenty years.*

### C3-d — Either partner declined

> **The question.** What do you want your marriage to be *for*, beyond the two of
> you being happy?
>
> **Why you two.** Every couple is answering this, whether or not a tradition is
> answering it for them.
>
> *A good answer: as C3-c.*

**Rule:** C3-d renders whenever either partner selected "Prefer not to say". It
is identical in tone to C3-c, so the page never signals that anyone declined.

---

## 5. C4 — What you each think happens next

Selected by `relationship_stage`, with `cohabiting`, `children_count` and
`relationship_duration_months` adjusting the closing line.

### C4-a — Premarital (`early_dating`, `newlyweds`, `committed`)

> **The question.** Describe an ordinary Wednesday, three years from now. Not the
> wedding — a Wednesday. Who does what, who is in the house, what happened that
> evening?
>
> **Why you two.** Most of a marriage is Wednesdays, and couples preparing for one
> spend almost all their planning on a single Saturday. Two people can agree
> completely about the wedding and hold quite different pictures of the ordinary
> week after it.
>
> *A good answer sounds like detail — who cooks, who is working late, whether
> anyone else is in the house. Differences here are useful and easy to talk about
> now; they are expensive to discover later. Watch for one of them describing
> their parents' Wednesday without noticing.*

**Closing line, appended by context:**

- *cohabiting* — "You already share a home, so some of this is testable. Which
  parts of that Wednesday are already true?"
- *children present* — "Protected time for the two of you is the thing that
  quietly erodes first. Where is it on that Wednesday?"
- *duration < 18 months* — "You are early enough that these patterns are still
  forming. Noticing them now is a real head start."

### C4-b — Established (`long_term`)

> **The question.** What is something you used to argue about and don't any more?
> How did that happen?
>
> **Why you two.** You have been together long enough to have solved things. Most
> couples cannot say how they did it, which means they cannot do it deliberately
> the next time.
>
> *A good answer sounds like a mechanism, not a truce — something one of them
> started doing, or stopped. If the answer is "we just stopped talking about it",
> that is worth staying with.*

### C4-c — Strained (`crisis`, `post_infidelity`, `separation_considering`)

**Not for the premarital pack.** Included because the field allows these values
and the generator must not fall through to C4-a, which would ask a couple in
crisis to describe a happy Wednesday.

> **The question.** What is one thing that is still working?
>
> **Why you two.** When a relationship is under strain the hard parts take up all
> the room, and what is still standing gets no attention at all — even though it
> is what any repair would be built on.
>
> *A good answer can be very small. If they cannot find one, that is information;
> do not push, and do not fill the silence for them.*

**If either partner's stage is in this group, the report should not be generated
for a premarital cohort at all.** Route to the facilitator's cohort view as "not
ready" rather than producing a document written for a different situation.

---

## 6. Selection order and fallbacks

1. Compute C1–C4 independently. No conversation depends on another.
2. Any missing field → that conversation's neutral variant (C1-d, C2-b, C3-d,
   C4-a). **Never omit a conversation** — a page with three is a page that tells
   the couple something was withheld.
3. "Prefer not to say" is a missing field for selection purposes and is never
   surfaced.
4. C4-c suppresses report generation for premarital cohorts (§5).

## 7. Acceptance criteria

| # | Criterion |
|---|---|
| 7.1 | Page 5 always renders exactly four conversations. |
| 7.2 | No variant selection reads `attachment_style`, an axis position, or any RSQ item — asserted. Page 5 is independent of P0.1. |
| 7.3 | "Prefer not to say" on either partner never produces text that differs visibly from the both-declined-nothing case (C3-d ≡ C3-c in tone). |
| 7.4 | Name-swap test: every sentence reads true with the two names exchanged. Manual, QA-owned. |
| 7.5 | A couple with any partner in `crisis` / `post_infidelity` / `separation_considering` produces no premarital report. |
| 7.6 | No conversation contains advice addressed to one partner about the other. |
