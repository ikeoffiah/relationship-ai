# Spec: the facilitator report

Owner: product/design (`local_81faf803`). Built by: engineer (`local_b69883b7`).
Execution-plan **P0.3**. Written 2026-08-03.

This is the artefact sold at $39/couple (Premarital Pack) and bundled into every
cohort. It is the thing a facilitator teaches from, and — at zero
downloads — the only tangible proof this product exists. It has to survive a
professional reader who knows what an attachment measure is.

---

## 1. What it is

**One PDF per couple. Eight pages. Identical for everyone who receives it.**

Not a compatibility score. Not a clinical assessment. Not a prediction about a
marriage. It is a structured reading of what two people each said about
themselves, arranged so a third person can run a ninety-minute conversation from
it.

The design target is Prepare/Enrich's facilitator report — the incumbent in this
channel, priced $35–65 — with one difference we can actually defend: theirs ends
when the workbook does; ours is the on-ramp to an app the couple keeps.

---

## 2. The boundary rule

This is the part to get right, and it is the reason this spec leads with it.

`boundary.py` exists to stop an **inferred model of one partner reaching the
other**, because — per `docs/outcome-loop.md` §2 — that artefact is a
manipulation manual. A report that put one partner's behavioural profile in the
other's hands would be exactly the thing the codebase was built to prevent,
wearing a PDF's clothes. `go-to-market.md` §5.5 already prohibits selling it.

The premarital report is **not** that, and the distinction is precise:

| Property | Eligible for the report | Never in the report |
|---|---|---|
| Source | **Self-report** — the person said it about themselves | **Inferred** from behaviour |
| Symmetry | Both partners answered the same instrument | One partner observed, the other not |
| Consent | Both consented at the point of answering | Ongoing, ambient, unreviewed |
| Time | A single, dated sitting | Continuous accumulation |
| Visibility | Both partners read the identical document | One party holds what the other cannot see |

So the rule, stated as the engineer will implement it:

> **The report generator reads `UserProfile` and nothing else.**

It must not import from — directly or transitively — `personalization.behaviour`,
`personalization.connection`, `apps.insights`, `apps.chat`, `apps.sessions`, or
`apps.memory`. No `BehaviourProfile` signals, no connection score, no
`perception_gap`, no `recurring_theme`, no session content, no message content,
no check-in scores, no `AssistNudge`.

**Test it the way `boundary.py` is tested — as an import assertion, not a
convention.** A unit test that imports the report module and asserts none of
those modules appear in its transitive imports, plus an output assertion that no
`behaviour.SIGNALS` key appears in any rendered string. That test is the product
promise, same as the existing one.

### 2.1 Symmetry — there is exactly one document

**Every recipient gets byte-identical content.** Both partners, the facilitator,
and the programme all read the same eight pages.

There is no facilitator-only annex, no "clinician notes", no leader's edition.
The moment a version exists that the couple cannot see, we have built the
asymmetric surface — and it leaks anyway the first time a facilitator quotes it
in the room with the couple sitting there.

If a facilitator asks for a leader's guide, that is a **separate, generic
document about how to run the session** (`facilitator-session-guide.md`).
It contains no couple's
data. It ships as one file for all cohorts, not one per couple.

### 2.2 Reversibility — the editorial rule for every joint sentence

Every sentence in the pairing section (§5) must be **true and readable when the
two names are swapped**. If a line only works in one direction, it is a claim
about one partner delivered to the other, and it does not ship.

- ✅ "One of you settles quickly after a disagreement; the other needs more
  signal that things are alright again."
- ❌ "Chidi needs constant reassurance, so give him space to express it."

The second is a user manual for a person. It is the exact failure mode.

---

## 3. Preconditions — hard gates on generation

The report **must not generate** unless all four hold. Each is a refusal, not a
degradation.

1. **Both partners have completed onboarding.** `onboarding_completed == True`
   on both profiles. A one-sided report is not a couple report and must never be
   produced — it would also hand one partner a document about a relationship the
   other has not consented into.
2. **Both partners have a scored attachment placement.** `attachment_style` is
   falsy when there is too little to say. See §3.1.
3. ~~P0.1 has shipped~~ — **done.** Model-of-other scored, item 26 corrected,
   2×2 placement restored. See §3.2.
