# Bliss — distribution and pricing strategy

Written 2026-08-03, and **revised twice the same day** as founder decisions
landed (`docs/execution-plan.md`):

- **D2 — one SKU at $39.** §5 rewritten; §6.0 and §8 re-targeted around
  facilitators rather than couples.
- **D3.0 — global SaaS, not a regional or diaspora product.** §7 rewritten
  global-first; §6.3(a) re-pointed at Catholic marriage-preparation offices; the
  withdrawn regional research retained in **Appendix A**.

Sections 1–4 and 9 are unchanged and still hold.

Companion to `docs/product-assessment.md`, which covers the product itself. This
document covers the two things that assessment identified as unstarted: **who
finds this product, and what they pay for it.**

Based on a full pass over the codebase (Flutter mobile, Django + FastAPI
backends, 285 commits since April 2026), the existing product assessment, and
market research on the couples-app category conducted for this document.

---

## 0. The plan I followed

Stated up front so the reasoning is auditable.

1. **Establish product truth from the code, not from the pitch.** Feature
   inventory, what is actually shipped vs specced, the two-sided mechanics, the
   cost structure implied by the model config, and the readiness gaps that
   constrain distribution.
2. **Price the category.** Direct competitors (Paired, Relish, Flamme), adjacent
   premium (Talkspace couples, OurRitual), and the ceiling that real couples
   therapy sets.
3. **Get the funnel economics.** Install→trial→paid benchmarks, CPI by platform,
   revenue-per-download by category, and category-specific retention.
4. **Find channel evidence, not channel opinion.** How the incumbents actually
   grew; what the institutional analogues (Prepare/Enrich, Hallow) prove about
   partner-led distribution; where two-sided products break.
5. **Work backwards from 1,000.** Pick the definition of "customer", build the
   funnel arithmetic per channel, then size the pricing to the funnel rather
   than to a comparison table.

**Since answered by the founder:** the market question is settled — Bliss is a
global SaaS product (D3.0), so §7 is now a channel strategy rather than a
market-selection argument, and §5 carries one global price rather than three
regional ones. The distribution plan in §6 is written for a solo founder with
~$50; §6.7 says what changes with real money.

---

## 1. What the product actually is

Stripped of the roadmap, Bliss is three products sharing one app:

| Layer | What it is | State |
|---|---|---|
| **The couple loop** | Daily question both partners answer privately, unlocking only when both are in. Check-ins, connection score, games, Two Truths, commitments, shared goals, Focus mode, @bliss. | Shipped, starved of content (14 questions) |
| **The AI counsellor** | Private and joint sessions with a personalised, memory-backed model. Tone coach and "say it better" inline in couple chat. Three-layer safety classifier with CI gates. | Shipped, buried behind four chrome bars |
| **The clinical bridge** | Therapist portal with bilateral-consent connections and strategy notes. RSQ attachment assessment, communication-style quiz, relationship portrait. | Built, no product story around it |

Two things in that table matter more for go-to-market than anything else:

**The RSQ + portrait is an assessment product hiding inside an app.** Thirty
attachment items adapted from the Relationship Scales Questionnaire (**not** a
validated scorer — the subscales are ad-hoc, there is no norming sample and no
reliability figures, so **"validated" must never appear in copy aimed at
clinicians**), a
communication-style quiz, cultural and faith
context, producing a per-partner portrait. Product-wise this is currently a
liability — 40 taps before any value (§2.2 of the assessment). Commercially it
is the single most sellable artefact in the codebase, because assessments are
what institutions buy. Prepare/Enrich sells essentially this — an assessment
plus a workbook plus a facilitator report — for **$35–$65 per couple**, and it
describes itself as the most widely used premarital assessment programme. That
is their own marketing claim, not an independently verified one — it is fine as
background, and should not be repeated as fact in anything we publish.

**The therapist portal is a distribution channel that was mistaken for a
feature.** `TherapistConnection.is_active` requires both `consent_therapist` and
`consent_client`. That bilateral gate is exactly what a clinician needs to
recommend a tool without a liability problem. Therapists are already the highest
-intent referrers in this category — the between-session-tool recommendation is
a routine part of couples practice.

**The genuinely defensible thing** is the ethical architecture: the partner
boundary (`personalization/boundary.py`), the behaviour-only connection score
that is allowed to fall and hides itself on a bad week, the assist paths that
fail open, the deliberate absence of a streak, the decision to derive-and-
discard call audio. In a category where the obvious business model is
engagement-maximisation applied to people's marriages, "we built this so it
cannot be used against you" is a positioning nobody else can copy quickly,
because copying it means giving up metrics. **This is the marketing message and
it is currently written only in code comments.**

### 1.1 What blocks distribution today

From the assessment, restated as go-to-market blockers:

- **No analytics of any kind.** You cannot run acquisition you cannot measure.
  Every channel test below is unreadable until this exists.
- **40+ taps to first value**, no skip, no scale anchors. Every install you buy
  or earn leaks here.
- **Email-only invite.** The product is two-sided; the invite is the growth
  loop; it is currently a text field for an email address, with no share sheet,
  despite `bliss://accept-invite?token=…` already working.
- **No billing of any kind.** No RevenueCat, no Stripe, no entitlement check.
- **14 daily questions.** The retention engine has two weeks of fuel.

**Nothing in §6 should be spent on before the first four are fixed.** Buying
traffic into this funnel is buying a leak. The sequencing in §6.1 accounts for it.

---

## 2. Market and competitive set

### 2.1 The category is real and mid-sized

Paired — the category leader for established couples — has ~8M downloads, over
100,000 daily active couples, and roughly **$200k/month revenue** on ~$7.3M
raised across three rounds. That is the honest shape of the prize: a good
couples app is a solid $5–20M ARR business, not a unicorn, unless it crosses
into clinical services or B2B.

The couples-app market is projected at ~$5.77B by 2033 (12.5% CAGR), but treat
category forecasts as directional only.

### 2.2 Price map

| Product | Price | Model |
|---|---|---|
| Flamme | $4–13/mo | Playful couples app + light AI coach, free tier |
| Paired | **$14.99/mo, $69.99–83.99/yr** | One subscription covers both partners; free tier with limited daily questions |
| Relish | **$99.99 / 6 months (~$16.67/mo)** | One sub, free linked partner account, 7-day trial; +$156 for coaching |
| Prepare/Enrich | **$35–65 one-off per couple** ($130 with virtual facilitator) | Institutional, facilitator-mediated |
| OurRitual | **$52–65/week for couples** | Hybrid: short live expert sessions + app |
| Talkspace couples | **$436/month** ($109/wk) | Licensed therapists, 4 live sessions + messaging |
| In-person couples therapy | **$100–250/session**, $150–300 typical in person | The thing everyone is priced against |

Two conclusions:

1. **The self-serve couples-app ceiling is ~$15/month, and one subscription
   covers both partners.** That is the settled norm — Paired, Relish and Flamme
   all do it. Charging per person would be a visible defection from category
   convention and would halve your pairing rate.
