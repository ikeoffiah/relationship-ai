# Bliss — App Store listing, landing page, and outreach copy

Written 2026-08-03. Companion to `docs/go-to-market.md`.

Everything here is copy, not code. It exists because `pubspec.yaml` currently
says *"A new Flutter project."* and there is no public sentence anywhere
describing what Bliss is.

**The single message.** Every asset below is a different length of the same
claim, which is the one thing no competitor can copy quickly:

> Bliss helps two people understand each other — and it will never tell one of
> you what it thinks about the other.

That is literally true and enforced in code (`personalization/boundary.py`,
with an adversarial test). It is unusual enough to be worth leading with, and it
answers the objection every couple has about this category before they raise it.

---

## 1. App Store / Play listing

### Name (30 char limit)

| Option | Chars | Note |
|---|---|---|
| **`Bliss: Couples & Marriage`** | 25 | **Recommended.** Mirrors the category leader's construction ("Paired: Couples & Relationship"), carries two keywords. |
| `Bliss: For Couples` | 18 | Cleaner, one keyword fewer. |
| `Bliss: Couples Counselling` | 26 | **Avoid.** See §1.5. |

### Subtitle (30 char limit)

Three options, deliberately testing different promises. The $50 ad test in §2
should pick the winner before you commit.

| Option | Chars | Angle |
|---|---|---|
| **`You both answer. Both unlock.`** | 28 | **Recommended.** The mechanic, which is what D5 puts on consumer surfaces. Concrete, and it describes something no competitor does. |
| `Talk better. Nothing shared.` | 28 | Boundary-led. Was the recommendation before D5; keep for professional surfaces. |
| `Before and after the wedding` | 28 | Premarital. Use if the facilitator channel is the primary funnel. |

### Keywords (100 chars, comma-separated, no spaces)

```
couples,marriage,relationship,partner,communication,premarital,connection,love,husband,wife
```

Deliberately omits **therapy**, **counseling** and **mental health** — see §1.5.

### Description

First three lines are all most people read. They must carry the hook alone.

```
Bliss is for two people who want to understand each other better.

Every day, you each answer one question privately. Neither of you sees the
other's answer until you've both replied — so nobody is reacting, everybody is
answering honestly.

And here is what Bliss will never do: it will never show one of you what it
thinks about the other. Not your patterns, not your profile, not a summary of
what you said in private. That isn't a setting you have to find. It's built
into how the app works.

WHAT YOU GET

• A daily question you both answer — revealed only when you're both in
• A private space to think out loud, with an assistant trained to help you say
  the hard thing more kindly
• Games, Two Truths, and shared plans for the lighter days
• A connection score built from what you actually do together — one that is
  allowed to go down, and that stays quiet on a bad week
• An optional daily reading, if faith is part of your relationship

WHAT YOU WON'T GET

• No streaks. We built one, then took it out. A consecutive-day counter turns
  how often two people tap a phone into a proxy for how they are doing — and
  the week one of you is ill, it hands you a number saying you broke something.
  You'll see "together 12 of the last 30 days" instead. A missed day simply
  doesn't add to it. It can't take away the days that happened.
• No notifications designed to make you anxious.
• We will never show one of you a profile of the other built from your private
  activity — not to you, not to anyone. The only thing anyone else ever sees is
  the assessment you both chose to take, in a report you both receive.

Bliss is not therapy and it isn't a replacement for a therapist. If you're in
crisis, support resources are one tap from every screen, always, whether or not
you ever pay us anything.
```

⚠️ **Hold this description until P0.10 lands.** "Support resources are one tap
from every screen" is currently false — `SupportAction` covers 11 of 53 screens,
including none of the six onboarding screens. The engineer is making it true
rather than us softening it. Do not submit before then. Same guard as §7.

### 1.5 A warning about metadata