4. **Both partners have accepted the report consent** (§8.1).

Failing any of these, the facilitator's cohort view shows the couple as
**"Not ready — waiting on [what]"**, naming which of the four is missing without
revealing either partner's answers.

### 3.1 `unknown` must be a real outcome

**Shipped.** `calculate_rsq_attachment_style({})` previously returned
`('secure', {all four: 3.0})` — a four-way tie resolved by dict ordering, so
anyone who submitted nothing was silently labelled securely attached. For a free
app that is a bug; for a paid assessment read by a professional it is the worst
failure available to us.

It now returns **`None`** on a tie, plus a `MIN_ITEMS_TO_SCORE` floor.

**Note the shipped choice differs from what this spec originally asked for, and
the shipped one is better.** I specified the string `"unknown"`; the engineer
returned `None` because every consumer already guards with a falsy check —
`(profile.attachment_style or "")` in `portrait.py` and `engagement/services.py`,
`if getattr(...)` in `chat/assist.py`. `None` does the right thing in all three
with no change to any of them, while `"unknown"` is truthy and would have
injected `attachment style: unknown` into a prompt.

The report refuses to generate under precondition 2 either way.

### 3.2 Why P0.1 is load-bearing for this artefact

The pairing section (§5) is generated from **two axes**, not from sixteen
hand-written style pairs. Those axes are model-of-self and model-of-other — which
is what Bartholomew's 2×2 actually is, and what P0.1 restores by scoring items
7, 14, 17, 26, 27 and 30.

Without model-of-other there is one usable axis, the pairing section collapses to
a label comparison, and the methodology page (§7) cannot honestly describe a 2×2.
**The gate did not fire — P0.1 shipped and the axes are verified** against the
four canonical prototypes, with a neutral responder landing on exactly
`(0.00, 0.00)`. See `report-pairing-blocks.md` §1.

---

## 4. The document

Eight pages. Page count is a design constraint, not an aspiration — a facilitator
will not teach from twenty.

| # | Page | Source |
|---|---|---|
| 0 | Cover | Names, programme name, facilitator, date |
| 1 | How to read this | Static |
| 2 | Partner A | `build_portrait(profile_a)` |
| 3 | Partner B | `build_portrait(profile_b)` |
| 4 | Where you meet | §5, generated from both placements |
| 5 | Four conversations | §6, selected by axis pattern |
| 6 | What you each said matters | Cultural/values fields, side by side |
| 7 | Notes | Blank, ruled, for the couple to write in |
| 8 | How this was made | §7, methodology and limits |

### Page 0 — Cover

Couple's first names. Programme name and facilitator name — cheap to
build and it converts, because a facilitator hands out their own work rather
than ours. Date of assessment.
Bliss wordmark, small, at the foot.

**No score, no headline label, no archetype on the cover.** A couple should not
learn their result from a cover sheet before anyone has framed it.

### Page 1 — How to read this

Five short paragraphs, static text, and the most important page in the document.
It sets what the reader is allowed to conclude.

*Rewritten 2026-08-03 in the coherence pass, once pages 4 and 5 had words. The
earlier version described only the attachment half and never mentioned the
conversations — so it framed about half of what it was framing.*

- **What this is.** Two things. A reading of how each of you tends to approach
  closeness — how you seek it, how you handle distance, what happens when
  something goes wrong. And then four conversations to have about the rest: how
  you each say a hard thing, whose family is in the room, what faith means here
  in practice, and what you each think happens next. **The second half is the
  point.** The first half is only there to make the conversations better ones.
- **Everyone reading this has the same pages.** Both of you, and your
  facilitator. There is no version with extra notes in it and no summary that
  goes to anyone else.
- **There is no score in here, and that is deliberate.** We could have given you
  a compatibility number — the tools that do are the ones you have probably
  heard of. But a single number, three weeks before a wedding, either reassures
  you about something it cannot see or gives you a reason to doubt something it
  cannot see either. Every combination on these pages includes couples who do
  well and couples who struggle. **The difference is what they do, not what they
  are** — which is the only reason a conversation like this is worth having.
- **There are no bad results — but there are costs, and we name them.** Every
  pattern in here comes with something it gives you and something it costs you.
  When you reach the part that names a cost, it is not a verdict. It is the half
  most reports leave out, because it is the less pleasant half to read.