2. **There is a wide-open gap between $15/month and $436/month.** Bliss's AI
   counsellor plus the therapist portal is the only asset in the codebase that
   can credibly occupy the $30–80 band. Nobody self-serve is there.

### 2.3 The wedge nobody else has

Bliss has three things the category leaders do not:

- **Faith as a first-class, opt-in, non-coercive feature.** `DailyReading`,
  `FaithPractice`, `FaithReflection`, tradition-tagged, with an explicit rule
  never to use faith framing to keep someone in an unsafe relationship. Paired
  and Relish have nothing here. Hallow proves the demand: 20M+ downloads, ~$400M
  valuation, materially lower churn among parish cohorts than individual
  subscribers.
- **Cultural context in the personalisation model** — `cultural_framing`
  switches between "family and community wellbeing" and "individual wellbeing".
  Every Western competitor assumes the latter. This is a real differentiator for
  African, South Asian, Middle Eastern and Latin markets and their diasporas.
- **A therapist portal with a consent gate.** *Frozen for v1 (D3.35) — the code
  exists but it is not part of what we ship or claim. Retained here because it
  is a real asset when there is capacity to use it.*

---

## 3. Unit economics

### 3.1 COGS is not the constraint

From `backend-fastapi/app/orchestration/model_config.py`: counselling replies on
`gpt-4o`, everything fast (tone coach, safety screening, memory extraction) on
`gpt-4.1-nano`.

At current API pricing (~$2.50/$10.00 per 1M tokens for gpt-4o; ~$0.10/$0.40 for
4.1-nano):

| Path | Per call (est.) | Typical monthly volume per couple | Cost |
|---|---|---|---|
| Counselling reply (3k in / 400 out) | ~$0.012 | 20–60 turns | $0.24–0.72 |
| Fast paths — tone, safety, extraction | ~$0.0002 | 300–800 calls | $0.06–0.16 |
| Embeddings, infra amortised @1k couples | — | — | ~$0.30 |
| **Total per couple per month** | | | **~$0.60–1.20**, heavy users ~$3 |

**Gross margin at $14.99/month is 92–96%.** At $89.99/year (~$7.50/mo) it is
still 84–92%. LLM cost does not constrain your pricing; it only constrains an
unlimited-voice-session tier, which is unbuilt anyway.

The real constraint is CAC.

### 3.2 CAC is brutal, and that decides the whole strategy

- iOS CPI averaged **$5.84 globally in Q1 2026** (up 19% YoY); Android $1.92.
  North America iOS runs $5–6. Dating/relationship sits at the high end of the
  range.
- Global install→trial is ~10.9%; trial→paid ~25.6%. Health & Fitness leads
  trial→paid at ~35%.
- Hard paywalls convert ~5× better than freemium at day 35 (10.7% vs 2.1%
  download→paid) with near-identical year-one retention.
- Health & Fitness median lifetime revenue per download is **$35.64** — the best
  category — and annual plans are 60.6% of its revenue.

Now apply the two-sided penalty, which is the number the benchmarks miss.

### 3.3 The funnel to a paying couple

A "customer" for Bliss should mean **a paying couple**, not a paying user or an
install. It is the only unit where the product works, and it is the unit you
bill.

Partner A installs. The couple only becomes a customer if A activates, A
invites, B accepts, B onboards, and one of them pays.

| Stage | **Today** (40-tap onboarding, email-only invite) | **After the §6.1 fixes** |
|---|---|---|
| Install → onboarding complete | 35% | 65% |
| → invite sent | 40% | 60% |
| → partner accepts & onboards | 45% | 60% |
| **= paired couples** | **6.3%** | **23.4%** |
| Paired → paying (highly qualified by now) | 25% | 30% |
| **Install → paying couple** | **~1.6%** | **~7.0%** |

**1,000 paying couples therefore needs ~63,000 installs today, or ~14,000 after
the fixes.** At $5 iOS CPI that is $315,000 versus $70,000 — and $70,000 is
still more than a bootstrapped budget.

Three things fall straight out of this:

1. **Fixing activation is worth more than any marketing budget you could
   plausibly raise.** It is a ~4.4× multiplier on every install from every
   channel, paid or free. Do it first.
2. **Paid install advertising is off the table** until you know your paying-
   couple LTV, and probably permanently on iOS at these CPIs.
3. **Every channel below must be zero-or-low CPI, high-intent, and ideally
   deliver couples in bulk** — which points hard at institutions and at the
   in-product invite loop.

---

## 4. The three growth loops that matter

Everything in §6 is an attempt to start one of these.

**Loop 1 — the partner invite (already built, badly).** Every paying couple is
two installs, one of which cost nothing. This is the only structurally free
acquisition the product has, and it currently runs through an email text field.
A share sheet with a link is worth more than any channel in §6. Target: **>60%
of activated users send an invite; >60% of invites convert.**

**Loop 2 — the couple-to-couple referral.** Couples socialise as couples. The
games, Two Truths and This-or-That are the natural vector: "challenge another
couple" is a mechanic the game models could support. Give each paying couple a
30-day free-couple code. Target: **>0.3 referred couples per paying couple.**

**Loop 3 — the institutional cohort.** One premarital class, one therapist, one
parish delivers 15–60 couples per touch at near-zero marginal cost. This is the
only loop that scales without a marketing budget, and it is the one Bliss is
uniquely equipped for (assessment + therapist portal + faith tab). Hallow's data
is the proof point: cohort-acquired users churn materially less than
individually-acquired ones.

---

## 5. Pricing

**One SKU. One price. Everywhere.**

```
Bliss — $39, one payment, per couple.
Yours to keep:  assessment · portraits · report · certificate · the daily loop
For 12 months:  the AI counsellor
```

The 12-month bound on the counsellor is **D3.11a**, and it supersedes the
perpetual-access recommendation in §5.2 below — unlimited permanent counselling
against a one-off price is unbounded cost, which §5.2 had identified and left
open. It is disclosed at the point of sale, in the same breath as the price and
alongside four things that *are* permanent. A time bound discovered in month 13
is the same category of error as a curriculum that does not exist.

Founder decision, 2026-08-03; rationale in `docs/execution-plan.md` D2.

**Dead as of that decision:** Premium at $14.99/$89.99, Bliss Together at $49,
the $9.99 therapist rate, the tiered Cohort License, the separate ₦ price list,
and the 30-day trial. This section previously ran to six sub-sections and a
five-row ladder. It is now four words, which is the point.

### 5.0 What $39 does **not** include — read before any facilitator call

An earlier version of this section sold the pack as including *"an 8-session
guided curriculum"* and *"a completion certificate."* **Neither exists.** Zero
hits across the repository for curriculum, 8-session or premarital; no
`Curriculum`, `Programme` or `SessionPlan` model. What exists is 121 daily
questions, 9 game packs, 9 micro-action templates, 8 daily readings and
conversation decks — good content, with no eight-session structure over it.

Both claims are struck from every asset. The certificate is scheduled
(execution-plan P0.11, ships with the report); the curriculum is P1 and
deliberately unshaped, pending §6.3(a)'s discovery question.

