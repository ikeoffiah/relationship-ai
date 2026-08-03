# Bliss — distribution strategy to the first 1,000 customers, and pricing

Written 2026-08-03. Companion to `docs/product-assessment.md`, which covers the
product itself. This document covers the two things that assessment identified
as unstarted: **who finds this product, and what they pay for it.**

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

One open question the founder did not answer: **which market is first.** So §5
prices all three candidate markets and §7 makes a recommendation with reasoning.
The distribution plan in §6 is written for a bootstrapped-to-modest budget; §6.7
says what changes with real money.

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
validated attachment items, a communication-style quiz, cultural and faith
context, producing a per-partner portrait. Product-wise this is currently a
liability — 40 taps before any value (§2.2 of the assessment). Commercially it
is the single most sellable artefact in the codebase, because assessments are
what institutions buy. Prepare/Enrich sells essentially this — an assessment
plus a workbook plus a facilitator report — for **$35–$65 per couple**, and it
is the most widely used premarital instrument in the world.

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
- **A therapist portal with a consent gate**, i.e. a B2B2C surface.

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

## 5. Pricing strategy

### 5.1 The structure

**One subscription per couple. Both partners covered. Always.**
Non-negotiable — it is the category norm, and per-person pricing would tax the
pairing loop that the whole product depends on.

**Three tiers, plus two institutional SKUs.**

#### Free — "the loop"
Daily question and the two-sided reveal. Daily check-in. Connection score.
Commitments. Safety resources. Basic games.

This tier is not charity; **it is the acquisition engine.** The reveal only
works if both partners are in, and you cannot ask someone to pay before their
partner has arrived. Never paywall anything that partner B needs in order to
join, and never paywall the safety surfaces.

#### Bliss Premium — the couple subscription
**$14.99/month or $89.99/year** (~$7.50/mo, 50% saving).

Unlimited AI sessions (private and joint), tone coach and "say it better",
weekly insights, the full games and question library, faith tab, Focus mode,
history, and full personalisation.

Why these numbers: $14.99/mo sits exactly at Paired's price, which is the
anchor buyers already have. $89.99/yr sits *above* Paired's $69.99–83.99 —
justified, because Paired has no AI counsellor — while staying under the $99.99
that Relish charges for six months. Annual should carry ~70% of revenue: Health
& Fitness, the closest analogue, takes 60.6% of revenue from annual plans and
has the category's best revenue-per-download.

#### Bliss Together — the guided tier *(build only after Premium works)*
**$49/month.** Premium plus a connected human — a monthly 30-minute session with
a coach or therapist through the existing therapist portal, plus their notes and
their view of the couple's progress.