- **It can be wrong.** You are the authority on you — and the two of you are the
  authority on the two of you. The pages about how you fit together are a
  reading, not a finding. If something does not fit, say so out loud in the
  session: that disagreement is more useful than a correct label would have been.

### Pages 2 and 3 — the two portraits

`build_portrait()` already produces exactly the right shape and its design rule —
"it must beat the horoscope test" — is the right one. Reuse it verbatim; do not
write parallel content.

Rendered per partner: archetype, headline, summary, what helps, what trips you
up, growth edge, likely friction (bulleted), communication note, context note.

**Both partners' pages are in both partners' copies.** That follows from §2.1 and
is normal for this genre — Prepare/Enrich does the same. What makes it safe is
that every line traces to something that person said about themselves.

One addition to the existing portrait payload, for the professional reader:
a small, quiet line at the foot of each page — *"Based on 27 questions you
answered about yourself on 4 March 2026."* Dated self-report, stated plainly, is
what separates an assessment from a horoscope.

**27, not 22** — the portrait's `communication_note` comes from the 5-item
communication quiz, so a footer citing only the attachment items understates its
own source. The count must match what actually fed the page; if the P1 item cut
changes it, this line changes with it. A footer that is casually wrong about its
own provenance undoes the credibility it exists to buy.

### Page 4 — "Where you meet"

See §5. This is the page the facilitator teaches from and the page most likely to
go wrong.

### Page 5 — "Four conversations"

See §6. The teaching material.

### Page 6 — "What you each said matters"

Two columns, side by side, drawn from the cultural/values screen: cultural
background, religious values, direct/indirect communication preference,
individual vs family-community orientation. Plus relationship stage, duration,
cohabiting, children.

No interpretation, no scoring — just both answers next to each other. In
premarital work, family-community orientation and religious values are among the
highest-yield discussion topics there are, and mismatches surface here without
anyone having to be told they are a mismatch.

Where the two answers differ, mark the row with a small neutral glyph and one
line: *"Worth talking about — different is common and workable, unexamined is
the problem."*

### Page 7 — Notes

Blank, ruled, headed *"What we want to remember from this conversation."*

Sounds trivial. It is the page that makes a printed artefact worth printing, it
is why facilitators keep paper handouts, and it is free.

### Page 8 — How this was made

See §7. This page is the credibility surface for the professional reader and the
main reason this report can be sold into a channel that already has
Prepare/Enrich.

---

## 5. The pairing section — construction

**Generated from two axes, not sixteen pair-blobs.** Less content to write, more
defensible, and it degrades honestly.

After P0.1, each partner has a position on:

- **Closeness** (model-of-other) — how readily they move toward connection
- **Reassurance** (model-of-self) — how much signal they need that things are alright

For each axis, classify the *pair* into one of three states by comparing the two
positions against a documented threshold:

| State | Meaning |
|---|---|
| `aligned_high` | Both partners sit toward the same end |
| `aligned_low` | Both sit toward the other end |
| `differing` | The two sit on opposite sides of the midpoint |

That is 3 × 3 = 9 combinations, each rendering a short block:

1. **What this looks like day to day** — two or three sentences, reversible.
2. **The strength in it** — every combination gets one, and it must be genuine,
   not consolation. Two guarded partners genuinely do give each other room; two
   reassurance-seeking partners genuinely do stay current with each other.
3. **Where it costs you** — named plainly. The report is worthless if every
   outcome is flattering.
4. **What usually helps** — behavioural, specific, addressed to *both*.

### Rules for this section

- **Reversibility (§2.2) applies to every sentence.** This is the acceptance
  test for the copy, and QA should check it by literally swapping the names in a
  generated PDF and re-reading.
- **Address the couple, never one partner.** "You two", "one of you… the other",
  "between you". Never "Ada should…".
- **No advice that positions one partner as the other's project.** Nothing of
  the form "here is how to handle him."
- **`differing` is never framed as a problem.** It is the most common outcome and
  the one most likely to be read as a verdict on a wedding. Lead with what the
  difference gives them.
- **No numbers on this page.** Axis positions drive selection; they are never
  printed. A printed number invites a couple to compare scores, which is the
  compatibility-score failure mode arriving through the back door.