**Why this is worse than an ordinary copy error.** In this channel the
facilitator's own reputation is the collateral — they recommended us to their
class. "The curriculum you told us about isn't in here" does not merely lose
cohort two; it gets repeated to every facilitator they know, and §6.0 says the
entire model rests on facilitators who stay and repeat. Sell the assessment,
the portraits, the report and the daily practice. All four exist.

### 5.1 Why $39 is the right survivor

- **It is the only price in the old §5 argued from something other than
  competitor comparison.** It sits inside Prepare/Enrich's $35–65 band — the
  purchase shape this buyer already makes, already budgets for, and already
  knows how to approve.
- **A one-off has no churn**, no cancellation flow, no dunning, no failed-card
  recovery, and no "what happens when the course ends" conversation with a
  facilitator's couples.
- **It is sayable.** A solo founder on a call says "thirty-nine dollars, once,
  covers both of you" and the pricing conversation is over. The tier table it
  replaced took a paragraph and invited negotiation.
- **It removes the App Store from the critical path entirely**, which is what
  makes execution-plan D1 (web-first billing) coherent.

### 5.2 What the decision costs, stated once

Two consequences follow mechanically. Neither is an argument to reverse it —
they are things to plan around.

**Revenue stops compounding.** Every dollar is sold once. Last month's couples
do not pay this month, so growth has to come entirely from new couples. That
makes the institutional channel not merely the best option but the *only* one:
2,564 couples is not a number one person recruits individually. See §6.0.

**COGS is now unbounded against fixed revenue.** This is the one genuinely new
risk and it did not exist under a subscription. From §3.1, a couple costs
~$0.60–1.20/month to serve, and heavy users ~$3. Against $39 collected once:

| Usage | Cost/month | Months until the couple costs more than it paid |
|---|---|---|
| Light | $0.60 | ~65 (5.4 years) — fine |
| Typical | $1.20 | ~32 (2.7 years) — acceptable |
| **Heavy** (~100 counselling turns/mo) | **~$3.00** | **~13 — loses money inside year two** |

Most couples will not be heavy, and ordinary attrition works in your favour
financially here. But "full app access" sold as a perpetual right against a
per-message model cost is an open-ended liability, and at 2,500 couples the tail
is real money.

**Do not fix this by metering the counsellor** — §5.4 explains why. Options, in
order of preference: (a) ship it as written, instrument cost-per-couple in the
analytics already built, and revisit with data; (b) define "full app access" as
24 months at the point of sale, which is longer than a premarital cohort needs
and still honest; (c) a fair-use ceiling on counselling turns, which is the
worst option because it rations the thing people need most.

**RESOLVED — superseded by D3.11a.** Option (b) was taken, and taken now rather
than later: the counsellor is bounded to 12 months at the point of sale, while
the assessment, portraits, report, certificate and daily loop stay permanent.
Product's reasoning was that the tail is not merely large but *unbounded*, and
that a bound disclosed at purchase costs far less than one introduced in month
13 to couples who were told "one payment, no subscription."

I had recommended (a) — ship perpetual, measure, revisit at 500. The case
against my version: it optimises for conversion today by deferring a disclosure
we would almost certainly have to make later, to the same people, having already
taken their money. That is the shape of the errors this document has been
correcting all week. The cost-per-couple instrumentation still ships, because
the 12-month bound needs validating too.

### 5.3 How it is sold to a cohort

The SKU sheet got simpler; the channel did not change.

- **One transaction, thirty codes.** 30 couples × $39 = **$1,170**, sold to the
  facilitator as a single purchase and delivered as redemption codes they hand
  out. This is the shape that makes a cohort one conversation instead of thirty.
- **Or the couples pay individually** at the same $39, which closes faster
  because it needs no budget approval, but leaks 20–40% redemption.

**Offer both on call one** (execution-plan D3.8): invoice where their budget
allows, the couples-pay link where it doesn't. My earlier "never quote a licence
on call one" rule still holds — that was about the *ladder*, and the ladder is
still not published. What changed is that facilitator-pays-by-invoice belongs on
the table from the start wherever the money exists, because of the leak below.

**The redemption leak is not forgetfulness — it is a rational free ride.**
Nothing stops a cohort couple installing the app, using the free daily-question
loop, and simply not paying $39 unless they want the report. That is the real
mechanism behind the 20–40% estimate, and it is worth being precise about,
because it means the leak *cannot be closed by reminder emails.* Facilitator-pays
does not have the problem at all: the couples never face the decision.

**The unresolved question underneath it — for the engineer's entitlement work
(P0.2): what does an unpaid install actually get?** My recommendation, and the
reasoning:

- **The daily-question loop stays free.** It is Loop 1 (§4), the only free
  acquisition the product has, and partner B must be able to enter without a
  paywall. Walling it kills the growth engine to protect a $39 sale.
- **$39 buys the assessment, both portraits, the facilitator report, and the
  counsellor.** These are the things a cohort is actually buying and the things
  a free rider cannot get by waiting.
- **Nothing downstream of the support icon is ever gated** (D7), for paid,
  unpaid and refunded couples alike.

That split makes the free ride rational-and-fine for a consumer — they get the
loop, we get a future buyer — and a genuine leak only in cohorts, which is
precisely the case facilitator-pays solves. It is a reason to prefer invoicing,
not a reason to wall the product.
- **The facilitator seat stays free, always.** Never invoice the person doing
  your distribution.
- **Take invoices and bank transfers, not just card.** Churches and NGOs
  frequently cannot pay by card. A Stripe-link-only checkout will lose sales
  that had already said yes. This is a requirement on the checkout build, not a
  preference.
- **Pilot the first cohort.** At zero downloads, sell nothing on call one. Let
  them run a cohort where the couples pay $39 each, then sell the block at
  cohort two when they have watched it work.

**On price flexibility:** $39 is global and single-currency (D3.0). That is a
deliberate trade — one price is the SKU, and geo-pricing would reintroduce the
tier table the founder collapsed. The consequence is that low-ARPU markets are
reachable through *institutions* with fee-paying clienteles rather than through
consumers. See the appendix for the regional-entry work that assumed otherwise.

### 5.4 What not to do

- **Never meter the counsellor** — no per-message credits, no session caps sold
  as a tier. Rationing therapy by the message makes people ration the thing they
  need. If §5.2's cost tail has to be addressed, address it with a term limit at
  the point of sale, not with a meter at the point of need.
- **Never gate the safety path.** No paywall, no entitlement check, no
  redemption-code wall on the support icon, the crisis resources, or anything
  downstream of them — for paid, unpaid, and expired couples alike. This is
  execution-plan D7 and QA owns the test.
- **Never build an "unlock your partner's profile" upsell.** `boundary.py`
  exists to prevent it, and `docs/outcome-loop.md` is right that an inferred
  model of one partner shown to the other is a manipulation manual. It would be
  the single most tempting upsell in the product. The prohibition is written
  here so that it is refused by reference rather than re-argued.
- **Never discount below $39 to individuals.** One price means one price; the
  moment it is negotiable it is a tier table again.

