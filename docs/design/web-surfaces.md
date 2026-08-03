# Landing, facilitator page and checkout — design

Owner: design (`local_81faf803`). Copy owner: marketing (`docs/marketing-copy.md`
§§7–11). Built by: engineer / marketing. Execution-plan **P0.5** and **P0.2**.
Written 2026-08-03.

Copy is not reopened here. This is the design of the surfaces it sits in.

The purchase and the product have to feel like one thing. Right now they are
going to be built by different people in different technologies at different
times, which is exactly how a checkout ends up looking like a checkout and an
app ends up looking like an app — and the couple who bridges them learns that
the company they paid is not quite the company they downloaded.

---

## 1. The system, ported

**Identical palette, identical typeface, identical scale.** Nothing new is
invented for the web, and the design tokens below are a transcription of
`mobile/lib/core/theme/`, not a parallel system. If a value here disagrees with
that directory, that directory is right.

```css
:root {
  --cream:        #FFFBF5;   --white:       #FFFFFF;
  --coral:        #FF9B8A;   --rose:        #FFB5C5;   --peach: #FFD4C8;
  --teal:         #7EBDB4;   --teal-ink:    #388076;
  --charcoal:     #4A4A4A;   --muted:       #6F6B67;
  --on-brand:     #3B2A24;   --hairline:    #EDE8E1;   --border: #8F8981;
  --calm:         #F0F7F5;   --notice:      #FFF9EC;   --neutral: #F6F2ED;
  --crisis:       #B71C1C;
  --radius-card:  20px;      --radius-cta:  24px;      --radius-pill: 999px;
}
```

**The one rule that must survive the port:** the pastels are fills and never
inks. `--coral` as link text on `--cream` is 1.98:1. On the web this is a
harder discipline than in the app, because "a coral link" is the most natural
thing in the world to write in CSS and nothing stops you. Links are
`--charcoal` with a 2px `--coral` underline at 3px offset; on hover the
underline thickens to 3px. The colour identifies the brand, the underline
identifies the link, and neither is asked to do the other's job.

**Type.** Inter, weights 400/500/600/700, self-hosted `woff2`, `font-display: swap`.
Not Google Fonts by CDN — a third-party font request on a page whose entire
argument is that we do not leak your data is an argument against itself, and
it is the first thing a technically-literate facilitator will look at.

| Role | Desktop | Mobile |
|---|---|---|
| Page headline | 44/1.15, 600, −0.02em | 30/1.2 |
| Section head | 28/1.25, 600 | 24/1.25 |
| Sub-head | 20/1.35, 600 | 18/1.35 |
| Body | 18/1.65, 400 | 17/1.6 |
| Small / caption | 15/1.5, 400, `--muted` | 15/1.5 |
| Eyebrow | 13/1, 700, +0.09em, uppercase | 13/1 |

Body at 18px with a **max measure of 62ch** — the same 50–75 character rule the
print report uses, and the reason the page is not full-width at any breakpoint.

**Motion.** The same four durations as the app (120/220/360/640ms) and the same
four curves, none of which overshoot. `prefers-reduced-motion: reduce` is
honoured — movement becomes opacity, ambient loops stop. There are no
scroll-triggered reveals anywhere on any of these pages: content that fades in
as you scroll is a device for making thin pages feel substantial, and it makes
the page unusable for someone who scrolls with a keyboard.

**Colour scheme.** One theme, light, cream. Not because dark mode is hard but
because cream at `#FFFBF5` is already gentle enough at night that the usual
argument does not apply, and a second theme is a second set of contrast failures
nobody will measure. `color-scheme: light` declared explicitly so the browser
does not attempt its own inversion.

---

## 2. `/` — the consumer landing page

Copy: `marketing-copy.md` §7. Mechanic-led per D5. **One page, one action, and
the action is the same action twice.**

### 2.1 Structure