Apple scrutinises mental-health apps. **Do not put "therapy", "counselling",
"treatment" or any clinical outcome claim in the name, subtitle, or promotional
text.** The existing in-app disclosure ("You are talking to an AI, not a
licensed therapist") is correct and should stay — it helps in review.

Have `VALIDATION.md` and the three-layer safety classifier ready to cite if
review asks. That documentation is an asset in that conversation, not a
liability.

### 1.6 Screenshots — shoot these five, in this order

1. **The reveal.** Both answers side by side. This is the product.
2. **The waiting state.** "You've answered. We'll show you both when Sam's in."
   Sells the mechanic in one image.
3. **The private session**, mid-conversation — but only *after* the four chrome
   bars are collapsed and the empty state is fixed.
4. **The boundary**, as a plain statement on a plain background. No UI.
5. **The daily reading**, for the faith and premarital audience.

Do not ship screenshots of the current onboarding. It is the weakest surface in
the product and it is 40 taps long.

---

## 2. Landing page — three variants for the $50 message test

One page, one email field, no navigation. Run all three at ~$17 each and compare
cost per email. **What you are buying is the answer to "which sentence makes a
stranger stop", not users.**

### Variant A — the mechanic *(re-cut per execution-plan D5)*

Originally written boundary-first. Changed: on a consumer surface a cold
negative claim about profiling can create the anxiety it answers. The mechanic
leads; the boundary lands as the closing line, as a reassurance rather than a
warning.

> **You both answer. Neither of you sees the other's answer until you have.**
>
> One question a day. You answer privately, they answer privately, and it opens
> for both of you at the same moment — so nobody is reacting to anybody, and
> both of you are answering honestly.
>
> Nothing you say gets used against you.
>
> `[ email ]  Get early access`

### Variant B — premarital

> **Find out how you two actually handle conflict — before the wedding.**
>
> A short assessment for both of you, and a portrait of how each of you handles
> closeness and conflict. Adapted from the Relationship Scales Questionnaire. Then
> a question a day, answered privately and opened together, for as long as you
> want it.
>
> $39 once, for both of you. No subscription.
>
> `[ email ]  Start the assessment`

### Variant C — the price anchor

> **Couples therapy costs $200 an hour, and most couples wait years to book it.**
>
> Bliss is a daily practice for the years in between: one question you both
> answer, a private place to think out loud, and help saying the thing you
> can't quite phrase.
>
> Not therapy. Not a replacement for it. Something for the other 364 days.
>
> `[ email ]  Get early access`

**Measure:** cost per email by variant, and nothing else. Ignore volume.

**Variant C — the six-year figure is checked, and it is wrong. Do not use it.**
"The average couple waits six years before seeking therapy" comes from Gottman &
Silver, *The Seven Principles for Making Marriage Work* (1999), and it is
repeated everywhere. A 2021 peer-reviewed replication in the *Journal of Marital
and Family Therapy* found the real interval is **~2.68 years**, with the great
majority of couples entering therapy within two years.

So the copy now says "years" without a number. If you want a number, use **"about
two and a half years"** and cite Doherty (2021) — weaker as a hook, but true, and
half your professional audience knows the six-year claim has been challenged.
Quoting a debunked Gottman statistic to a Gottman-trained facilitator is the
worst possible first impression.

### 2.1 What the email sequence can and cannot do

Three emails, and only one job: **get the person to invite their partner.**

Bliss cannot convert a single person. The purchase event needs two people, and
your list only ever contains one of them. So the sequence is not a nurture
funnel, it's an invite prompt with better manners.

1. **Immediately** — what Bliss is, in four sentences, plus the boundary.
2. **Day 2** — "The daily question only works if you're both in. Here's the
   link to send them." *One button. This is the whole email.*
3. **Day 5** — one concrete thing the product does (say-it-better, or the
   assessment), then the same link again.

Stop after three. A person who hasn't invited their partner in five days is
not a customer yet, and emailing them again won't change that.

---

## 3. Facilitator outreach email

For premarital-class leaders and marriage-preparation coordinators, in any
English-speaking market. Send individually. Never BCC.

**Subject:** `Premarital assessment tool — looking for one class to test it`

```
Hello [name],

I've spent the last four months building a premarital tool and I'm looking for
one real class to test it with. I found you through [specific: their parish
marriage-prep page / the facilitator directory / the certification cohort].

What it does: each couple takes a short assessment on attachment and
communication style, and you get a report per couple you can teach from. After
the wedding they keep the app — a daily question they both answer, and a place
to work through things.

What I'm asking: one cohort, one term. I'll set every couple up myself, sit in
if that's useful, and fix anything that breaks the same day.

What it costs you: your first cohort costs you nothing. Couples pay $39 once —
no subscription and nothing to cancel. If it's useless after one session, tell
me and I'll leave you alone.

Would a 20-minute call be worth your time?

[name]
[phone] · [link]
```

**Be straight about the $39.** An earlier draft of this email said "I'm not
selling anything yet." That was true of a licence and false of the couples, and
a facilitator who discovers the price after recommending you to their class will
never recommend you again. The honest version is also the stronger one: $39
once, no subscription, is a *better* deal than the $35–65 their couples already
pay for Prepare/Enrich, and saying so early is the pitch rather than a
concession.

**Why this works at zero downloads.** It asks for a trial, not a purchase — so
there is no budget decision and nothing to scrutinise. It offers labour, which
facilitators never get from Prepare/Enrich. And it names a specific reason you
contacted *them*, which is the difference between outreach and spam.

**Do not** claim users you don't have, describe it as "launching soon", or
attach a deck. The honest version converts better here, and getting caught
inflating traction with the exact person whose trust you need is unrecoverable.

**Volume:** ten emails, expect one yes. One yes is 20–40 couples — more than
the entire hand-recruitment phase.

---

## 4. The second-degree intro ask

For friends. The point is that the friend brokers and someone else participates,
so you are never the person watching a marriage you're socially inside of.

> "I've been building something for couples — it's a daily question you both
> answer, plus help with the conversations that are hard to start. Do you know
> anyone who got engaged recently? I'm trying to find ten couples who'll tell me
> honestly where it's creepy or useless."

Three things this does deliberately: it targets **engaged** couples, where the
surveillance reading doesn't arise; it asks for an **introduction**, not
adoption; and the request is **criticism**, which people enjoy giving and which
carries no obligation to like you afterwards.

---

## 5. What not to say, ever

- **"AI therapist", "AI counsellor", "digital therapist"** — untrue, and an App
  Store review problem.
- **Any outcome claim** — "saves marriages", "couples report 40% more…". You
  have no data, and in this category a fabricated outcome claim is the kind of
  thing that ends a company.
- **"Know what your partner is really thinking"** — the single most tempting
  line in this market and the exact thing the product refuses to do. Writing it
  would sell the opposite of what you built.
- **Anything implying surveillance, monitoring, or checking up.** Not "see how
  your relationship is really doing" — that reads as a scorecard on a person.

---

## 6. Open questions

- **App name conflict — checked, and "Bliss" is crowded.** Live in the same
  space today: *Bliss Dating App: Chat & Date* (Google Play, actively updated,
  v2.9.1 in Feb 2026), *Bliss — The Game for Lovers*, *Bliss by Games for
  Loving*, and *Bliss Cruise*. Two consequences: you will not rank for the bare
  term "bliss", and — worse — the strongest namesake is a **dating** app, which
  is the one adjacency this product cannot afford, since Bliss is for people who
  already found each other.

  **My recommendation: do not rename now, and do not let this block P0.** Under
  execution-plan D1 the next 90 days sell on the web, where the store name is
  irrelevant, and the in-product assistant is called `@bliss` throughout the
  code, the notification types and the database — renaming is a real cost during
  a feature freeze. The store name only has to be decided before P1 store
  metadata. When it is, differentiate in the name itself (`Bliss Couples`,
  never bare `Bliss`) and rank on `couples` / `premarital` keywords rather than
  on the brand term, which was never going to carry ASO anyway. Bundle ID
  `co.owjar.bliss` is unaffected either way.
- **Which subtitle wins** — decided by §2, not by opinion.
- **Whether to lead with premarital or general couples.** The strategy doc
  recommends premarital, because that's where the distribution is. If §2 says
  Variant A beats Variant B on cost per email, that's evidence the general
  positioning is stronger and the doc should change.

---

## 7. The consumer landing page — `/`

Mechanic-led per execution-plan D5. One page, one action.

> # You both answer. Neither of you sees the other's answer until you have.
>
> One question a day. You answer privately, they answer privately, and it opens
> for both of you at the same moment — so nobody is reacting to anybody, and
> both of you are answering honestly.
>
> **[ Get Bliss — $39 ]**
> One payment. Both of you. No subscription.
>
> ---
>
> ### What you get
>
> **An assessment, and what it found.** Twenty minutes each. You each get a
> portrait of how you handle closeness, conflict and repair — yours, about you.
>
> **A question every day.** Answered privately, unlocked together.
>
> **Somewhere to think out loud.** A private space to work through the
> conversation you're dreading, and help saying it more kindly when you're
> ready to have it.
>
> **The lighter things.** Games, Two Truths, plans you make together.
>
> ---
>
> ### What Bliss will never do
>
> It will never show one of you what it thinks about the other. Not your
> patterns, not your profile, not a summary of what you said in private.
>
> There is no streak. A week where one of you was ill is not a failure and we
> won't put a number on it.
>
> **[ Get Bliss — $39 ]**
>
> ---
>
> Bliss is not therapy and it is not a replacement for a therapist. If you're in
> crisis, support resources are one tap from every screen — always, whether or
> not you've paid us anything.

> ⚠️ **"one tap from every screen" is not true yet** — `SupportAction` is on 11
> of 53 screens, and the six onboarding screens, where someone answers thirty
> items about abandonment and rejection, are among the uncovered. The engineer
> is making it true (P0.10). **Do not publish this page, or submit the App Store
> description, until that lands.** If it slips, the fallback wording is
> "support resources are always reachable" — but fixing it beats describing it
> accurately, and it is a safety gap independent of the copy.

**Why the negative section survives here but not in the headline.** D5 is about
what *opens* the page. By the time someone has read what the product does, "here
is what it will never do" reads as a promise rather than as a warning about a
danger they hadn't considered. Order is the whole difference.

---

## 8. The facilitator page — `/for-facilitators`

Boundary-led per D5, and **no price list** — per D2.1 the ladder is a
negotiating reference, not published. One action: book a call.

> # For people who run premarital classes
>
> Your couples take a structured attachment and communication assessment,
> adapted from the Relationship Scales Questionnaire. You get a report per
> couple you can teach from. After the wedding, they keep the app.
>
> **$39 per couple. Your first cohort costs you nothing.**
> The assessment, portraits, report and certificate are theirs to keep. The AI
> counsellor runs for 12 months.
>
> **[ Book 20 minutes ]**
>
> ---
>
> ### Why clinicians and counsellors tend to ask about this first
>
> **One partner's profile is never shown to the other.** Not as a setting — as a
> single enforced boundary in the code, with a test that tries to break it and
> fails. What Bliss infers about someone is used to help *them* communicate, and
> is never surfaced to their partner.
>
> **And that includes what we show you.** I can tell you who's finished, so you
> can chase them. I can't tell you what any couple answered — not to you, not to
> anyone. If I'd build that for you, you'd be right to wonder what I'd tell
> someone else about your couples.
>
> **If faith is part of your programme, it's part of the app.** An optional
> daily reading and practice, tradition-tagged, with one rule written into it:
> faith framing is never used to pressure anyone to stay in an unsafe
> relationship. Faith-based preparation is how most premarital counselling in
> the world is actually done — this was built for it, not adapted to it.
>
> **The connection score is built from what a couple does, not from what either
> of them privately reported** — because averaging two private check-ins
> publishes one partner's answer to the other by arithmetic. It can go down. It
> goes quiet on a bad week, because the morning after a fight someone opening
> the app for help should be met with something useful, not a low number.
>
> **Nothing that reaches crisis support is ever behind a payment** — paid,
> unpaid, refunded or expired, it makes no difference.
>
> That is not a policy we're asking you to trust. There is a test that fails the
> build if a paywall, a trial wall or an entitlement check appears anywhere on
> the crisis path. And because a test that passes proves nothing on its own,
> there is a second set of tests that deliberately plant such a gate — in the
> support icon, one import away, next to a mount point — and fail if the first
> test doesn't catch it.
>
> The billing code isn't written yet. The test is already there, and it fails
> the moment billing appears without a runtime check beside it, so the
> protection arrives with the risk rather than after it.
>
> ---
>
> ### What running a cohort looks like
>
> 1. A 20-minute call. Tell me what your programme already does.
> 2. Your couples get a link. They pay $39 each; you pay nothing.
> 3. Each couple's report reaches you before the session you'd teach it in.
> 4. I'm reachable the whole time and I fix what breaks the same day.
>
> **[ Book 20 minutes ]**

---

## 9. Checkout

> ### Bliss — $39
> One payment. Covers both of you. No subscription, nothing to cancel.
>
> - The assessment and your portraits — **yours to keep**
> - Your report and certificate *(and your facilitator's copy, if you came from
>   a class)* — **yours to keep**
> - The daily question and everything you do together — **yours to keep**
> - The AI counsellor — **for 12 months**
>
> `[ card fields ]`
>
> **[ Pay $39 ]**
>
> 30 days, full refund, no questions asked.
> Questions before you buy? [email] — a person answers.

Three requirements on the build, all of which cost sales if missed:

- **$39 is global**, one currency, no geo-pricing. Simplicity is the SKU.
- **State the 12-month counsellor bound at the point of sale, never after.**
  (D3.11a — unlimited permanent counselling against a one-off price is
  unbounded cost.) It is disclosed in the same breath as the price, alongside
  three things that *are* permanent, which is why it reads as scope rather than
  as a catch. A time bound discovered in month 13 is the same category of
  problem as the curriculum that did not exist.
- **Offer bank transfer / invoice alongside card.** Churches and NGOs frequently
  cannot pay by card. Stripe invoices cover this; Paystack is cut (D3.0).
- **The 30-day refund is not decoration.** At zero downloads and no reviews it is
  the cheapest objection-killer available, and a one-off purchase makes it safe
  to offer — there is no subscription for a refunded buyer to keep using.

---

## 10. After payment — the couples-pay gap

**This is the highest-risk copy in the funnel and it is new.** Under
couples-pay, partner A pays and partner B has not arrived. The money is already
collected, so the risk is not lost revenue — it is a couple who paid $39 and
never got the product, which means **a facilitator whose class paid and got
nothing, who never runs cohort two.** Per §6.0 of the strategy doc, cohort two
is where all the compounding lives. So this screen is load-bearing on the
21-facilitator model, not a receipt.

### The confirmation screen — one action only

> # You're in. Now bring them.
>
> Your $39 covers both of you — they don't pay anything.
>
> Bliss needs two people. Your daily question is waiting, and it opens for both
> of you the moment they answer too.
>
> **[ Send the link ]** *(WhatsApp, Messages, anything)*
>
> ---
>
> **They won't see your answers.** Not the ones you've already given, not the
> assessment, not anything you write privately. They'll see today's question,
> the same as you.
>
> *Meanwhile — your assessment is ready. You don't have to wait for them.*

Three deliberate choices: **one button**, because a confirmation page with four
options converts on none of them; **the "they won't see your answers" line**,
because it is the exact fear that stops someone sending the link and it costs one
sentence to remove; and **the solo fallback**, because "waiting on your partner"
as a dead end is, per the product assessment, the fastest way to make someone
stop opening an app.

### The nudge sequence

Only if the partner hasn't joined. Three, then stop.

| When | Message | Purpose |
|---|---|---|
| **+24h** | "Your assessment is ready to read. [Partner] hasn't joined yet — here's the link again." | Value first, ask second |
| **+72h** | "Bliss works better with two, but it works alone too. Here's what your portrait says about how you handle conflict." | Deliver something real; re-offer the link |
| **+7 days** | "Still here whenever they are. Or reply to this and tell me what got in the way." | Last one, and it doubles as discovery |

Stop at three. Someone who hasn't invited their partner in a week is not
converting on a fourth email, and this is a product about not nagging people.

### Requirements this implies

Handing these to the engineer as spec, not building them:

- **Purchase covers a couple, not a person.** Partner B redeems into A's
  purchase and never sees a paywall.
- **Both-partners-paid edge case.** Two people in the same class may each buy
  before pairing. Detect it at pairing and refund one automatically — do not
  make them ask. Getting this wrong in a cohort is visible to the facilitator
  immediately.
- **The share action is the same share sheet as P1's in-app invite.** Build once.
- **A couple who never pairs must still get the assessment and private
  sessions.** Otherwise the refund rate is the pairing failure rate.

---

## 11. What the facilitator needs between cohorts

Answering the PM's question. Right now nothing in the product knows a
facilitator exists between cohorts, and per §6.0 the second cohort is where the
entire model compounds. The minimum, in priority order:

1. **A reason to be in touch that isn't a sale.** After a cohort closes, send the
   facilitator an anonymised summary of what their class actually did —
   completion rate, which items the group scored lowest on. It is genuinely
   useful teaching material, it proves the tool worked, and it arrives without
   asking them for anything. Nothing identifies a couple.
2. **A standing link of their own.** One URL they reuse every term, so cohort two
   costs them a paste rather than a conversation. This alone probably decides
   whether ≥3 cohorts/year happens.
3. **Their name on the report.** Cheap, and it makes the artefact theirs.
4. **A calendar nudge before their next term starts**, timed to their cadence —
   which means asking on the first call when their programme runs.

Items 1 and 2 are the ones with revenue attached. Both are small.

---

## 12. The first facilitator call — script and the one question that decides P1

Twenty minutes. The sale is the second-most valuable thing this call produces.

### Before you say anything about Bliss

Two minutes of them, first. It is not warm-up — the answers set the price path
and the cadence you need for §11.

1. "Walk me through your programme — how many couples, how many sessions, how
   often does it run?" *(→ cohort size, and cohorts/year, which is the §8 metric)*
2. "What are you using now — Prepare/Enrich, your own material, something else?"
3. "Who pays for it today, the couples or the church?" *(→ decides invoice vs
   couples-pay before you have to guess — D3.8)*

### What to say Bliss is — and nothing more

> "Each couple takes a short assessment on attachment and communication style.
> You get a report per couple you can teach from. They keep the app afterwards —
> a question a day they both answer privately, and it opens for both of them
> once they've both replied. $39 per couple — your first cohort costs you
> nothing. The assessment, portraits, report and certificate are theirs to
> keep; the AI counsellor runs for 12 months."

**Do not say curriculum. Do not say certificate. Do not say eight weeks.**
Neither the curriculum nor the certificate exists yet (§5.0 of the strategy
doc). If they ask directly: *"Not yet — a completion certificate is being built
now. The eight-week question is actually what I wanted to ask you about."*

### The question that decides what we build next

Ask it straight, and let them talk:

> **"You already run an eight-week course. Would you rather have a programme to
> run — or materials that drop into the one you've already got?"**

Then: *"What would have to be true for you to use it next term as well as this
one?"*

We do not know the answer and we should not pretend to. Building an eight-week
programme before asking is exactly the failure `product-assessment.md` §2.14
describes — a good decision made in isolation and never checked against a real
person. Their answer decides P1.

### Record it like this — attributed, not aggregated

One row per call. **Do not summarise into a percentage**; ten facilitators is a
sample where who said it matters more than how many did.

| Facilitator | Programme | Cohort size | Cohorts/yr | Who pays today | Programme or materials? | Verbatim | Outcome |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

The "verbatim" column is the point. *"I've got a course, what I haven't got is
anything that tells me what's actually going on with each couple"* is a product
direction; "prefers materials" is not.

### Closing

Ask for the next cohort, not this one — a programme mid-term will not restructure
around a stranger. Then: *"Can I send you one couple's report so you can see what
your session would have in it?"* That is the artefact doing the selling, and it
is the strongest close available at zero downloads.

---

## 13. The 30 — target list, personalisation, and the one-sheet

**Nothing here is sent without the founder's explicit go-ahead, per batch.**
This section is the prepared material, not an outbox.

**What is and isn't verified.** The organisations and programme names below came
from public marriage-ministry pages. **I have not verified any individual's name
or email address, and have invented none.** Finding the person is the founder's
first ten minutes per target — §13.3 says how.

### 13.1 Why these thirty — and why the first ten are a deliberate mix

**Re-cut 2026-08-03 for D3.0 (global SaaS).** An earlier version led with twelve
diaspora parishes; that targeting is withdrawn. What survives unchanged is the
selection principle: **rank by the strength of the pipeline, not by size.**

The strongest pipeline is a programme somebody *refuses to proceed without*, and
the best of those also has an established budget line.

**Tier A — Catholic marriage-preparation offices (12).** The centre of the
strategy. Pre-Cana is a diocesan requirement, it runs across every
English-speaking market, the coordinator role is formal and publicly listed, and
**these offices already pay $35–65 a couple for Prepare/Enrich.** Mandate, budget
line and price are all established before you dial. Start at diocesan Office of
Family Life / Marriage Preparation level, not individual parishes — one yes
reaches many parishes.

**Tier B — evangelical and non-denominational premarital programmes (10).** US,
UK, Canada, Australia. Many decline to conduct a wedding without counselling, so
the mandate property holds; what is unknown is whether the *church* pays or the
couples do. Public programme pages make personalisation easy.

**Tier C — additional premarital programmes (5).** *Was couples therapists;
dropped under D3.35 and redistributed here.* The reasoning is focus, not
principle: a therapist who recommends the app costs us nothing, but it is a
**trickle** channel — couples arriving one at a time — against a cohort channel
delivering 25 at once. Under a one-off price, cohorts are strictly better. If a
therapist approaches unprompted, take it; do not spend outreach hours there.

Use these five to go wider on whichever of Tier A or B is answering.

**Tier D — wedding-adjacent (3).** Planners, registries, gifting. Kept small
until something above proves out.

**The first ten, deliberately mixed:**

| Tier | Calls in first ten | What that batch answers |
|---|---|---|
| **A** — Catholic offices | 5 | Does $39 clear a real institutional budget line, from the buyer already paying $35–65? |
| **B** — evangelical / non-denom | 3 | Does the pitch travel where the mandate exists but no budget line does? |
| **C** — extra programmes | 2 | Depth in whichever of A or B is answering |

Three different questions. Ten calls into one tier answers one of them slowly.

**Batch the sends in fives.** Five, read what comes back, adjust the
personalisation line, then the next five. Thirty at once wastes twenty-five
chances to improve the sentence that decides whether the mail is read.

### 13.2 The personalisation line — the only part that changes

The body is §3's email, unchanged. One sentence differs per target, and it is
the sentence that decides whether the mail is read:

| Tier | Line |
|---|---|
| A | "You're running Pre-Cana with Prepare/Enrich, I'd assume. I've built something adjacent and I'd rather show you than pitch you." |
| B | "I saw your marriage ministry runs [programme name]. I've built an assessment tool for engaged couples and I'm looking for one class to test it with." |
| C | As Tier A or B, whichever the target is. |
| D | "I read your [specific page] — the [specific detail] is why I'm writing to you and not to a directory." |

**One specific detail per target, always.** It is the entire difference between
outreach and spam, and it takes four minutes on their website.

### 13.3 Finding the actual person

In order, stop when it works:

1. Church site → *Ministries* / *Connect* → Marriage, Family Life, or Pre-Marital.
   The coordinator is usually named on the page.
2. Diocesan sites: *Office of Family Life* / *Marriage Preparation* — staff
   directories are public.
3. **Phone the church office and ask "who runs marriage counselling?"** Faster
   than any amount of searching, and being a person who phoned is itself the
   personalisation.
4. Never a generic `info@` if a named person is findable. Never BCC. Never a
   list tool — thirty individually-sent mails from a personal address, or don't
   send.

### 13.4 The one-sheet — hold this during the call

Everything the founder needs on one page. Full script in §12.

**Open — ask before pitching:**
1. How many couples, how many sessions, how often does it run?
2. What are you using now — Prepare/Enrich, your own manual, something else?
3. **Who pays today, the couples or the church?** *(decides invoice vs
   couples-pay before you have to guess)*

**Say this, and only this:**
> "Each couple takes a short assessment on attachment and communication style.
> You get a report per couple you can teach from. They keep the app afterwards —
> a question a day they both answer privately, that opens once they've both
> replied. $39 per couple — your first cohort costs you nothing. Assessment,
> portraits, report and certificate are theirs to keep; the counsellor runs
> for 12 months."

**Never say:** curriculum · certificate · eight weeks · therapy · any outcome
claim. If asked: *"Not yet — a certificate is being built now. The eight-week
question is what I wanted to ask you about."*

**When they ask what you can see about their couples:**
> "I can tell you who's finished, so you can chase them. I can't tell you what
> any couple answered — not to you, not to anyone. If I'd build that for you,
> you'd be right to wonder what I'd tell someone else about your couples."

**When they ask what you can see about their couples — and they will:**
> "I can tell you who's finished, so you can chase them. I can't tell you what
> any couple answered — not to you, not to anyone. If I'd build that for you,
> you'd be right to wonder what I'd tell someone else about your couples."

*Best line in the project. It converts our biggest constraint into the reason to
trust us, and it pre-empts the objection a counsellor is most likely to have.*

**The question that decides what we build:**
> "You already run a course. Would you rather have a programme to run — or
> materials that drop into the one you've already got?"

*(Expect "materials" from any contact inside a mandated programme — Pre-Cana
especially. Ask anyway, and record it verbatim.)*

**Ask every mandated programme:**
> "Does the church actually decline to marry a couple who hasn't completed it,
> or is it encouraged rather than required?"

*(A mandate someone enforces is a funnel; a mandate nobody enforces is a
suggestion. This is the question that tells you which one you're looking at.)*

**Then:**
- "What would have to be true for you to use it next term as well as this one?"
- **"When does your next cohort start?"** *(the §11 cadence — ask every time)*
- Close on the *next* cohort, not the current one.
- **"Can I send you one couple's report, so you can see what your session would
  have in it?"** — the artefact does the selling. Strongest close available at
  zero downloads.

### 13.5 Record it — one row per call, attributed

| Facilitator & org | Tier | Cohort size | Cohorts/yr | Who pays now | Programme or materials? | Mandate enforced? | Verbatim quote | Next cohort | Outcome |
|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | |

Do not aggregate into percentages. At n=10, who said it matters more than how
many did, and the verbatim column is where the product direction comes from.

---

## 14. The first-cohort delivery kit

The gap between a facilitator saying yes and money arriving. Written against
what the code actually does today, with every missing piece named in §14.6.

### 14.0 The thing that should shape the entire kit

**A premarital class is the only context in this business where both partners
are in the same room at the same time.**

The two-sided cold start is the product's hardest problem — §3.3 of the strategy
doc puts install→paired at ~6% today and ~23% after the fixes, and every channel
is throttled by it. In a cohort, that constraint disappears. Both partners are
sitting next to each other with phones out and someone at the front of the room
telling them what to do.

**So pair them in the room. Do not send anyone home with an invite to send.**
This turns the single largest leak in the funnel into a supervised two-minute
step, and it is the reason a cohort couple should activate at a rate no other
channel can touch.

Corollary, and it decides the rest of the kit: **pair in the room, assess at
home.** Pairing fails without supervision and takes two minutes. The assessment
takes twenty minutes a person and fails in a room — nobody wants to answer
"I want to merge completely with another person" sitting beside their fiancé
with a facilitator watching.

### 14.1 Before the session — what the facilitator gets, and nothing more

Sent one week ahead. **A facilitator who has to prepare is a facilitator who
postpones**, so this is three things:

1. **One sample report** — a real one, for a fictional couple. This is what they
   are actually buying and most will not have looked closely until now.
2. **A half-page they can read aloud**, in their words. Not a deck.
3. **Their cohort link and QR code**, as a printable PNG and as something they
   can paste into a WhatsApp group.

That is the whole pre-session ask. **Do not send a training call, a webinar, a
slide deck, or a "quick 15 minutes to walk you through it."** Every one of those
is a reason to move the date.

### 14.2 In the room — twelve minutes

Give the facilitator this as a script, timed:

> **(2 min) "We're going to use something new this term. It's an assessment of
> how each of you handles closeness and conflict, and I'll get a report on each
> couple that we'll work through in session two. It costs $39 per couple, once.
> Take out your phones."**
>
> **(3 min) Everyone scans the code. One of you pays.**
>
> **(5 min) Both of you install it and — this bit matters — sign in with
> Google. Then connect to each other: the person who paid gets a code, the
> other one enters it. Put your hand up if you're stuck.**
>
> **(2 min) "You'll each get twenty minutes of questions to do at home this
> week, separately. Don't do them together and don't discuss them first —
> the whole point is that you each answer honestly."**

**"Sign in with Google" is not a preference — it is the whole reason the room
works.** Verified in `auth_viewmodel.dart`: `signInWithGoogle()` returns a token
directly and never routes to `EmailVerificationScreen`, while email signup
always does. Twenty-five people waiting on OTP emails over venue wifi is exactly
where a live setup dies, and this avoids it with no engineering at all. Email
signup stays as the fallback for anyone without a Google account — expect a
handful, and let them finish at home rather than holding the room.

**⚠️ Tell the facilitator what NOT to demo.** The two-sided reveal — the best
thing in the product and the first thing anyone reaches for to show a class —
**cannot be demonstrated in the room.** Its entire mechanic is that neither
partner sees the other's answer until both have replied; shown side by side on
a projector, it spoils itself and teaches the class that the privacy claim is
decorative.

If they want to show something, show **the question with both answers still
hidden**, and say: *"You'll each answer this tonight, separately. It opens for
both of you when you're both in."* That demonstrates the mechanic by withholding
it, which is the point.

Then the facilitator does nothing else. No app demo, no feature tour.

**Why payment happens in the room:** a $39 decision made at home, alone, next to
a partner asking "do we need this?", converts far worse than one made in a room
where the person they trust has just said it is part of the course. It also
removes the free-ride problem in §5.3 of the strategy doc entirely — nobody is
weighing whether to skip it when everyone around them is paying.

### 14.3 At home — the assessment

**Why not in the room, since you have them there?** A facilitator will ask this,
and the answer should be ready, because "it takes too long" is the weakest of
the three real reasons:

1. **Co-presence corrupts the instrument.** The items doing the work are *"I
   worry about being abandoned"* and *"I often worry that romantic partners
   won't want to stay with me."* Answered beside your fiancé three weeks before
   the wedding, that is not the same measurement — and we would be printing a
   methodology page describing it as self-report.
2. **Someone in a controlling dynamic will not answer honestly with their
   partner beside them — and that is precisely the couple a premarital
   facilitator most needs to see clearly.** This is the argument to lead with
   for a professional audience. It is a safety point, not a data-quality one,
   and a counsellor will recognise it immediately.
3. **Dignity.** A partner who reads more slowly — second language, dyslexia,
   poor eyesight — gets watched by the room not finishing.

Both partners, separately, within the week. One reminder at day 3 to whoever
hasn't finished, and — importantly — **the reminder goes to the couple, not to
the facilitator.** A facilitator chasing 25 couples is a facilitator who does not
run cohort two.

### 14.4 Before session two — the reports

The facilitator gets all completed reports **48 hours before the session**, not
the morning of. They need time to read them, and the whole value proposition is
that they can teach from them.

Reports for incomplete couples are held, not sent partial. A half-report is
worse than none: it invites the facilitator to draw conclusions from one
partner's answers, which is the exact asymmetry `boundary.py` exists to prevent.

### 14.5 When a couple gets stuck

Three tiers, and the first two must absorb almost everything:

1. **A one-page troubleshooting sheet** the facilitator holds — "can't pay",
   "didn't get the code", "my partner's phone is Android", "I already have an
   account". Five answers, no jargon.
2. **A support address that is not the founder's personal phone**, published to
   couples directly so the facilitator is never the router.
3. **The founder, reachable, for cohort one only.** That is the pilot promise
   and it should be kept — but see §14.7.

### 14.6 What this needs that does not exist

Checked against the code, then resolved. **The sequencing question this section
originally raised is closed:** pairing and cohort attribution were promoted to
P0, email verification turned out to need no work at all, and the questionnaire
length is being managed rather than cut. **Nothing on this list now blocks a
first cohort.**

| Need | State today | Blocking? |
|---|---|---|
| **Pair in person by short code** | **Promoted to P0.** A 6-character code partner B types in — not QR. Same benefit, materially less work than QR plus deep links. | Resolved |
| ~~Deferred email verification~~ | **Solved, free.** `signInWithGoogle()` returns a token and never routes to `EmailVerificationScreen`; only email signup does. Verified in `auth_viewmodel.dart`. | Resolved — "sign in with Google" is the in-room instruction |
| **Cohort attribution link** | **Promoted to P0**, on the grounds that it is *unrecoverable*: you cannot reconstruct after the fact which couples were in cohort one, so skipping it permanently costs the post-cohort summary and the who's-finished view. | Resolved |
| **Short onboarding** | **Stays P1, deliberately.** Mitigated by answer persistence (D3.1, already P0) rather than by cutting the instrument — a couple does ten items tonight and twenty tomorrow. To be promoted on cohort-one evidence if completion is still bad, rather than on prediction. | Managed risk, not a gap |
| **Facilitator completion view** | Does not exist. | No — a weekly email listing who is done is enough for cohort one |
| **Report delivery to a facilitator** | P0.3, being built. | Already scheduled |

**One thing persistence changes rather than fixes, worth watching in cohort
one.** It converts abandonment into *stalling*: instead of a couple being lost
at item 19, they are parked at item 19 indefinitely. Because incomplete couples'
reports are held rather than sent partial (§14.4), the facilitator still gets
nothing for that couple — the failure mode is the same shape, it just no longer
announces itself. **So the day-3 reminder matters more under persistence, not
less**, and the metric to watch in cohort one is not "abandoned" but "both
partners complete", which is the only state that produces a report.

**If the pairing code slips**, the fallback is: couples pay in the room, install
at home, pair at home by email invite. That is honest, it still works, and it
gives up the single biggest advantage the channel has. It should be a deliberate
decision, not a discovery on the day.

### 14.7 What breaks at cohort three

Worth naming now because the whole model rests on repetition:

- **The founder cannot be the support line past two or three concurrent
  cohorts.** Twenty-five couples times three is 75 couples, and the founder is
  also the engineering and product team.
- **Manual report generation does not survive.** If any part of producing a
  report is hand-run, it caps cohorts at whatever one person can do in a week.
- **A facilitator with no self-serve link has to talk to the founder every
  term.** §11's standing link is what stops cohort two from costing a
  conversation — it is listed there as a growth feature, and it is really a
  capacity constraint.

---

## 15. The sourcing playbook — finding and qualifying targets at volume

§13 is thirty targets built by hand. That does not scale, and the arithmetic
says it has to: **~21 active facilitators needs ~70 calls and ~210 contacts over
a year** (`go-to-market.md` §6.0). This is the method for producing those
without anyone hand-building a list again.

**The constraint is founder-hours, not target supply.** There are thousands of
qualifying organisations. There is one person. So the whole playbook optimises
for *disqualifying from the outside* — a call that discovers on minute three
that the programme is encouraged rather than required is a call that should
never have been booked. **Sixty qualified contacts beat two hundred unqualified
ones.**

### 15.1 The filter — the mandate property, applied from a webpage

Two tests, both usually answerable without contacting anyone:

1. **Does somebody refuse to proceed without it?** Look for *"is required"*,
   *"must be completed before"*, *"a wedding date cannot be set until"*. As
   opposed to *"we encourage"*, *"we recommend"*, *"couples are invited to"*.
2. **Does it follow the couple**, or apply only at one venue?

A mandate someone enforces is a funnel. A mandate nobody enforces is a
suggestion, and a suggestion does not assemble a cohort.

### 15.2 Catholic dioceses — the highest-yield source, with one trap

**The USCCB publishes a [Directory of Diocesan Marriage & Family Life Directors
and NFP Coordinators](https://www.usccb.org/topics/natural-family-planning/directory-diocesan-marriage-family-life-directors-and-nfp),
listed alphabetically by state.** That is a public, ready-made directory of the
exact role we are selling to, across every US diocese. **Start here.** It is
worth more than any amount of searching, and it removes the "finding the person"
problem for the entire Tier A list at once.

Two structural notes that save time:

- Marriage & Family Life is usually its own diocesan department, but not always
   — it also sits under Evangelization, Faith Formation, or the offices of the
  Vicar General or Chancellor. If it isn't obvious, it's in one of those.
- **Sell to the diocese, not the parish.** One diocesan yes reaches many
  parishes; a parish yes reaches one. This is the leverage the 21-facilitator
  model needs.

**The trap — read the diocese's approved-instrument list before calling.**
Dioceses require a premarital inventory, and typically **approve several rather
than mandating one**: FOCCUS, Prepare/Enrich, and Fully Engaged are the three in
common use. Which of those a diocese lists tells you which conversation you are
in:

| What the diocese publishes | What it means | Action |
|---|---|---|
| No named instrument; parish or facilitator chooses | **Best case.** Open slot, discretion at the level you're already pitching | Call |
| Several approved instruments listed | Approval process exists and is winnable. Budget confirmed | Call — ask how something gets added |
| A single mandated instrument | Closed. Do not pitch as a replacement | Call only as a *supplement*, or skip |
| **Requires Nihil Obstat / Imprimatur** | Doctrinal approval Bliss does not have and cannot quickly get | **Disqualify.** Do not spend a call |

That last row is the most valuable line in this section. *Fully Engaged* carries
a Nihil Obstat and Imprimatur; a diocese that requires one has a gate we cannot
pass, and it is visible on their website in under a minute.

**The reframe this forces, and it should reach the strategy doc:** in a diocese
with a closed inventory list, Bliss is not competing for the inventory slot. It
is the thing the couple keeps *after* the inventory — which is a different, and
in some ways easier, pitch.

### 15.3 Evangelical and non-denominational programmes

No directory exists. Search patterns that work, per city:

```
"premarital counseling" required church [city]
"marriage preparation" "before we will marry" church [city]
site:*.church premarital class
"engaged couples" class ministry [city]
```

Then apply §15.1 to the page you land on. Large multi-site churches are worth
disproportionately more: they run cohorts continuously rather than annually,
which is the §8 *cohorts-per-facilitator* metric.

### 15.4 UK, Ireland, Canada, Australia

Anglican and Catholic dioceses in each publish marriage-preparation
requirements the same way; the diocesan-office structure is equivalent. Search
`[diocese] marriage preparation course` and apply the same filter. Do this after
the US list is working, not alongside it — one person, two channels.

### 15.5 Couples therapists — not a channel for v1

**Deprioritised under D3.35.** Not because it is a bad channel — a therapist
recommending the app is free distribution — but because it delivers couples one
at a time against a cohort channel delivering 25, and one founder working two
channels badly loses to one channel worked well.

If a therapist approaches unprompted, take it. Do not source them.

*If it is ever revived, the directories are public and filterable: the Gottman
Referral Network, Psychology Today (filter couples counselling by location),
and AAMFT.*

### 15.6 Disqualify from the outside — the signal table

Spend zero founder-minutes on anything in the right-hand column.

| Qualify | Disqualify |
|---|---|
| "Required before a wedding date is set" | "We encourage all couples to…" |
| Named coordinator with a direct email | Only a generic `info@`, no names, no phone |
| Published term dates or multiple cohorts a year | Runs once a year, or "contact the pastor" as the only route |
| Names an inventory they use — budget confirmed | Requires an imprimatur-bearing instrument |
| A structured programme page: sessions, dates, format | A single sentence on a wedding-enquiries page |
| Congregation large enough for a 10+ couple cohort | Very small congregation — cohort too small to matter |
| Uses someone else's materials | Sells its own premarital curriculum — competitor, not channel |

**Two of these are worth more than the rest.** "Required" versus "encouraged"
decides whether a funnel exists at all. Cohorts-per-year decides whether the
relationship is worth $4,680 or $1,170 — and that is the difference between the
21-facilitator model working and not.

### 15.7 The weekly routine

To hit ~210 contacts a year, sourced and qualified:

- **~4 qualified contacts a week.** Roughly 60–90 minutes: work down the USCCB
  directory, open each diocese's marriage page, apply §15.6, keep or drop.
- **Expect to drop half.** That is the playbook working, not failing.
- **Batch sends in fives** (§13.1), so the personalisation line keeps improving.
- **Log every drop with its reason.** After fifty, the disqualify column can be
  tightened with evidence instead of judgement — and the drop reasons are
  themselves a finding about the channel.

One person, ninety minutes a week, is the entire sourcing cost of the plan. The
calls are the expensive part, which is why the filtering has to happen before
them.