### 5.5 Gifting — now stronger, not weaker

A one-off is the natural gift SKU. "$39, once, for a couple you love" needs no
explanation, has no recurring charge to inherit, and nothing to cancel. Parents
and friends buying for engaged couples were always the best fit here, and in
many wedding cultures a purchasable gift code sold alongside a
premarital cohort is a natural attachment.

Same price, same product, different buyer. Build it as a code, not a new SKU.

---

## 6. Distribution: the road to $100k at $39 a couple

### 6.0 The arithmetic — two channels, and they do different jobs

**Revised for D3.39: couples therapists are the primary channel, premarital
programmes are secondary.** Both stay. They are not alternatives, and the
reason is arithmetic.

At $39 one-off, $100,000 is **2,564 couples**. Where those couples come from
differs by an order of magnitude per relationship:

| Relationship | Couples/yr | Revenue/yr | Notes |
|---|---|---|---|
| **One facilitator** running 4 cohorts of 30 | ~120 | **~$4,680** | Bulk, scheduled, repeating |
| **One therapist** referring couple-by-couple | 10–20 | **~$390–780** | Trickle, continuous |

**A therapist relationship is worth roughly 6–12× less than a facilitator
relationship.** That is not a reason against the channel — it is the reason the
plan needs both, and it decides which does which job.

**Therapists cannot reach $100k alone.** At ~$585/yr each it would take ~171
active therapists, which at a 10–15% cold-outreach conversion means contacting
1,100–1,700 of them. At the four-contacts-a-week rate one founder can sustain
(§15.7), that is five to eight years. The channel is not the scale engine and
should never be planned as one.

**What therapists are is the fastest route to first revenue, real usage, and
genuine global reach.** One person decides, on the call. No committee, no term
calendar, no doctrinal review, and directories exist in every English-speaking
market rather than only the US (§15.2).

#### The honest ramp, both channels

Therapists from month 1; programmes introduced around month 6, once there is
usage and a reference to point at.

| Quarter | Active therapists | Active facilitators | Couples | Revenue |
|---|---|---|---|---|
| Q1 | 3 | 0 | ~8 | ~$300 |
| Q2 | 10 | 0 | ~30 | ~$1,200 |
| Q3 | 20 | 2 | ~125 | ~$4,900 |
| Q4 | 30 | 5 | ~250 | ~$9,750 |
| **Year 1** | **30** | **5** | **~410** | **~$16,000** |

Exiting month 12 at roughly a **$41k/yr run rate** — about $17k of it from
therapists and $23k from five facilitators, which is the ratio table above doing
its work. **$100k still requires the cohort channel at scale (~21 facilitators),
and now arrives around month 24–30** rather than month 15–18.

#### State the cost of the reversal plainly

**This plan banks less in year one than the facilitator-first version did
(~$16k against ~$54k) and pushes $100k out by roughly six to twelve months.**

That is the real trade and it should not be smoothed over. The counter-argument
is that the $54k was never as solid as it looked: it required conservative
institutions to say yes to an unproven product with no users, no outcomes, no
references — and, on due diligence, a `spicy` game category (§9). **A lower
number with a higher probability is worth more than a higher number that
depended on the hardest possible first customer.**

The sequencing error being corrected is mine: I had us approaching the buyer
with the **highest evaluation bar** at the moment our evidence was **weakest**.
Therapists are a lower bar, reachable globally, and they generate exactly the
evidence — usage, outcomes, a named professional willing to be referenced —
that makes the institutional conversation winnable later.

### 6.1 Phase 0 — weeks 0–6: earn the right to distribute

No acquisition spend. No launch. Five things, in this order:

1. **Ship analytics.** The event schema from assessment §2.1 — onboarding
   start/step/abandon/complete, invite sent/opened/accepted, pairing complete,
   question answered/revealed, session started, day-N return, trial start,
   subscribe. Names and timestamps, no content, consent-aware. **Everything
   below is unmeasurable without this.**
2. **Cut onboarding to 8–10 items, label the Likert anchors, make the rest
   progressive, drop the hard gate.** This is the 4.4× multiplier from §3.3.
3. **Ship the share-sheet invite** with a link as the primary action (WhatsApp
   first — the highest-reach messaging app in most markets, and the deep link already
   works). Let partner B see the blurred question before onboarding.
4. **Ship billing** — Stripe Checkout on the web (D1). Paystack is cut from P0
   (D3.0); IAP comes later, with the app-store listing.
5. **Fix the top visual defects** — the Dynamic Island clipping on all four
   tabs, the strategy chip, the joint-session title, the storage/history
   contradiction. You are about to invite strangers in.

The daily-question content pool (§2.3 of the assessment) must be fixed before
Phase 3, not before Phase 1 — 50 hand-held couples will not exhaust 14
questions, 500 will.

### 6.2 Phase 1 — weeks 4–12: 50 couples, by hand

Do not launch. Recruit fifty couples personally and talk to them weekly. This
is the 20-user pilot done properly, and it doubles as the discovery process the
assessment says is entirely absent (§2.14).

Where the 50 come from:
- Personal and second-degree network. Ask directly, one couple at a time.
- Two additional premarital programmes, per §6.3(a). *(Was three couples-
  therapists; cut under D3.35.)*
- One premarital cohort (see §6.3).

What you get: the activation numbers in §3.3 replaced with real ones, the first
churn signal, the language couples actually use to describe the problem — which
becomes your ad copy, your App Store subtitle and your creator brief — and the
answer to which of the twenty-one feature areas anyone touches.

**Gate to Phase 2:** ≥60% of installs pair, ≥40% of paired couples still active
in week 4, and at least 15 couples who say they would pay.

### 6.3 Phase 2 — the two institutional channels, in order

#### (a) Couples therapists — PRIMARY (D3.39)

**Reversed from a previous cut. This is now the first channel worked.**

Why it goes first, in order of weight:

1. **Lowest evaluation bar at the moment our evidence is weakest.** No users, no
   outcomes, no references. A secular clinician evaluating a between-session
   tool for their own practice is a far easier first customer than an
   institution running a doctrinal and reputational check.
2. **Genuinely global.** Therapist directories exist in every English-speaking
   market — Psychology Today, Counselling Directory (UK), and national
   association registers across CA/AU/IE. The programme list was US-first only
   because the USCCB happens to publish a directory. This channel is
   contactable remotely from anywhere, which is what "global with no budget"
   actually requires.
3. **One person decides, on the call.** No committee, no term calendar, no
   approved-instrument list. A therapist can say yes and refer a couple that week.
4. **They are the audience for the actual differentiator.** Clinicians care about
   the partner boundary more than any feature in the product.

**The pitch — the boundary leads, and it is the whole opening:**

> The model never shows one partner an inference about the other. Not as a
> setting — as a single enforced function, with a test suite that tries to break
> it and fails. Here is the file.

Then: free for the therapist, always. Their couples pay $39, get the assessment
and portraits, and **the therapist gets the same report** — recast for this
channel as *"a report you and your couple can work from"* rather than a
facilitator's teaching document. Same artefact, same eight pages.