```
┌────────────────────────────────────────┐
│  Bliss                                 │  wordmark only. no nav.
├────────────────────────────────────────┤
│                                        │
│  You both answer. Neither of you       │  44/1.15 600, max 16ch per line
│  sees the other's answer until         │
│  you have.                             │
│                                        │
│  [body paragraph]                      │  18/1.65, 52ch
│                                        │
│  ┌──────────────────┐                  │
│  │  Get Bliss — $39 │                  │  coral, --on-brand ink, 56px tall
│  └──────────────────┘                  │
│  One payment. Both of you.             │  15, --muted
│  No subscription.                      │
│                                        │
├────────────────────────────────────────┤
│  WHAT YOU GET                          │  eyebrow
│  four blocks, stacked, no cards        │
├────────────────────────────────────────┤
│  WHAT BLISS WILL NEVER DO              │  eyebrow
│  two paragraphs. nothing else.         │
│  ┌──────────────────┐                  │
│  │  Get Bliss — $39 │                  │
│  └──────────────────┘                  │
├────────────────────────────────────────┤
│  [crisis line]                          │  --calm panel
└────────────────────────────────────────┘
```

**No navigation bar.** No "Features / Pricing / About / Login". One page with
one action does not need navigation, and a nav bar is four invitations to leave
before reading the sentence the page exists for. A single small `Log in` link at
the top right is the only exception, and it is `--muted` at 15px.

**The headline is the hero.** No illustration, no phone mockup, no screenshot,
no photograph. The headline *is* the mechanic and the mechanic is the pitch;
putting a picture next to it splits the attention of the only sentence that has
to land. Set it left-aligned at ~16ch per line so it breaks into three short
lines — the shape of the sentence carries its meaning, and centring it would
lose that.

**"What you get" is four blocks, not four cards.** Bold lead-in, then body, with
a 1px `--hairline` rule between blocks and generous space. Cards would make them
feature tiles; these are four sentences about what happens to you. No icons — an
icon beside "Somewhere to think out loud" is a decision about what that looks
like, made by us, before they have imagined it themselves.

### 2.2 "What Bliss will never do" — the most important design decision on the page

This section is the product's strongest asset and the instinct will be to
feature it: a bordered panel, a coral heading, a shield icon, three checkmarks.

**All of that would undermine it.** A promise about restraint, delivered
loudly, reads as marketing. The section is set as **plain body text at the same
size as everything else, on plain cream, with no panel, no border, no icon, and
no colour** — with 96px of space above and below it. It is the quietest thing on
the page and it will be the most-read.

That is not a stylistic preference; it is the position, executed. The page is
claiming *we will not manipulate you*, and every persuasion device applied to
that claim is evidence against it.

### 2.3 The crisis line

Copy §7's closing paragraph sits in a `--calm` panel at radius 20, full measure,
with the same `♥` glyph used by `SupportAction` in the app. `--charcoal` at
17px — **not `--muted`, not 14px, not italic.** Same principle as the paywall's
support block (`safety-surfaces.md` §1.4): the moment it is styled as fine print,
it is fine print.

**Publication gate, restated because it is a design constraint too:** the phrase
*"support resources are one tap from every screen"* is false until
`support-icon-coverage.md` §§2–4 land. **Do not build this panel with that
sentence hard-coded**, and do not publish the page until the coverage test
passes. If it slips, the interim wording is *"support resources are always
reachable"* and the panel is otherwise unchanged.

---

## 3. `/for-facilitators`

Copy: `marketing-copy.md` §8. Boundary-led per D5, no price list per D2.1, one
action: book a call.

**This page is set in a different register from `/`, deliberately, and closer to
the printed report.** Same tokens, different application:

| | `/` | `/for-facilitators` |
|---|---|---|
| Headline | 44px | **34px** |
| Measure | 52ch | **66ch** |
| Coral | the CTA, twice | **the CTA only, once** |
| Panels | one (`--calm`) | none |
| Section rule | hairline | **1px `--border`, full measure** |
| Register | a product | **a document** |

A professional evaluating a tool for couples whose marriages they are
responsible for is reading, not scanning. The longer measure, smaller headline
and near-total absence of accent colour say *this was written to be read* —
which is the same argument the report's page 8 makes typographically, and
consistency between the page and the artefact it sells is worth more here than
consistency between this page and the consumer one.

### 3.1 The boundary section

Copy §8's five boundary claims are the substance. Set as a numbered list —
actual numerals, `01`–`05`, in `--coral` at 13px/700 in the left margin, with
the claim in 20/1.35/600 and the explanation in body beneath.