---

## 6. "Four conversations"

Four prompts, selected by the axis pattern from §5, each with: the question, why
it is being asked of *this* couple, and a note to the facilitator on what a good
answer sounds like.

This is the page that makes the artefact *teachable*, and teachability is what a
facilitator is buying. A report they read is a document; a report they can run a
session from is a tool they use again next cohort — and the next cohort is the
whole business model.

Content: I will write the nine axis-pattern variants as a follow-up to this spec
(§10), since they are copy rather than structure and the engineer can build
against the shape before the words are final. Placeholder strings are acceptable
in the first build.

---

## 7. Methodology and limits

One page, plain, unhedged. Written for the reader who will judge us on it.

Must state:

- **The instruments — all three of them.** The earlier draft named only the
  attachment questionnaire, which accounts for pages 2–4. Pages 5 and 6 come from
  elsewhere, and a professional asking *"where does the family question come
  from?"* must find an answer here. All three are self-report and each partner
  answered separately:

  | Source | Feeds |
  |---|---|
  | A 22-item questionnaire adapted from the Relationship Scales Questionnaire (Griffin & Bartholomew) | Pages 2, 3, 4 |
  | A 5-item communication-style questionnaire | Pages 2, 3, and conversation 1 |
  | Background and context questions each partner answered about themselves | Page 6, and conversations 2, 3 and 4 |

- **The adaptation, named as an adaptation.** Our subscales are not the published
  Griffin & Bartholomew scoring. Say that. A professional who recognises the
  items will notice, and volunteering it converts a discovered weakness into
  demonstrated candour. Anything else is a discovered misrepresentation.
- **How page 4's two dimensions were arrived at.** Carry the wording from
  `report-pairing-blocks.md` §4 verbatim — derived rather than measured, no
  published formula, relative rather than normed, threshold chosen rather than
  measured. Four checkable admissions, and they are load-bearing: they are what
  buys credibility for everything else on this page.
- **What it does not measure.** Not conflict, not commitment, not sexual
  compatibility, not finances, not violence, not mental health. **And not the
  topics page 5 raises** — the conversations about family, faith and expectations
  are prompts drawn from what each partner said, not assessments of agreement on
  those subjects. We are not scoring anyone's compatibility of belief.
- **Self-report at one point in time**, subject to how each person felt that day.
- **Not a clinical instrument** and not a substitute for assessment by a licensed
  professional; not diagnostic; not predictive of marital outcome.
- **What we do with the answers** — one line, and a pointer to the privacy page.
- **What we never do:** *"Neither partner is ever shown a profile of the other
  derived from their private activity in the app. The report contains only what
  each of you said about yourself, and you both have this same document."*
- **What we will not send the facilitator**, stated on the page the facilitator
  reads: *"There is no version of this report that you cannot see, and no
  separate note to your facilitator. We are also not going to flag couples to
  them as needing attention — a system that quietly tells a third party you look
  like a concern, on the strength of a questionnaire you answered about yourself,
  is not something we would want pointed at us either. If something in here
  worries you, it goes to you."*

That last line is the sentence that sells to a clinician, and it is true, and it
is enforced by a test. This is where the boundary earns revenue rather than just
being ethical — and it belongs in the professional register per D5.

**Honesty requirement:** if P0.1 lands without validation work, this page must
not imply validation we have not done. "Adapted from" and "not clinically
validated in this form" are both fine to write and are survivable. A claim of
psychometric validity we cannot support is not.

---

## 8. Generation and delivery

### 8.1 Consent

At the point of purchase/redemption, each partner accepts one screen:

> *"Your report is shared. Your answers become a report that you, [partner], and
> your facilitator [name] all receive — the same document for everyone. It
> contains what you said about yourself in the questionnaire. It never contains
> anything from your private sessions or chats."*

Explicit, per-partner, recorded through the existing consent app, revocable
before generation. Both required (precondition 4). This is also the sentence that
makes the artefact defensible if it is ever challenged.

### 8.2 Cohort redemption pairs the couple directly — keep the email invite off the money path

**A cohort code redeems for a couple, not a person.** The facilitator issues one
code per couple; the first partner redeems and is paired, the second redeems the
same code and lands in the same relationship.