> ⚠️ **What we must NOT promise: a therapist portal, dashboard or login.**
> `apps/therapist/` is a REST API — a login view and viewsets for connections
> and strategy notes — with **no client of any kind.** No mobile feature, no web
> app, nothing to log into. Verified 2026-08-03. The offer is *referral plus a
> report delivered to them*, not an account they use. An earlier draft of this
> section promised "a free therapist account" and "their couples' shared
> progress"; both were written before anyone checked whether a client existed.

Expect ~10–15% of cold outreach to try it, and each active therapist to refer
10–20 couples a year (§6.0). Target ~30 active by month 12.

#### (b) Premarital programmes — SECONDARY, and unchanged

**Kept intact, deliberately.** Everything in §15 (sourcing), `marketing-copy.md`
§14 (the delivery kit) and the call script applies unchanged when this channel
opens. It is not wasted work and it should not be deleted — it is the **scale
engine**, and per §6.0 it is the only path to $100k.

**What changed is when, not whether: introduce it around month 6**, once there
is usage, an outcome, and a named professional willing to be a reference.
Approaching a conservative institution with none of those was the sequencing
error §6.0 describes.

**Why this channel works anywhere, which is the point (D3.0).** The mechanism is
not cultural, it is structural: a premarital programme assembles couples into
cohorts on a schedule, with a facilitator who is looking for better materials
than a photocopied workbook. That is true in Sydney, Dublin, Toronto and Ohio.

The strongest version of it is a **mandatory** programme, because a mandate is a
self-enforcing funnel — nobody has to be persuaded to attend. Two properties
make a mandate real, and both are worth checking on any target:

1. **Somebody refuses to proceed without it.** A government can announce a
   requirement and never police it; a church that declines to conduct the
   wedding has enforced it completely.
2. **It follows the couple**, rather than applying only at one location.

- **US and international Catholic marriage-preparation offices — start here.**
  Pre-Cana is a diocesan requirement, it runs worldwide, the coordinator role is
  formal and publicly listed, and **these offices already pay $35–65 a couple for
  Prepare/Enrich.** Budget line established, price established, mandate
  self-enforcing. This is the centre of the strategy, not a side bet.
- **Evangelical and non-denominational premarital programmes** in the US, UK,
  Canada and Australia. Many require counselling before the church will conduct
  a wedding — the same self-enforcing property, under their own programme names.
  Named public programme pages make them easy to personalise to.
- ~~Couples therapists~~ — deprioritised for v1 (D3.35). Free distribution, but
  a trickle against a cohort. Accept inbound; do not source.

*Evidence note: the mandate property was established while researching a
regional entry that is no longer the plan — the RCCG, a denomination that
requires premarital counselling and declines to officiate without it,
regardless of where the wedding takes place. That research is retained in the
appendix. What transfers is the property, not the targeting: Catholic Pre-Cana
has the same structure and a far larger, more global footprint.*

Pitch to the facilitator, never to the couple: *"Your couples get the assessment
and a report you can teach from, and they keep the app after the wedding."*
Free facilitator seat, cohort dashboard, $39/couple.

Target: 5–8 cohorts, 25–40 couples each, ~60% activation = ~200 couples.

**(b) Couples therapists — deprioritised for v1 (D3.35)**

**Do not source therapists.** Not because the channel is bad — it costs nothing
and a clinician's referral is high-intent — but because it delivers couples one
at a time against a cohort channel delivering 25, and one founder working two
channels badly loses to one channel worked well. If a therapist approaches
unprompted, take it. The case below is retained for when there is capacity.


The therapist portal already has the bilateral consent gate that makes this
safe. Therapists recommend between-session tools routinely; the Gottman Referral
Network is a public, free-to-search directory of Gottman-trained clinicians.
(An earlier draft said it lists "thousands." I have not counted it — do not use
a number in a deck without pulling one from the directory first.)

Cold-outreach 100 therapists with a specific, honest offer: free therapist
account, their couples get Premium at $9.99, they get the couple's shared
progress with both consents, and — the actual hook — *"the model never shows one
partner an inference about the other; here is the code that enforces it."*
Clinicians care about that boundary more than any feature.

Expect 10–15% to try it; each active therapist brings 5–10 couples. ~100 couples,
and materially better retention than self-serve.

**(c) Wedding-adjacent — target 50 couples**

Wedding planners, registries, bridal fairs and wedding-content creators, with
the gifting SKU. Strongest wherever wedding spend is concentrated and communal.

### 6.4 Phase 3 — weeks 16–48: content and creators, ~600 couples

Only after Phase 2 proves activation and retention.

**(a) Relationship-therapist creators, not generic influencers.** Paired grew
through influencers and partnerships; the version of that which works for a
counselling product is licensed therapists and relationship educators on TikTok
and Instagram, whose audiences arrive pre-qualified and who can speak credibly
about the safety architecture. Seed 20–30 with free lifetime accounts and an
affiliate cut before paying anyone. Brief them on the *boundary*, not the
feature list — "an app that refuses to tell your partner what it thinks about
you" is the video that gets made.

**(b) A shareable artefact.** The relationship portrait is about *yourself*, so
it is safe to share, and it is a natural social object. The connection score is
about the couple and must never be shareable. Build the former into a share
card; the assessment is the top of the funnel and the share card is its
distribution.

**(c) Communities, not campaigns.** r/Marriage, r/relationship_advice,
r/CouplesTherapy, and — in most markets outside the US — WhatsApp and Facebook
groups. Organic Reddit rewards genuine
contribution over promotion and takes 30–60 days to show signal; budget the
time. Answer questions as a founder who built a thing, not as a brand.

**(d) ASO.** "couples app", "marriage counseling app", "relationship app for
couples", "premarital counseling". Cheap, compounding, and currently at zero:
`pubspec.yaml` still says *"A new Flutter project."*

**(e) The loops.** By Phase 3 the invite loop and the couple-code loop should be
producing 25–40% of new couples with no channel attached. If they are not, the
problem is the product, not the marketing.

### 6.5 Channel summary

| Channel | Couples | Cost/couple | Time to signal | Confidence |
|---|---|---|---|---|
| Partner invite loop (Loop 1) | structural | $0 | immediate | **High** — already built |
| Premarital cohorts — SECONDARY, from ~month 6 | 150 in yr 1, then the scale engine | ~$0 + time | 4–8 weeks | **High on yield, high on bar** — needs evidence first |
| **Couples therapists — PRIMARY** | ~410 in yr 1 | ~$0 + time | 2–6 weeks | **High** — one decider, global directories, lowest bar |
| Hand recruitment | 50 | $0 | immediate | High, does not scale |
| Therapist creators | 250 | $0–$50 | 8–16 weeks | Medium |
| Couple-code referrals (Loop 2) | 150 | ~$8 (comped month) | 12+ weeks | Medium |
| Communities / Reddit / WhatsApp | 150 | $0 | 4–8 weeks | Medium |
| Wedding channel + gifting | 100 | low | 8–16 weeks | Medium |
| ASO | compounding | $0 | 12+ weeks | Medium |
| **Paid installs** | — | **$70–300 CAC** | — | **Do not** |