Numerals rather than bullets because these are *commitments*, and a numbered
commitment can be referred to on a call: "the second one, about what you see."
That is a small thing that makes a document usable in a conversation, which is
the only place this page's job actually gets done.

**The test paragraph** — the one about tests that plant a paywall and fail if
the first test does not catch it — is the single most credible thing on any
surface we own, because it is falsifiable and specific. It gets its own block
with a 1px `--border` rule above and below it, and it is the only place on this
page where I would allow `--neutral` as a fill at 6% equivalent. Nothing else.

### 3.2 The faith paragraph, and the global-product problem

Copy §8 includes the faith claim, and this is the paragraph most likely to be
mis-designed.

**Typography only. No imagery, no iconography, no symbol, of any tradition.**
No cross, no crescent, no star, no dove, no praying hands, no stained-glass
motif, no candle.

The reasoning is commercial as well as respectful. Our first calls are Catholic
marriage-prep offices and evangelical premarital programmes in the US, UK,
Canada and Australia — but the product serves a worldwide user base and the
faith feature is *tradition-tagged*, which is precisely the differentiator. A
single symbol on this page tells a facilitator from any other tradition that the
tagging is decoration over a default. And a cross on the page tells a Catholic
office nothing they did not already assume, so we would be paying for it in
reach and buying nothing.

The same rule applies inside the app's faith surfaces: **the tagging is the
feature, so the chrome must be neutral and the content carries the tradition.**
No tradition gets ornament in the frame.

The one sentence that must not be softened is the constraint: *faith framing is
never used to pressure anyone to stay in an unsafe relationship.* Set at
`--charcoal` 600, on its own line, with space around it. It is the sentence that
distinguishes a faith-aware product from a faith-pressuring one, and it is the
one a safeguarding-conscious facilitator is looking for.

### 3.3 What running a cohort looks like

Four numbered steps. Same numerals as §3.1. **No timeline graphic, no connecting
line, no icons.** A four-step process rendered as an infographic is the visual
signature of collateral (`facilitator-report.md` §1, test 2), and this page is
judged by the same eye that judges the report.

---

## 4. `/checkout`

Copy: `marketing-copy.md` §9. This is the page where restraint is most expensive
and most necessary.

### 4.1 Layout

Single column, 480px max, centred. **No sidebar, no order summary panel, no
progress stepper, no trust-badge row.** There is one product at one price; a
checkout with a summary column is a checkout that expects a cart.

```
  Bliss — $39                          28/1.25, 600
  One payment. Covers both of you.     18/1.65
  No subscription, nothing to cancel.

  ────────────────────────────────     1px --hairline

  The assessment and your portraits           yours to keep
  Your report and certificate                 yours to keep
  The daily question and everything
    you do together                           yours to keep
  The AI counsellor                           for 12 months

  ────────────────────────────────

  [ card fields ]

  ┌──────────────────────────────┐
  │         Pay $39              │     coral, --on-brand, 56px
  └──────────────────────────────┘

  Or pay by bank transfer / invoice     link, --charcoal + coral underline

  30 days, full refund, no questions asked.
  Questions before you buy? [email] — a person answers.
```

### 4.2 The 12-month line

D3.11a and marketing §9 both require the counsellor's 12-month bound to be
disclosed **at the point of sale, in the same breath as the price.** The design
requirement that follows is narrow and non-negotiable:

**"for 12 months" is set at exactly the same size, weight and colour as the
three "yours to keep" lines above it.** Not smaller. Not `--muted`. Not
asterisked. Not in a tooltip. Not below a fold.

The four lines form a scope statement, and the whole reason it reads as *scope*
rather than as a *catch* is that three permanent items and one bounded item are
presented as one list of equal things. Demote the fourth line by one visual step
and it becomes a disclosure, which is what it would then be.

Right-align the four qualifiers in a second column at desktop; stack them
beneath at mobile with the same weight.

### 4.3 The bank-transfer path is not a footnote

Churches and NGOs frequently cannot pay by card, and per marketing §9 a
card-only checkout loses sales that have already said yes. **It is a link
immediately below the pay button, at body size**, not in the footer and not
behind an accordion. Someone who has already been told by their finance office
that they cannot use a card needs to see it before they conclude the page does
not apply to them.

### 4.4 Forbidden, same list as the paywall