Rationale: the report requires both partners (precondition 1), so if pairing
depends on the email-invite loop, then the deliverable we sold depends on the
weakest funnel in the product (`product-assessment.md` §2.6). Pairing at
redemption removes it from the critical path entirely and means the P1 share-sheet
work does not block P0 revenue.

### 8.3 Onboarding must survive interruption — this blocks the artefact

`OnboardingViewModel` holds every answer **in memory** and POSTs once, at the
end, via `submitOnboarding()`. There is no incremental save. A partner
interrupted at item 25 of 30 loses all forty answers and restarts from zero.

For a free app that is friction. For a $39 artefact that **cannot be generated
unless both partners finish**, it is the most likely way a paid cohort produces
no deliverable — and the facilitator, not the couple, is the one who will report
it.

**Required for P0:** persist answers as they are given (local storage is
sufficient; a draft endpoint is better) and resume where the user left off. This
is small and it is on the money path.

### 8.4 Rendering

Server-side HTML → PDF (WeasyPrint or equivalent). A4 **and** US Letter — a
report that prints wrong is a report a facilitator stops handing out. Under D3.0
this matters more, not less: A4 is the standard nearly everywhere outside North
America, so a Letter-only PDF prints badly for most of a global channel.

**Print constraints — these come from how the artefact is actually used.** A
facilitator will photocopy this, and the copy is what most couples get:

- **Sans-serif body.** The serif-for-credibility instinct is convention, not
  evidence; sans-serif is better supported for low-vision and elderly readers,
  and facilitators in this channel are frequently in their sixties.
- **No tint above 10%.** Above that, comprehension measurably drops after
  photocopying — which rules out the shaded callout boxes this document would
  otherwise want.
- **No hairlines below 0.5pt.** A 0.25pt rule does not reproduce on an office
  laser printer, so table borders and dividers simply vanish.
- **No colour-dependent meaning**, already required above, and doubly so once
  greyscale copying is assumed rather than tolerated. Print-safe: no dark backgrounds, no colour-dependent meaning,
≥11pt body. Must be legible photocopied in greyscale, because it will be.

Delivered as: facilitator download from the cohort view; both partners get a link
in-app and by email. Regenerating after either partner retakes the questionnaire
produces a new dated version; old versions are not silently overwritten.

### 8.5 The cohort view

Who has completed, who has not, **without any couple's
answers**. Statuses: `not started` / `one partner done` / `ready` / `report
generated`. No scores, no styles, no labels. The facilitator sees completion, not
content — and that constraint is itself a selling point to say out loud on a call.

---

## 9. Deliberately absent

Each of these will be asked for. Each is refused, with the reason, so the
refusal survives the person who wrote it.

| Not building | Why |
|---|---|
| **A compatibility score or percentage** | Prepare/Enrich prints percentages. We will not. A single number from a 22-item self-report, handed to a couple weeks before a wedding, either falsely reassures or hands them a reason to call it off. It is also the first thing a professional reader would distrust. |
| **Any facilitator-only content** | §2.1. Creates the asymmetric surface and leaks the moment it is quoted aloud. |
| **Behavioural data of any kind** | §2. Score, insights, check-ins, message content. The import test enforces it. |
| **Predictions about the marriage** | We cannot support them and would be liable for them. |
| **"How to handle your partner" advice** | §2.2. This is the manipulation manual, one editorial slip away. |
| **Risk flags to the facilitator** | Tempting and dangerous: a system that quietly tells a third party a couple looks high-risk, on 22 self-report items, without telling the couple. If the questionnaire ever surfaces a safety concern it goes to **the person**, through the existing safety path, never to the facilitator. Per D7 that path is never gated. |
| **A comparison against other couples** | Norming data we do not have. |
| **A 2×2 diagram with the couple plotted on it** | **D3.42.** The version of the compatibility score most likely to be proposed by someone who has read and agreed with the no-numbers rule. A diagram with two dots is two numbers, plus a third the couple invents — the distance between them — rendered more memorably than digits would have been. It is also the obvious way to visualise pages 2–4, so it *will* be requested. A diagram of the **model** on the methodology page is fine; a diagram with **your dot on it** is not. |

---

## 10. Acceptance criteria