### 6.6 Anti-channels

- **Paid iOS installs.** $5.84 CPI ÷ 7% install→paying-couple = **$83 CAC** at
  best, $300+ at today's conversion. Against a $90–150 first-year ARPU with
  Apple's cut removed, that is not a business at your stage.
- **Dating apps and dating-adjacent placements.** Wrong audience — Bliss is for
  people who already found each other.
- **Generic lifestyle influencers.** Category needs credibility, not reach.
- **Broad PR before the funnel works.** A TechCrunch post into a 1.6%-converting
  funnel wastes the only launch you get.

### 6.7 What changes with $50k+

Order of priority: (1) content production for the daily-question pool, which is
the retention constraint and is a content-ops problem, not an engineering one;
(2) a part-time partnerships person to work the church and therapist channels
full-time — this channel is labour-bound, not capital-bound; (3) creator
affiliate payouts; (4) *only then* paid installs, Android-first, in low-CPI
markets, and only once you have measured paying-couple LTV.

---

## 7. Market strategy — global, and honest about what that costs

**Revised 2026-08-03 for D3.0.** An earlier version of this section recommended a
diaspora-first beachhead. The founder's direction is that Bliss is a global SaaS
product, not a product for a particular population, so that recommendation is
withdrawn. The channel argument survives it — see below — and the withdrawn
research is retained in the appendix rather than deleted.

### 7.1 The honest difficulty, stated first

**A global product with no marketing budget has no distribution.** "Global" names
an addressable market; it does not name a way of reaching anyone. Nothing in §3.2
changes: iOS CPI is ~$5.84, the install→paying-couple funnel makes paid
acquisition unaffordable, and there is $50 in the budget.

So going global makes the institutional channel **more** important, not less. It
is the only mechanism in this document that reaches couples in bulk, at
approximately zero marginal cost, without a brand anyone has heard of. The
cohort channel is the answer to the global ambition, not a retreat from it.

The thing a beachhead was buying — a defined population you can saturate and be
known within — has to be bought some other way. The replacement is **channel
concentration rather than demographic concentration**: be the tool that
premarital programmes use, everywhere, rather than the tool one community uses.
That is a narrower wedge than it sounds, because premarital programmes talk to
each other within denominations and dioceses, which is where word of mouth
substitutes for a brand.

### 7.2 Where to start, in order

1. **Couples therapists, globally (D3.39).** The first channel worked, from
   month 1. Lowest evaluation bar, one decider, directories in every
   English-speaking market. See §6.3(a) — and note what cannot be promised: there
   is no therapist portal, only referral plus a report.
2. **Catholic marriage-preparation offices**, from around month 6. Pre-Cana is a
   diocesan requirement; the coordinator role is publicly listed; **the office
   already pays $35–65 a couple for Prepare/Enrich.** Mandate, budget line and
   price all established. This is the **scale** engine and the only path to
   $100k — approached once there is evidence to show it.
3. **Evangelical and non-denominational premarital programmes**, alongside (2).
   Many decline to conduct a wedding without counselling — the same
   self-enforcing property under their own programme names.
4. **Everything in §6.4** — the invite loop, creators, communities, ASO — behind
   those, and unchanged.

### 7.3 What "global" does not mean

- **It does not mean localisation.** English-speaking markets first, one
  currency, one price. Localisation is a cost with no evidence behind it yet.
- **It does not mean every market at once.** One person can work about two
  channels. Global is the *ambition*; the first ten calls are still ten calls.
- **It does not mean low-ARPU markets are addressable at $39.** They are
  reachable through institutions with fee-paying clienteles, not through
  consumers. That is a real consequence of the single global price (§5.3).

### 7.4 What carried over from the withdrawn recommendation

Kept deliberately, because the reasoning is what mattered:

- **The institutional motion.** A premarital programme assembles couples into
  cohorts on a schedule with a facilitator looking for better materials. That is
  structural, not cultural, and it is true everywhere.
- **The mandate property.** The strongest programmes are ones somebody refuses
  to proceed without. It was discovered in a denomination that is no longer the
  target; Catholic Pre-Cana has the same property at far greater scale.
- **The whole delivery kit** (`marketing-copy.md` §14), including pair-in-the-room.
- **The prediction on the curriculum question** (§7.5 below), which if anything
  is stronger now.

### 7.5 The curriculum prediction survives and strengthens

Facilitators inside a denomination with a **mandated** programme are unlikely to
want a competing eight-week curriculum and likely to want materials that slot
into the one they must use. That was argued from one denomination's manual. It
applies at least as strongly to Catholic Pre-Cana, which is more prescribed, not
less. Expect *"materials, not a programme"* — and ask anyway.

---

## 8. The numbers to watch

Six, re-targeted for the single price. The top two are new and now outrank
everything else, because §6.0 makes facilitators the unit of growth:

| Metric | Target | Why |
|---|---|---|
| **Active facilitators** | 21 by month 12 | The actual growth unit. Each is ~$4,680/yr |
| **Cohorts per facilitator per year** | ≥3 | Where compounding lives under a one-off SKU. A facilitator who runs one cohort and stops is a failed sale that looked like a win |
| **Redemption rate within a cohort** | >80% | Codes bought but never used are the silent leak in block sales |
| **Install → paired couple** | >20% | Still the multiplier on every channel |
| **Invite send / accept rate** | >60% each | Loop 1's health |
| **Week-4 couple retention** | >40% | Whether the loop holds without a streak |

**Retired:** trial→paid — there is no trial. Note that `install → paired couple`
now measures product health rather than revenue, since a cohort couple arrives
already paid for.

Add one qualitative gate: **two couple interviews per week, every week, written
down.** The assessment is right that reasoning quality has carried this product
a long way without feedback, and right that it does not scale.

---

## 9. Risks

**App Store review and clinical claims — improved by D3.35.** Apple scrutinises
mental-health apps. Never say "therapy" or "counselling" in metadata where it
implies licensed care. **Shipping with no humans in the loop makes this
materially easier:** the "not a licensed therapist" disclosure is now
unambiguously true rather than a carefully-worded hedge, and there is no
clinician relationship a reviewer could read as licensed care being brokered.
That is a better position to argue from. The safety classifier and
`VALIDATION.md` remain assets in that conversation — have them ready.

**Safety liability at scale — and the one operational cost D3.35 does *not*
remove.** The three-layer classifier is gated at ≥90% clear-crisis recall with
zero tolerated false positives on safe messages. At 1,000 couples you will see
cases the eval set does not contain. This document previously said "budget for
human review of every escalation."

**With no clinicians, that reviewer is the founder, personally, at whatever hour
it happens.** D3.35 removes clinician recruitment, scheduling, payment, training
and liability — real savings — but it does not remove the reviewing. Stated
plainly so it is visible now rather than discovered at the first escalation:

- Escalations do not respect a working day, and a founder who is also the
  engineering and product team has no rota to fall back on.