This is the $15-to-$436 gap. OurRitual charges $52–65/*week* for a
similar hybrid; Talkspace $436/month. $49/month with one short session is
defensible, differentiated, and it turns the therapist portal from dead code
into a revenue line. Do not build this until Premium has 300+ paying couples;
it introduces supply-side operations and clinical liability.

#### Institutional SKU 1 — Premarital Pack
**$39 one-off per couple** (US/UK) — assessment, portrait, an 8-session guided
curriculum, a facilitator report, and a completion certificate. Sold to and
through churches, premarital programmes and marriage registries; includes 6
months of Premium.

This is priced deliberately inside Prepare/Enrich's $35–65 band, against which
it has a real advantage: theirs is a PDF and a workbook, yours is an app the
couple keeps using afterwards. **The one-off has no churn problem and comes with
a distributor who assembles the couples for you.** Facilitator seat: free, or
$99/year for cohort management.

#### Institutional SKU 2 — Therapist seats
**Free for the therapist, always.** Client couples get Premium at $9.99/month
(a third off) while connected. Optionally $29/therapist/month later for
caseload tooling.

Never charge the referrer. A therapist recommending a between-session tool is
doing you a $0-CAC favour worth 15–30 couples; a $29 invoice converts that
favour into a purchasing decision and kills it.

### 5.2 The paywall mechanic — a specific recommendation

The benchmark data says hard paywalls beat freemium 5:1. The product says a
two-sided app must be free until both partners are in. Resolve it by **moving
the paywall from install-time to moment-of-need**:

- No paywall at install, none during onboarding, none before pairing.
- The AI counsellor is gated behind a **30-day trial that the user starts by
  opening a session** — not at signup. Trials of 17–32 days convert at a median
  **42.5%**, far above short trials, and a couple who opens a counselling
  session after a fight is the highest-intent user this product will ever have.
- The trial is per couple, and either partner can start it.
- Ask for the card up front (opt-out trial), with the standard reminder before
  charge.

This gets the hard-paywall conversion profile on the monetising surface while
keeping the viral surface free.

**One product constraint that overrides revenue:** never paywall or trial-gate
the safety path, the crisis resources, or anything reached from the support
icon. A product that gates help behind a card at the moment someone needs it is
a scandal waiting to happen, and it would contradict the one thing that makes
this product distinctive.

### 5.3 Market-specific pricing

| Market | Monthly | Annual | Premarital Pack | Rails |
|---|---|---|---|---|
| US / UK / CA / AU | $14.99 | $89.99 | $39 | App Store / Play IAP |
| Nigeria & Africa | **₦3,900** | **₦24,000** | **₦12,000** | Paystack / Flutterwave, web checkout |
| Diaspora (US/UK) | Same as US/UK | Same | Same | IAP |

The Nigerian number is anchored against what Nigerians already pay monthly:
Showmax ₦4,500, Netflix ₦2,500–8,500, Spotify ₦1,600. ₦3,900 for a couple —
under ₦2,000 per person — is a defensible position between Spotify and Showmax.

But be clear-eyed: Nigerian ARPU is structurally low and naira devaluation means
subscription revenue growth chronically lags subscriber growth across the
region. **In Nigeria the one-off Premarital Pack will outsell the subscription,
probably by a lot**, and the gifting SKU below matters more than it does in the
West.

**Take App Store IAP seriously as a cost.** 30% (15% under the Small Business
Program, which you qualify for) comes off every $14.99. Push annual, and for the
institutional SKUs sell on the web where Apple's cut does not apply.

### 5.4 Two mechanics worth building

**Gifting.** "Give Bliss" as a wedding or anniversary gift — a purchasable code
for 12 months. Couples products are among the most giftable software there is,
the buyer is not the user (so price sensitivity drops), and in Nigerian wedding
culture especially, a gift SKU sold alongside a premarital pack is a natural
fit.

**The couple code.** Every paying couple gets a code for 30 days free for
another couple. Loop 2, made concrete.

### 5.5 What not to do

- **No streaks-for-discounts, no engagement-linked pricing.** The team correctly
  deleted the streak. Reintroducing it through billing would be worse.
- **No per-message or per-session credits on the counsellor.** Metering therapy
  by the message makes people ration the thing they need. Margin is 90%+; there
  is no cost argument for it.
- **No "unlock your partner's profile" tier, ever.** `boundary.py` exists
  precisely to prevent this and the reasoning in `docs/outcome-loop.md` is
  right: an inferred model of one partner shown to the other is a manipulation
  manual. It would also be the single most tempting upsell in the product.
  Write the prohibition down before someone proposes it in a growth meeting.

---

## 6. Distribution: the road to 1,000 paying couples

### 6.0 Definition and honest timeline

**Target: 1,000 paying couples** ≈ 2,000 users ≈ **$90k–150k ARR** at the
pricing above, depending on annual/monthly mix and market.

Realistic timeline on a bootstrapped budget, assuming the Phase 0 fixes land:

- **Month 3:** 100 paired couples, 0 paying (no paywall yet)
- **Month 6:** 500 paired couples, ~120 paying
- **Month 9:** 1,400 paired couples, ~420 paying
- **Month 12:** 3,000 paired couples, **~1,000 paying**

Twelve months, not six. Anyone promising 1,000 paying couples in a quarter on
this budget is promising paid installs you cannot afford. The Phase-0 activation
fixes are what make the twelve-month number achievable rather than optimistic.

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
   first — decisive in Nigeria and among diaspora, and the deep link already
   works). Let partner B see the blurred question before onboarding.
4. **Ship billing** — RevenueCat for IAP, Paystack for the African web SKUs.
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
- Three couples-therapists, recruited by cold outreach, each bringing 3–5
  clients onto the therapist portal.
- One premarital cohort (see §6.3).

What you get: the activation numbers in §3.3 replaced with real ones, the first
churn signal, the language couples actually use to describe the problem — which
becomes your ad copy, your App Store subtitle and your creator brief — and the
answer to which of the twenty-one feature areas anyone touches.

**Gate to Phase 2:** ≥60% of installs pair, ≥40% of paired couples still active
in week 4, and at least 15 couples who say they would pay.

### 6.3 Phase 2 — weeks 8–24: institutions, ~350 couples

The highest-yield, lowest-cost channel available, and the one Bliss is uniquely
built for. Three sub-channels.

**(a) Premarital programmes and churches — target 200 couples**

Every engaged couple in a church programme is a couple that has already agreed
to do relationship work on a schedule, assembled into cohorts of 10–60, with a
facilitator who is looking for better materials. This is the single best-matched
audience for the assessment + portrait + curriculum that Bliss already has.

- **Nigeria is unusually favourable.** Lagos State introduced compulsory
  pre-marital preparatory counselling for intending couples, delivered by
  marriage officials across all twenty LGAs and LCDAs on an eight-week
  curriculum, and in 2026 launched a digital pre-marital certification programme
  training pastors, imams and marriage counsellors. That is a state-mandated,
  digitally-minded, eight-week funnel of couples with a counsellor attached —
  and Bliss is an eight-week, faith-aware, assessment-led curriculum in an app.
  Approach the certified-counsellor cohort, not the state, first.
- **Diaspora churches** (RCCG, Winners, Catholic parishes, Anglican) in London,
  Houston, Dallas, Maryland, Atlanta run premarital classes constantly and serve
  a population with Western wallets and the cultural framing Bliss already
  models. There are ~294k Nigerian-born residents in the UK and ~476k in the US
  (~760k by ancestry).
- **US Catholic parishes** already buy Prepare/Enrich at $35–65 a couple, so the
  budget line exists and the price is established.

Pitch to the facilitator, never to the couple: *"Your couples get the assessment
and a report you can teach from, and they keep the app after the wedding."*
Free facilitator seat, cohort dashboard, $39/couple.

Target: 5–8 cohorts, 25–40 couples each, ~60% activation = ~200 couples.

**(b) Couples therapists — target 100 couples**

The therapist portal already has the bilateral consent gate that makes this
safe. Therapists recommend between-session tools routinely; the Gottman Referral
Network alone lists thousands of trained couples clinicians, publicly and free
to search.

Cold-outreach 100 therapists with a specific, honest offer: free therapist
account, their couples get Premium at $9.99, they get the couple's shared
progress with both consents, and — the actual hook — *"the model never shows one
partner an inference about the other; here is the code that enforces it."*
Clinicians care about that boundary more than any feature.

Expect 10–15% to try it; each active therapist brings 5–10 couples. ~100 couples,
and materially better retention than self-serve.

**(c) Wedding-adjacent — target 50 couples**

Wedding planners, registries, bridal fairs and wedding-content creators, with
the gifting SKU. High in Nigeria and diaspora where wedding spend is
concentrated and communal.

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
r/CouplesTherapy, Nairaland's family section, and — decisively for Nigeria and
diaspora — WhatsApp and Facebook groups. Organic Reddit rewards genuine
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
| Premarital cohorts | 200 | ~$0 + time | 4–8 weeks | **High** — budget and behaviour exist |
| Therapist referrals | 100 | ~$0 + time | 6–12 weeks | Medium-high |
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

## 7. Which market first — the recommendation

**Diaspora-first, US/UK, with the premarital pack as the wedge.**

The reasoning:

- **Western pricing, community distribution.** You get $14.99/month and $39
  packs, but you reach them through church and community networks rather than
  through $5.84 CPIs. That is the only combination that closes the CAC gap in
  §3.3 on a bootstrapped budget.
- **The differentiators fire natively.** Faith tab, cultural framing, communal
  family orientation, dense premarital-class culture. Against Paired and Relish
  in the general US market you are a worse-funded me-too with an AI feature.
  Against them in Nigerian and African diaspora churches in Houston, London and
  Atlanta, you are the only product that was built for those couples.
- **It is a beachhead, not a ceiling.** Winning a defined community first is
  how you earn the general market later, and the same product ships to both.
- **Nigeria is the second market, not the first, and it is mostly a one-off-
  purchase market.** Lagos's compulsory premarital counselling and the 2026
  digital certification programme make it strategically valuable — but naira
  ARPU and devaluation mean the subscription will underperform, and you should
  enter it with the ₦12,000 Premarital Pack through certified counsellors, not
  with a ₦3,900/month subscription through the App Store.
- **The pure US/UK general market is the most expensive path** and the one where
  your unique assets count for least. Enter it in year two, via the therapist
  channel and creator content, once the loops are proven.

---

## 8. The numbers to watch

Five, and only five, until 1,000:

| Metric | Target | Why |
|---|---|---|
| **Install → paired couple** | >20% | The single multiplier on every channel |
| **Invite send rate** | >60% of activated | Loop 1's health |
| **Invite accept rate** | >60% | Loop 1's health |
| **Week-4 couple retention** | >40% | Whether the loop holds without a streak |
| **Trial → paid** | >35% | Whether the AI counsellor is worth $14.99 |

Add one qualitative gate: **two couple interviews per week, every week, written
down.** The assessment is right that reasoning quality has carried this product
a long way without feedback, and right that it does not scale.

---

## 9. Risks

**App Store review and clinical claims.** Apple scrutinises mental-health apps.
Never say "therapy" or "counselling" in metadata where it implies licensed care;
the in-app disclosure already exists and is correct. The safety classifier and
`VALIDATION.md` are assets in a review conversation — have them ready.

**Safety liability at scale.** The three-layer classifier is gated at ≥90%
clear-crisis recall with zero tolerated false positives on safe messages. At
1,000 couples you will see cases the eval set does not contain. Budget for
human review of every escalation and keep the paraphrase-recall gap in
`VALIDATION.md` visible.

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
4. Wire RevenueCat and Paystack; no paywall live yet.
5. Write the positioning page — the boundary, the score that can fall, the
   absent streak, the discarded call audio — in plain language, publicly, for
   the first time.
6. Book calls with five premarital facilitators and ten couples therapists.
7. Recruit the first fifty couples by hand and interview two a week.

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