**Boundary**
1. Import test: the report module's transitive imports exclude `behaviour`,
   `connection`, `insights`, `chat`, `sessions`, `memory`.
2. Output test: no `behaviour.SIGNALS` key, no numeric score, and no string from
   `SELF_DESCRIPTION` appears in any rendered page.
3. Byte-identical output for both partners and the facilitator, asserted.

**Correctness**
4. Generation refuses on any unmet precondition (§3), with the reason surfaced to
   the cohort view and no partial PDF written.
5. `calculate_rsq_attachment_style({})` returns `unknown`, not `secure`.
6. A couple where one partner is `unknown` produces no report.

**Copy**
7. Reversibility: for a sample of couples across all nine axis patterns, swapping
   the names produces text that reads correctly. Manual, QA-owned.
8. No page prints a numeric score.

**Craft**
9. Renders correctly on A4 and Letter; legible in greyscale at 100%.
10. Regeneration produces a new dated version without destroying the prior one.

**Journey**
11. A partner who force-quits mid-questionnaire resumes with answers intact
    (§8.3).
12. Two people redeeming the same cohort code land in one relationship (§8.2).

---

## 11. Open questions

1. **Nine axis-pattern copy blocks + four conversation sets.** Mine to write,
   next deliverable. Engineer can build the shape against placeholders.
2. **Threshold for `differing`.** Needs the corrected scorer's output
   distribution. Engineer: once P0.1 lands, give me the axis distribution across
   whatever profiles exist and I will set it. Until then, midpoint split.
3. **Do we name the instrument as RSQ-derived on page 8?** I say yes (§7). It is
   discoverable from the items, and volunteering it is worth more than the
   distinctiveness we lose. Flagging because marketing may disagree.
4. ~~Certificate of completion~~ — owned, specced in Appendix A (P0.11).

---

# Appendix A — the completion certificate

Execution-plan **P0.11**. Same generation pipeline as the report; engineer builds
it alongside P0.3.

## A.1 What it is

**One page. One per couple. Landscape. Printable at home on a home printer.**

It goes on a wall and it gets photographed. That is not a joke about its
importance — for a church premarital course it is the only part of this product
that a couple's family sees, and a photographed certificate with a parish name on
it is the cheapest distribution this business has.

## A.2 Content

- **"Certificate of Completion"**
- *"[Partner A] and [Partner B]"*
- *"completed the [programme name] premarital preparation programme"*
- Date of completion
- Facilitator name, and a signature line — **ruled, blank, for a wet signature.**
  Do not pre-render a digital signature; a facilitator signing it by hand is what
  makes it theirs rather than ours.
- Programme / parish name and logo if supplied
- Bliss wordmark, small, at the foot — the same restraint as the report cover

## A.3 Rules

- **No scores, no attachment styles, no archetypes, no assessment content of any
  kind.** This document leaves the couple's house and hangs on a wall. Anything
  psychological on it is a privacy incident with a picture frame around it. The
  boundary rule (§2) applies with no exceptions.
- **Both partners named, equal weight, same type size.** Alphabetical by first
  name to avoid encoding any precedence.
- Renders on A4 and US Letter, landscape. Legible photocopied and photographed.
- No QR code, no verification URL, no "scan to verify." It is a keepsake, not a
  credential, and a broken link on a wall five years from now is worse than no
  link.

## A.4 When it generates

On **programme completion**, not on purchase — otherwise it certifies nothing.

Until the curriculum exists (see §11.5), "completion" has no definition. Two
options, and the facilitator picks per cohort at redemption:

- **Facilitator-marked** — they tick the couple complete in the cohort view.
  Correct default: they ran the sessions, they are the authority on whether the
  couple finished, and it needs no product surface.
- **Programme-marked** — automatic once the eight sessions are done, available
  only once the curriculum ships.

Ship facilitator-marked first. It works today, needs one button in the cohort
view, and it does not block on §11.5.

## A.5 Acceptance criteria

13. Certificate contains no attachment style, archetype, score, or portrait text
    — asserted against the rendered output.
14. Generates only for couples the facilitator has marked complete; not on
    purchase, not on report generation.
15. Renders A4 and Letter, landscape, legible in greyscale.
16. Both partners' names appear at identical type size.