- It scales with couples, so it gets worse exactly as the plan succeeds. At the
  §14.7 capacity ceiling — two or three concurrent cohorts, ~75 couples — this
  compounds with founder-as-support-line.
- The cost is not the volume, it is the **unpredictability**: one escalation a
  month is nothing to schedule around and impossible to be unavailable for.

There is no clean answer at this size, and inventing one would be worse than
naming it. The honest mitigations are: keep the false-positive gate at zero so
escalations stay rare and real; make sure the escalation path tells the founder
what happened without requiring them to read a conversation to find out; and
treat this as a reason the capacity ceiling in §14.7 arrives sooner than the
support-line arithmetic alone suggests.

**The `spicy` game category needs a written position before any institutional
conversation.** Flagged, not resolved — this is a product and founder call, not
a marketing one.

What is actually there, verified 2026-08-03: `GamePack` has a `spicy` category
alongside relationship, spiritual and financial; `is_restricted()` returns true
for it; and the docstring states it requires age verification plus a per-couple
opt-in, enforced in the API. **The gating is correct and defensible.** The
problem is not the implementation, it is that a diocesan Family Life director
doing due diligence will find it, and *"we'll explain if it comes up"* is not a
plan.

Three things about it:

- **It does not block the therapist channel.** Secular clinicians working with
  adult couples will not blink, and several will consider it a feature.
- **It is survivable with a prepared answer and fatal without one** — and the
  worst possible moment to improvise is in front of your first institutional
  customer, which is precisely where the old plan put it.
- The honest answer is probably the true one: it is off by default, invisible
  unless both partners are age-verified *and* both opt in, and one partner can
  end it unilaterally. Whether that is enough for a given diocese is *their*
  call to make with full information, not ours to make by omission.

Deciding this is cheap now and expensive later. Options range from a written
position, through a facilitator-facing note, to a cohort-level disable — but
somebody should choose before the first programme call, not during it.

**The two-sided cold start is the whole risk.** Everything in this document is
downstream of the pairing rate. If §6.1's fixes do not move install→paired above
15%, no channel saves it.

**Churn is structural.** Couples leave when things get better and when things
end. Annual plans, the premarital one-off, and institutional cohorts all blunt
it; monthly self-serve will not look like a SaaS retention curve and should not
be judged against one.

**Doing distribution before instrumentation.** The failure mode is running four
channels for three months and being unable to say which produced anything —
which is precisely the position the product is in today with its twenty-one
features. Ship analytics first.

---

## 10. The first four weeks

1. Ship the event schema.
2. Cut onboarding to 10 items and label the Likert anchors.
3. Ship the share-sheet invite with WhatsApp first.
4. Wire Stripe Checkout on the web; no paywall live yet (Paystack cut, D3.0).
5. Write the positioning page — the boundary, the score that can fall, the
   absent streak, the discarded call audio — in plain language, publicly, for
   the first time.
6. Book calls with ten premarital facilitators, starting from the USCCB
   directory (`marketing-copy.md` §15.2).
7. Recruit the first fifty couples by hand and interview two a week.

---

## 11. Claim audit — what is verified, what is not

Added 2026-08-03 at the PM's request, after the Gottman six-year figure turned
out to be debunked. **Nothing marked ⚠️ or ❌ goes into a deck, a landing page,
or a facilitator conversation without being checked first.** Every number in a
strategy doc eventually gets repeated by a founder on a call, which is exactly
how a bad statistic ends up in front of the one person qualified to catch it.

| Claim | Where | Confidence | Note |
|---|---|---|---|
| Couples wait 6 years before therapy | **REMOVED** | ❌ **Debunked** | Gottman & Silver 1999; 2021 *JMFT* replication found ~2.68 years. Never use. |
| The assessment is "**validated**" | **REMOVED** from all copy | ❌ **False** | Ad-hoc subscales, no norming sample, no reliability figures. To a clinician "validated" is a term of art and they will ask for figures there are none of. Copy says "structured, adapted from the Relationship Scales Questionnaire". |
| "14 of 30 items are never read" | **REMOVED** | ❌ **Also false — and it was our own argument** | Withdrawn (D3.37): the scorer reads 17 of 30, and the unread items are unused *by design* — embedded Collins & Read AAS material for subscales this product doesn't compute. Unused ≠ discarded in error. **The "validated" verdict above is unaffected; it never rested on the item count.** Noted here because it is the only error in this document that ran in the direction of *understating* our own product — which is safer, and no more true. |
| Lagos premarital counselling is "compulsory" | **Appendix A** | ⚠️ **Unverified enforcement** | Primary source is the 2022 Lagos MOJ announcement. Policy-on-paper ≠ funnel. Withdrawn from the plan (D3.0); caveat retained in case it is ever revived. |
| Gottman Referral Network lists "thousands" | §6.3(b) | ⚠️ **Corrected** | Directory is public and free; the count was mine and unchecked. Pull a real number before quoting. |
| Prepare/Enrich is "most widely used" | §1 | ⚠️ **Their own claim** | Vendor marketing, not independent. Fine as background, not as fact. |
| Paired: ~8M downloads, ~$200k/mo revenue, 100k daily couples | §2.1 | ⚠️ **Third-party estimates** | From app-intelligence sites (SensorTower/AppstoreSpy-class), not disclosed by the company. Revenue estimates in particular are rough. Directional only. |
| Couples-app market $5.77B by 2033 | §2.1 | ⚠️ **Weak source** | Traced to a competitor's marketing blog citing an unnamed report. Already hedged in text; **do not put this in a deck** — category forecasts persuade nobody who matters and this one won't survive a question. |
| Competitor prices (Paired $14.99, Relish $99.99/6mo, Flamme $4–13) | §2.2 | ⚠️ **Affiliate/review sites** | Not read off the storefronts. Cheap to verify directly and worth doing before any comparison slide. |
| iOS CPI $5.84 / Android $1.92, Q1 2026 | §3.2 | ⚠️ **Single source** | One benchmark report. The conclusion (paid installs unaffordable) is robust to being wrong by 2×, so the decision stands regardless. |
| 17–32 day trials convert at 42.5% | §3.2 | ⚠️ **Single source** | Now moot — there is no trial under the single price. |
| Hard paywall 10.7% vs freemium 2.1%; H&F revenue/download $35.64; H&F trial→paid 35% | §3.2 | ✅ **Solid** | RevenueCat / Adapty industry reports; large samples, primary publishers. |
| Talkspace $436/mo; OurRitual $52–65/wk; couples therapy $100–250/session | §2.2 | ✅ **Solid** | Vendor pricing pages plus independent review corroboration. |
| Prepare/Enrich $35–65 per couple | §1, §5 | ✅ **Solid** | Multiple independent facilitator and parish sources. **The load-bearing comparison for $39 — and it holds.** |
| Nigerian diaspora ~294k UK-born, ~476k US-born | **Appendix A** | ✅ **Solid** | Census-level data. No longer used for targeting (D3.0). |
| Hallow 20M+ downloads, ~$400M valuation, lower parish churn | §2.3 | ✅ **Reasonable** | Contrary Research; secondary but well-sourced. Used as an analogy, not a projection. |
| **Funnel rates in §3.3 (35%/40%/45% → 65%/60%/60%)** | §3.3 | ⚠️ **My estimates** | Not measured — assumptions built from category benchmarks. Explicitly labelled as such. **These are what P0.4's analytics replace, and the whole activation case rests on them.** |
| **COGS $0.60–1.20/couple/month** | §3.1, §5.2 | ⚠️ **My estimates** | Token counts per turn (3k in / 400 out) are assumed, not measured, and one source put gpt-4.1-nano at half the price I used. **Actionable: the engineer can measure real token usage per session and settle this** — it now matters more than it did, because §5.2's cost tail depends on it. |