`safety-surfaces.md` §1.4 applies in full: no countdown, no scarcity, no social
proof, no strikethrough price, no pre-ticked anything, no confirmshaming, no
"most popular" badge. There is one plan, so a "recommended" flag would be
self-parody, but it will be suggested anyway.

Two additions specific to a checkout:

- **No newsletter opt-in on this page**, ticked or unticked. Consent bundled
  with a purchase is *forced action* (FTC §7) and it is the exact behaviour the
  product's privacy claims disown.
- **Card fields are Stripe Elements, styled to the tokens** — 16px radius,
  `--border` at 1.5px, focus ring `--on-brand` at 2.5px. Never left at the
  default Stripe styling. A checkout that changes typeface at the card field is
  a checkout that looks like it might not be ours, which at the moment of
  payment is expensive.

### 4.5 Accessibility

- Every field has a persistent `<label>`, never a placeholder-as-label. Same
  rule as the app (`accessibility.md` §6.4).
- Errors are announced via `aria-live="polite"`, described by `aria-describedby`,
  and are **text plus colour** — `--crisis` alone fails §5 of the a11y doc.
- Focus ring `--on-brand` 2.5px, visible on every interactive element, **never**
  `outline: none`.
- The pay button is a `<button>`, not a styled `<div>`, and is not disabled
  until validation passes — a disabled submit button with no explanation is the
  most common accessibility failure in checkouts.

---

## 5. `/thanks` — after payment

Copy: `marketing-copy.md` §10. Per marketing this is load-bearing on the
21-facilitator model, not a receipt.

**One action, and the design must make that literally true.**

```
  You're in. Now bring them.            34/1.2, 600
  [body]

  ┌──────────────────────────────┐
  │        Send the link         │      coral, 56px, full width
  └──────────────────────────────┘
  WhatsApp, Messages, anything          15, --muted

  ────────────────────────────────

  They won't see your answers.          18/1.65, 600
  [body]

  Meanwhile — your assessment is ready. [link] --charcoal + coral underline
  You don't have to wait for them.
```

- **One coral button on the page.** The solo fallback is a link, deliberately
  subordinate: it must exist (a "waiting on your partner" dead end is the
  fastest way to make someone stop opening an app) and it must not compete.
- **No receipt block, no order number, no "check your email" banner above the
  fold.** Those go in the email. A confirmation page that leads with
  bookkeeping has spent its one moment of maximum intent on bookkeeping.
- **"They won't see your answers"** gets a `--calm` panel. It is the specific
  fear that stops someone sending the link, and it is the one place on these
  pages where a panel earns itself, because the sentence needs to be found by
  someone scanning rather than read by someone reading.
- **No confetti, no animation, no success checkmark.** They bought a
  counselling product because something needs work. Celebrating the transaction
  misreads the room, and it is the same misjudgement as a spring curve on the
  paywall.

---

## 6. Acceptance criteria

| # | Criterion |
|---|---|
| W1 | Every colour, radius and type size on all four pages traces to a token in §1, and the tokens match `mobile/lib/core/theme/`. Checked by diff, not by eye. |
| W2 | No pastel is used as text or as an icon colour anywhere. Every text/background pair measures ≥4.5:1 (≥3:1 for ≥24px). |
| W3 | Fonts are self-hosted; the pages make **zero** third-party network requests. Verified in the network panel. |
| W4 | No countdown, scarcity claim, social-proof count, strikethrough price, pre-ticked box, or newsletter opt-in on `/checkout` or `/thanks`. |
| W5 | "for 12 months" renders at identical size, weight and colour to the three "yours to keep" lines. |
| W6 | Bank transfer / invoice is reachable within one viewport of the pay button, at body size. |
| W7 | `prefers-reduced-motion: reduce` removes all movement; no scroll-triggered reveals exist to remove. |
| W8 | All four pages pass at 320px width with no horizontal scroll, and at 200% browser zoom. |
| W9 | Keyboard-only completion of `/checkout` is possible with a visible focus ring at every step. |
| W10 | The `/` crisis panel does not contain the words "one tap from every screen" until the coverage test in `support-icon-coverage.md` §6 passes. |
| W11 | No page contains a photograph of a couple, a phone mockup, a timeline graphic, or a religious symbol. |