**Two asks that follow from this table:**

1. **Engineer:** measure real tokens-per-counselling-turn and per-couple monthly
   cost. It converts the largest ⚠️ in the economics into a fact, and §5.2's
   perpetual-access decision depends on it.
2. **Whoever takes the first Nigerian calls:** ask a Lagos marriage official
   whether the premarital requirement is enforced in practice. One question,
   and it either confirms or removes a whole channel.

---

## Appendix A — withdrawn: the regional-entry research

**Status: prepared work for a regional entry nobody has chosen. Not the plan
(D3.0). Retained because it may be right later, and because two findings in it
are load-bearing elsewhere.**

**What still counts as evidence, referenced from §6.3(a) and §7.4:** the RCCG —
a large denomination with parishes across the UK and US — requires intending
couples to complete counselling before the wedding and declines to participate
in the wedding of any couple who has not, *regardless of where the wedding takes
place*, with a published standard manual. That established the **self-enforcing
mandate** property that the global channel case now rests on. Source caveat
unchanged: denominational policy as published by church-affiliated sources, not
audited practice.

**What is withdrawn as targeting:**

- Twelve RCCG diaspora parishes and eight other African-founded churches as the
  first twenty targets.
- Diaspora population sizing (~294k Nigerian-born in the UK, ~476k in the US,
  ~760k by ancestry) as a market-sizing argument.
- Nigeria as a second market, and with it the ₦ price anchors (₦3,900/mo,
  ₦24,000/yr, ₦12,000 pack) — all superseded by the single global $39.
- **Paystack**, cut from P0 (D3.0); Stripe alone covers what is being sold.
- The Lagos State compulsory pre-marital counselling policy and the 2026 digital
  certification programme. **Note the standing caveat if this is ever revived:
  enforcement four years on was never verified, and a policy on paper is not a
  funnel.**

**If a regional entry is ever chosen**, the two things to re-check first are that
enforcement caveat, and whether $39 clears a real institutional budget line in
that market — the consumer certainly cannot reach it.

---

## Sources

- [Paired pricing (LoveFix, 2026)](https://lovefix.app/resources/apps/is-paired-app-worth-it-2026/) · [Paired App Store listing](https://apps.apple.com/us/app/paired-couples-relationship/id1469609343)
- [Paired seed round and growth targets (TechCrunch)](https://techcrunch.com/2021/05/27/paired-pulls-in-3-6m-to-encourage-more-couples-to-get-cosy-with-app-based-relationship-care/) · [Paired company profile (Tracxn)](https://tracxn.com/d/companies/paired/__A1EUzc6NxW3uxdK1QSfoH4Hpt-_fR2UaBLAZ_8-olTE) · [Couple app statistics (Amora)](https://tryamora.app/statistics/couple-apps)
- [Relish pricing (LoveFix, 2026)](https://lovefix.app/resources/apps/relish-app-pricing-2026/) · [Relish Series A (Crunchbase News)](https://news.crunchbase.com/startups/relish-secures-5m-series-a-to-grow-relationship-training-app/)
- [Flamme and AI couples apps (Unite.AI)](https://www.unite.ai/best-ai-apps-for-couples/)
- [Talkspace couples pricing](https://www.talkspace.com/pricing) · [Talkspace couples review (ChoosingTherapy)](https://www.choosingtherapy.com/talkspace-couples-therapy-review/)
- [OurRitual plans](https://www.ourritual.com/plans) · [OurRitual review (ChoosingTherapy)](https://www.choosingtherapy.com/our-ritual-review/)
- [Couples therapy cost 2026](https://costinsighthub.com/us/health/how-much-does-couples-therapy-cost) · [Couples therapy statistics 2026](https://www.connectedcouples.app/blog/couples-therapy-statistics)
- [Prepare/Enrich assessment](https://www.prepare-enrich.com/the-assessment/) · [Prepare/Enrich pricing via Catholic parishes](https://agapecatholicministries.com/product/prepare-enrich/) · [Prepare/Enrich facilitators](https://www.prepare-enrich.com/facilitators/)
- [RevenueCat State of Subscription Apps 2026](https://www.revenuecat.com/state-of-subscription-apps) · [2026 trends summary](https://www.revenuecat.com/blog/growth/subscription-app-trends-benchmarks-2026/)
- [App subscription trial benchmarks 2026 (Business of Apps)](https://www.businessofapps.com/data/app-subscription-trial-benchmarks/) · [Trial conversion rates (Adapty)](https://adapty.io/blog/trial-conversion-rates-for-in-app-subscriptions/)
- [Mobile app marketing benchmarks 2026: CPI by vertical (Admiral Media)](https://admiral.media/mobile-app-marketing-benchmarks-2026/) · [CPI research (Business of Apps)](https://www.businessofapps.com/ads/cpi/research/cost-per-install/)
- [Hallow business breakdown (Contrary Research)](https://research.contrary.com/company/hallow) · [Hallow parish partnerships](https://help.hallow.com/en/articles/14062511-my-parish-just-partnered-with-hallow)
- [Lagos compulsory pre-marital counselling (Lagos State MOJ)](https://lagosstatemoj.org/2022/08/30/lagos-introduces-compulsory-pre-marital-preparatory-counseling-for-intending-couples/) · [Lagos digital pre-marital certification programme, 2026](https://www.thetimes.com.ng/2026/03/lagos-launches-online-pre-marital-course-for-pastors-imams-marriage-counsellors/)
- [Nigerian diaspora populations (NGEX)](https://ngexglobal.com/where-nigerian-immigrants-are-nigerian-diaspora-by-country/) · [British Nigerians](https://en.wikipedia.org/wiki/British_Nigerians) · [Nigerian Americans](https://en.wikipedia.org/wiki/Nigerian_Americans)
- [Nigeria streaming subscription prices](https://www.naijatechguide.com/showmax.html) · [Netflix Nigeria pricing](https://siliconafrica.org/netflix-subscription-plans/)
- [Gottman Referral Network](https://gottmanreferralnetwork.com/) · [Therapist review of relationship apps](https://www.southdenvertherapy.com/blog/do-relationship-apps-work-therapist-review)
- [OpenAI API pricing 2026 (CloudZero)](https://www.cloudzero.com/blog/openai-pricing/) · [GPT-4.1-nano pricing](https://pricepertoken.com/pricing-page/model/openai-gpt-4.1-nano)
