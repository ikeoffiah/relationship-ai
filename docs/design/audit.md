# Design audit — where the system has drifted

Owner: design (`local_81faf803`). Written 2026-08-03, against the code, not
against the docs. Covers 187 Dart files and 53 screens.

Companion documents: `system.md` (the rules and tokens), `accessibility.md`
(the contrast reference and the a11y fix list), `facilitator-report.md`,
`web-surfaces.md`, `safety-surfaces.md`.

---

## How to read this

**The design system here is good and it is not the problem.** Coral / cream /
teal, Inter, a semantic surface layer, one reserved crisis red, category inks
that displaced ten Tailwind defaults. Someone reasoned carefully and wrote the
reasoning down in the comments, which is rarer than the system itself. Two
files — `today_hero.dart` and `app_card.dart` — are close to exemplary and are
the model for everything below.

The problem is **reach**. The tokens exist; 18 of 187 files import them. So the
system describes an app that mostly isn't built yet, and the gap is filled with
whatever the author of each screen decided that day.

Findings are ranked by **how visible each is**, which for this product means
one specific test: *how likely is a facilitator evaluating us, or a couple who
has just paid $39, to see this in their first ten minutes?* That ordering puts
a contrast ratio above a border radius even though the border radius is
uglier — and it is why the counsellor's message bubble is item 2 of 21 rather
than a footnote.

Each item states what it is, why it matters, and the exact change. Items marked
**[DONE]** are in files I own and are already fixed. Items marked
**[ROUTE]** are for the engineer and are written to be applied without asking
me a question.

Severity: **S0** = a paying customer or evaluating facilitator sees it and
draws a conclusion · **S1** = a daily user sees it · **S2** = structural, felt
rather than seen, and the reason S0s keep reappearing.

### One thing this audit deliberately does not do

**Where a visual defect is downstream of a functional one, I have flagged it
rather than fixed it.** A polished surface over a broken mechanism is worse than
an ugly one, because the ugliness is the evidence — it is what leads somebody to
the fault. Three items here are held for that reason: the counselling session's
empty state (item 5b), session history (item 10a), and the memory transparency
panel (item 10a). Each names the functional defect it is waiting on.

I would rather ship an audit with three visible holes in it than ship the holes
covered over.

---

# Tier 0 — the ones that cost money

## 1. Every primary button, every user message, every selected chip is white text at 2.04:1 — **S0** [DONE + ROUTE]

`ColorScheme.light(... onPrimary: Colors.white)` over `warmCoral #FF9B8A`.

```
white on warmCoral ........ 2.04:1     AA body needs 4.5:1, AA large needs 3:1
white on calmTeal ......... 2.14:1
white on softRose ......... 1.66:1
white on goldMedium ....... 1.53:1
```

This is the most-repeated pixel in the product. It is the "Continue" button
under all thirty questionnaire items, the user's own bubble in every
conversation, the selected state of every chip, the send button, the FAB.

It also fails *below the large-text floor*, which is worth stating plainly: this
is not a marginal 4.2:1 that a reasonable person could argue about. At 2.04:1
the label and the button are close to the same lightness, and the text is
legible mainly because we know what it says.

The obvious fix is wrong. Darkening coral until white sits at 4.5:1 lands on
`#E82200` — a fire-engine red, one step from `AppColors.crisis`, the one colour
in this system that is reserved and whose reservation is a safety property. **We
would be paying for contrast with the crisis palette.**

**The fix: keep the fill, change the ink.** `AppColors.onBrand` `#3B2A24`, a
warm near-black, clears 4.5:1 on every fill in the palette — coral 6.68, rose
8.21, peach 10.05, teal 6.37, sage 7.31, gold 7.92–10.08, error 5.84. One
value, no lookup table. And dark-on-warm reads as *paper*; white-on-warm reads
as a *notification*. For a product whose entire position is restraint, the
accessible answer is also the more on-brand one, which is usually the sign it
is right.

[DONE] `ColorScheme.onPrimary`, `onSecondary`, `onTertiary`, `onError` now
resolve to `AppColors.onBrand`. `elevatedButtonTheme` sets
`foregroundColor: AppColors.onBrand`.

[ROUTE] The theme cannot reach call sites that hardcode the colour. Strip these:

| File | Line | Change |
|---|---|---|
| `onboarding/screens/rsq_screen.dart` | 152 | `Colors.white` → `AppColors.onBrand` (selected chip label) |
| `onboarding/screens/rsq_screen.dart` | 185 | `.copyWith(color: Colors.white)` → delete; `ElevatedButton` now inherits |
| `onboarding/screens/rsq_screen.dart` | 172–179 | delete the whole `styleFrom`; the theme supplies coral, radius 24, 48pt height |
| `couple_chat/views/couple_chat_screen.dart` | 676, 722 | `mine ? Colors.white : …` → `mine ? AppColors.onBrand : …` |
| `couple_chat/views/couple_chat_screen.dart` | 752, 763 | `Colors.white.withValues(alpha: 0.7 / 0.85)` on coral is **1.65:1 / 1.84:1** → `AppColors.onBrand.withValues(alpha: 0.75)` (3.99:1, and these are the timestamp and tick, which are non-text-adjacent glyphs) |
| `couple_chat/views/couple_chat_screen.dart` | 422, 1169, 1191 | `foregroundColor: Colors.white` → delete, inherit |
| `couple_chat/views/couple_chat_screen.dart` | 1170 | `warmCoral.withValues(alpha: 0.4)` disabled fill → `AppColors.neutralSurface` + `AppColors.disabledInk`. A faded version of the enabled colour is the single most common way a disabled control gets mistaken for an enabled one. |

Then grep `Colors.white` inside any widget whose background is a brand hue, and
treat each hit as this same bug.

### 1a. The same defect, inverted, on 39 buttons — found while fixing the above

Of 75 `ElevatedButton`s, 36 carry an explicit `styleFrom`. **The other 39 were
rendering coral text on a near-white fill at 1.98:1**, and nobody wrote that
anywhere.

Material 3's `ElevatedButton` defaults to `backgroundColor:
colorScheme.surfaceContainerLow` with `foregroundColor: colorScheme.primary`.
Since `primary` is coral and we had not set an `elevatedButtonTheme`, every
button whose author trusted the theme got the palette's least legible pairing —
while the 36 that overrode it got white-on-coral at 2.04:1. So *both* halves of
the app's buttons failed, in opposite directions, and which one you got depended
on whether the author had bothered to style it.

This is the clearest illustration in the audit of why partial theming is worse
than none: a half-set `ColorScheme` does not degrade to a default, it composes
with Material's defaults into pairings nobody chose.

[DONE] `elevatedButtonTheme` sets coral fill, `onBrand` ink, elevation 0, radius
24, and a 48pt minimum height. The 39 bare buttons are now correct, on-system,
and correctly sized for touch, with no change at their call sites.

---

## 2. The counsellor's reply — the surface $39 buys — renders in Material's default lavender — **S0** [DONE]

`assistant_message_bubble.dart:76`:

```dart
color: message.isSafetyMessage
    ? Colors.amber.shade50
    : Theme.of(context).colorScheme.surfaceContainerHighest,
```

We set six roles on `ColorScheme.light` and left twenty to Material 3's
baseline, **which is a purple scheme**. `surfaceContainerHighest` was therefore
resolving to `#E6E0E9` — a cool lavender-grey belonging to a different design
system — at 1.26:1 against cream.

Under D3.11 the AI counsellor is the thing behind the paywall. It is the most
expensive surface we run, the one a facilitator will ask to see, and the only
one a couple pays specifically for. It was the one surface in the app that was
not ours, and it clashed in temperature with everything around it.

[DONE] Every container and outline role is now bound to a palette value;
`surfaceContainerHighest` → `AppColors.assistantSurface` `#F1EBE3`, warm, one
clear step off cream. A screen reaching for an M3 role can no longer leave the
palette by accident — which is the actual fix, since this will happen again.

[ROUTE, optional] `Colors.amber.shade50` on the same line → `AppColors.noticeSurface`,
and `Colors.amber.shade300` at line 81 → `AppColors.goldDark`.

---

## 3. The assistant has no bubble and no avatar; the user has a solid coral one — **S0** [ROUTE]

Noted in `product-assessment.md` §2.12 and still true. The message with an
attribution problem is the only one without attribution.

This is not a polish item, it is a **safety-posture item**. The whole product
turns on the user knowing, at every moment, who is speaking and who can see it.
A reply from an AI that renders as unowned text on the page is the one
formatting choice guaranteed to blur that.

**Spec.** In `assistant_message_bubble.dart`, wrap the existing `Container` in a
`Row(crossAxisAlignment: CrossAxisAlignment.start)`:

```
[ 28×28 circle ] [ 8 ] [ existing bubble Container ]
```

- Circle: `AppColors.calmSurface` fill, `AppColors.hairline` 1px border,
  centred `Icon(Icons.spa_outlined, size: 16, color: AppColors.seenTick)`.
  Teal, not coral — the user's side of the conversation is coral and the two
  must never be the same colour.
- Wrap the circle in
  `Semantics(label: 'Bliss', excludeSemantics: true, child: …)` so the reply is
  announced as attributed rather than as a decorative image.
- Bubble keeps `assistantSurface` and its asymmetric radius (16 with a 4pt
  top-left), which already correctly mirrors the user's bubble.
- Reduce `maxWidth` from `0.75` to `0.72` of screen width to leave room for the
  avatar without the bubble reaching the right edge.
- **No name label under the avatar, no "AI" badge, no typing-persona.** The
  avatar is attribution, not a character. Adding a name would make Bliss a
  personality, and this product's counsellor should read as a facility, not a
  friend.

Also at line 24: `AnimatedTextDisplay` renders
`Text(widget.text, style: const TextStyle(fontSize: 16))` — the counsellor's
words are the one string in the app with no line height set, so they set at
Inter's default ~1.2 rather than the 1.6 every other body string in the app
uses. Replace with `Theme.of(context).textTheme.bodyLarge`. This is a two-word
change that makes the longest text in the product materially easier to read.

And line 37: `_StreamingCursor` is `Colors.blue.withValues(alpha: 0.6)`. There
is no blue in this palette. → `AppColors.seenTick`.

---

## 4. `bodySmall` shipped at 3.88:1, and it is inherited everywhere — **S0** [DONE]

`softCharcoal.withValues(alpha: 0.7)` composites to `#807F7D` over cream:
**3.88:1**, at the 12px size that is the entire reason the slot exists.

This is the highest-leverage single line in the audit, because every screen that
correctly reached for the theme instead of hardcoding a style inherited the
failure. Doing the right thing produced the defect.

[DONE] → `AppColors.mutedInk` `#6F6B67`, 5.12:1 on cream, 5.28:1 on white,
4.74:1 on `neutralSurface`. Same visual intent, measured.

The general rule, now written into `app_colors.dart`: **quieter is a size and a
position, not an alpha.** Fading text does not reduce its importance; it
reduces its legibility, and it does so most for the people who already find
reading hardest.

---

## 5. The private session opens as four bars of legal posture and 1,100pt of nothing — **S0** [ROUTE]

`product-assessment.md` §2.9 describes it; nothing about it is a copy problem,
so it lands here. Top to bottom on entry: app bar with "Private session" + a
Consent pill; a pink bar saying "Private session · Nothing shared"; a white bar
saying "Your private session"; a grey bar about not being a licensed therapist;
then void.

"Private session" three times, four disclosure bars, zero product. **A
facilitator opening this screen on a call sees a product that is visibly
frightened of itself.**

The design fix, which is separable from the copy fix:

**5a. Collapse bars 2–4 into one line.** One `Container`, full width, height
36, `AppColors.calmSurface` fill, `AppColors.hairline` bottom border, 12px
`labelSmall` in `mutedInk`, a 14pt `Icon(Icons.lock_outline)` in `seenTick`
leading, and a single trailing text button. Not three stacked bars in three
different colours from three different authors — `chat_screen.dart:339`
(`Colors.grey.shade100`), `:378` (`Colors.indigo.shade50` — indigo is not in
this palette), and `in_session_consent_banner.dart`.

**5b. The empty state is deliberately NOT being designed yet. Do not build one.**
*(Withdrawn 2026-08-03 on PM instruction. Recorded rather than deleted, because
the reasoning is the most useful thing in this document.)*

I had specified an opening greeting and three starter prompts here, per §2.9's
recommendation. That is now on hold, and it should be.

QA established that the blank screen is not a missing empty state. **The
counsellor is stateless.** `chat_router._initial_state` seeds the buffer with a
single message — 317 input tokens per turn, measured — and the cross-session
memory writer is an unwired stub. The AI does not remember turn one by turn
three, or anything from a previous session.

A counsellor with no memory has nothing to open with. The void is the *symptom*.
Designing a warm greeting and three inviting prompts over it would make the
screen look considerably better while the product remained exactly as broken —
and would remove the one visible cue that leads a person to the real fault.

This is the general rule and it applies beyond this screen:

> **Where a visual defect is downstream of a functional one, fixing the
> appearance destroys the evidence.** Spec it, flag it, and leave it.

It is worth being precise about why this is not just prudence. An empty state is
the *promise* a screen makes about what will be there. Promising "tell me
anything, I'm listening" on top of a counsellor that forgets is not a cosmetic
mismatch — it is the product telling a lie in my handwriting, on the surface
someone paid $39 for, to a person who opened it because something happened
tonight.

Revisit once conversational memory lands. At that point it is a different design
problem and a better one: not decoration over a void, but the opening of a
conversation that will be remembered.

**5a stands and is unaffected** — the four chrome bars are a layout defect
regardless of what the counsellor remembers, and collapsing them is the change
that makes the emptiness *legible* as emptiness rather than as four bars of
legal text above a scroll region.

---

# Tier 1 — seen every day

## 6. The daily check-in exists twice, at two sizes, with two confirmations — **S1** [ROUTE]

| | `home/views/today_hero.dart:256` | `engagement/views/daily_ritual_screen.dart:304` |
|---|---|---|
| Emoji size | 22 | 30 |
| Treatment | `Expanded` tiles, `softRose` @16% wash, radius 12 | bare `InkWell`, `EdgeInsets.all(4)`, no fill |
| Layout | `Row` of `Expanded` | `spaceBetween` |
| Done state | `check_circle_rounded` 18pt, `sageGreen` | `check_circle` 18pt, `calmTeal` |
| Confirmation | none | `SnackBar('Checked in — nice 💛')` |
| Tokens | `AppSpacing`/`AppRadii` throughout | raw literals throughout |
| Accessible name | none | none |

The single interaction this product asks a person to perform every day is
implemented twice by two people who never saw each other's version. Whichever
one a user meets first sets their expectation, and the other then feels wrong.

**Spec.** Extract `lib/shared/widgets/connection_check_in.dart` from the
`today_hero` version — it is the better of the two — and use it in both places.
`daily_ritual_screen` deletes `_CheckInCard` and calls the shared widget.

Take the *snackbar* from the ritual version, not the silence from the hero
version: a check-in that produces no acknowledgement reads as not having
registered. Reword it: *"Noted."* — `💛` and "nice" both evaluate the answer,
and this product should not be pleased with you for reporting a 5 and neutral
about a 1.

Accessible labels for the five faces are specified in `accessibility.md` §2.1
and are **required** as part of this change, not after it.

## 7. There is no motion vocabulary, and two of the curves are celebration curves — **S1** [DONE + ROUTE]

`AppTheme.slowFade`, `gentleMotion` and `orbAnimation` have existed since the
first commit and **are referenced by nothing** — `grep` returns the three
declarations and no uses. In their place, 47 animations each chose their own
number: fourteen distinct durations (100/120/150/180/200/250/300/400/600/800/
900/1000/1200/1500ms) and six curves.

Colour drift shows up in a screenshot and eventually gets filed. Motion drift
doesn't, so it never does — it is only *felt*, as the sense that the parts of a
thing were made by different people.

Two of the six curves are the actual brand problem. `Curves.elasticOut` and
`Curves.easeOutBack` overshoot: the element travels past its destination and
springs back. That is a confetti gesture. It is the motion signature of the
streak-and-badge product this one deliberately is not, and it is worst on the
screens where it currently runs, because it applies a party trick to somebody's
relationship.

[DONE] `core/theme/app_motion.dart` — four durations (120 / 220 / 360 / 640),
one ambient loop (3s), four curves, **none of which overshoot**, and the
reduced-motion helpers described in item 8. The scale is deliberately close to
Material 3's own tokens (150 / 300 / 600) and inside NN/g's ≤400ms guidance for
anything that isn't a deliberate reveal.

[ROUTE] Replace every `Duration(milliseconds: N)` in an animation with the
nearest `AppMotion` step, and both overshoot curves with `AppMotion.enter`.
Mechanical; the mapping is: ≤150→`instant`, 180–300→`quick`, 350–450→`settle`,
600–900→`reveal`, ≥1000→`reveal` (and ask whether it should be that long at
all — 1200ms and 1500ms transitions are past the point where users report
waiting rather than watching).

## 8. Reduced motion is honoured nowhere — **S1** [DONE + ROUTE]

`MediaQuery.disableAnimations` appears **zero times in 187 files**. All 47
animations play at full amplitude for a user who has asked their phone to stop
moving things.

This is not a small population and it is a badly-matched one for this product:
Reduce Motion is set by people with vestibular disorders (for whom large moving
surfaces cause real nausea — Apple's HIG singles out oscillation near 0.2Hz as
most provoking), by migraine and post-concussion users, and by a much larger
group who simply find animation tiring. A couples-counselling app is
disproportionately opened by people who are already depleted.

[DONE] `AppMotion.prefersReducedMotion(context)`,
`AppMotion.duration(context, d)`, `AppMotion.allowAmbient(context)`.

[ROUTE] The rule, which is not "turn everything off":

- **Movement** (slide, scale, translate, parallax) → cross-fade of the same
  duration. The change still reads; nothing travels.
- **Ambient loops** → stop. Show the final frame. `glowing_orb.dart` is the
  main offender: three stacked `BoxShadow`s on a repeating animation, which is
  precisely the large slow pulse the guidance is about.
- **Opacity and colour** → leave alone.

## 9. The suggestion strip clips mid-word with no affordance — **S1** [ROUTE]

`chat/widgets/suggestion_strip.dart:50`. A horizontal `SingleChildScrollView` of
`ActionChip`s whose labels are whole sentences. The last visible chip is cut off
flush at the viewport edge with no fade and no partial-item peek, so it reads as
a rendering bug rather than as more content.

Three changes:

1. Wrap the scroll view in a `ShaderMask` with a
   `LinearGradient(begin: centerRight, end: centerLeft, colors: [transparent, black], stops: [0, 0.06])`
   in `BlendMode.dstIn`, so the right edge fades over the last 6%. A fade is the
   only scroll affordance that costs no vertical space, and vertical space above
   a keyboard is the scarcest thing on this screen.
2. `padding: EdgeInsets.only(right: AppSpacing.xxl)` inside the `Row`, so the
   final chip can reach the left edge and the strip visibly *ends*.
3. `ActionChip(label: Text(s, maxLines: 1, overflow: TextOverflow.ellipsis))`
   with `constraints: BoxConstraints(maxWidth: 260)`. A suggestion chip wider
   than the screen is not a chip.

Also on this file: line 40's label is `softCharcoal.withValues(alpha: 0.6)` at
11px — **3.06:1**. → `AppColors.mutedInk` at `labelSmall`. Line 37's
`AppColors.calmTeal` icon is 2.07:1 → `AppColors.seenTick`.

## 10. Six empty states, six treatments, and two screens that render literally nothing — **S1** [ROUTE]

Icon sizes 56 / 64 / 72, emoji at 44 and 48, one built entirely from
`Colors.grey[300]/[500]/[400]`, and:

- `couple_chat/views/couple_chat_screen.dart:523` — with no messages, falls into
  `ListView.builder(itemCount: 0)` and **renders an empty screen**. This is the
  couple's own thread, i.e. Loop 1, i.e. the free acquisition loop, i.e. the
  first thing partner B ever sees.
- `games/views/game_play_screen.dart:442`, `faith/views/faith_screen.dart:245`,
  `bliss/views/calendar_screen.dart:274` — bare unstyled `Text`.

An empty state is not a fallback; on a young product it is the *modal*
experience, and half the app's screens are empty for a brand-new couple.

**Spec.** `lib/shared/widgets/empty_state.dart`:

```dart
EmptyState({
  required IconData icon,      // never emoji — see accessibility.md §2.2
  required String title,       // headlineMedium, softCharcoal
  String? body,                // bodyMedium, mutedInk, max ~2 lines
  Widget? action,              // one, or none
})
```

Icon at `AppIconSize.hero` (64) in `AppColors.rosePeach`, `AppSpacing.xl`
below it, title, `AppSpacing.sm`, body, `AppSpacing.xxl`, action. Centred,
`maxWidth: 320`. Wrapped in `Semantics(container: true)` so it is announced as
one thing.

Replace all eleven existing empty states with it, and add one to each of the
four screens above. In `couple_chat`, the empty state is the highest-value copy
in the free tier — it is where partner B decides whether this is a product.

### 10a. Two exclusions, under the rule in item 5b — **flagged to PM, not fixed**

Applying the same test to the rest of the empty-state list turns up two that I
believe are symptoms rather than defects. I have not designed either.

**`history/session_history_screen.dart` and `session_detail_screen.dart`.**
D3.13 records that `sessions.Session` holds **zero rows**, including after a
real session against the local stack, because `persist_turn()` swallows every
exception and returns. So session history is not empty for a new user — **it is
empty for everyone, permanently, and nothing anywhere reports it.**

This screen currently has one of the better empty states in the app
(`Icons.history_rounded` at 72, coral at 40%). That is the problem. A
well-drawn "Nothing here yet" is a *reassurance*, and it is the reason a broken
feature has sat unnoticed long enough to reach a decision document. Improving it
further would deepen the reassurance in exact proportion to how wrong it is.

D3.13's resolution is to fix the promise rather than the feature — not to store
transcripts, and to make the You tab's "everything you have talked through
before" true by changing what it says. **That is a copy and information-
architecture decision, and until it lands I should not be drawing anything on
this screen.** Once it lands, the design problem is not an empty state at all;
it is how to present "we deliberately do not keep this" as the strength it is.

**`consent/widgets/memory_transparency_panel.dart:330`.** Same shape, unverified.
This panel shows the user what Bliss has remembered about them. If the memory
writer is a stub (it is, per the above) or the zones are unpopulated, this
panel is empty for structural reasons and its empty state is a claim about the
system's state that may not be true. Its accessibility defect (§5 of
`accessibility.md` — zones distinguished by colour alone) is real and
independent, and should still be fixed. Its empty state should not be touched
until someone confirms the panel can be non-empty.

PM: both of these are questions, not conclusions. If the underlying faults are
already known and scheduled, say so and I will design against the fixed
behaviour rather than the current one.

## 11. "Error" is drawn in three incompatible visual languages — **S1** [ROUTE]

| Where | Treatment |
|---|---|
| `daily_ritual_screen.dart:90` | container, `AppColors.error` |
| `faith/views/faith_screen.dart:68` | same shape, `softRose` + `softCharcoal` |
| `consent/consent_summary_sheet.dart:157` | raw `Colors.red`, no container, `TextButton` |
| `session_history_screen.dart:191`, `notification_center_screen.dart:189` | `Icons.cloud_off_rounded` 64 + coral `ElevatedButton.icon` retry (these two agree with each other) |

The last pair is the right one. Extract it as
`lib/shared/widgets/error_state.dart` with the same signature as `EmptyState`
plus `onRetry`, and use it in all five places.

`Colors.red` in `consent_summary_sheet` deserves a specific note: it is close
enough to `AppColors.crisis` (2.82:1 apart) to read as the crisis colour, on the
**consent sheet**, where a red alarm is exactly the wrong emotional register for
"we could not load your settings." → `AppColors.onErrorContainer`.

---

# Tier 2 — structural, and the reason Tier 0 keeps coming back

## 12. The token files are imported by 18 of 187 files — **S2**

`AppSpacing` / `AppRadii` reach ~10% of the codebase. Everything else uses
literals, and the literals show the drift precisely:

```
SizedBox(height: N)        2,4,6,8,10,12,14,16,18,20,24,28,32,36,40,48,100,120,200
BorderRadius.circular(N)   2,4,6,8,10,12,14,16,20,24,32,50,999
EdgeInsets.all(N)          2,4,8,10,12,14,16,18,20,24,28,32,40
```

Note `999` typed by hand at seven sites while `AppRadii.pill` exists and is used
at five others — the same value, in the same app, half tokenised. That is the
shape of the whole problem: not ignorance of the system, just no forcing
function.

[ROUTE] Add a lint. `flutter_lints` will not catch this, but a
`dart run custom_lint` rule — or, cheaper and good enough, a CI grep — that
fails on `BorderRadius.circular(` with a literal outside `core/theme` would stop
the bleed today. Same for `Colors.<swatch>`. See item 21.

## 13. 247 inline `fontSize:` literals across 21 sizes — **S2** [partly DONE]

```
10:3  11:10  12:43  13:37  14:24  15:19  16:44  17:1  18:22  20:9  22:10
24:6  26:3  28:6  30:4  32:1  36:1  40:1  44:8  48:3  56:5
```

13 and 17 exist for no reason anyone could reconstruct. 10 is below the floor.
The theme defined 7 of Material's 15 slots and then 13 more were added in the
last pass, but **18 and 22 — the two most-hardcoded sizes after 16 — still had
no slot**, so they were reinvented 32 times between them.

[DONE] `headlineLarge` (22) and `headlineMedium` (18) added. The ladder is now
continuous: 11 · 12 · 14 · 15 · 16 · 18 · 20 · 22 · 24 · 28 · 32.

[ROUTE] Mechanical replacement, and **delete `fontSize: 10` and `fontSize: 13`
outright** — 10 goes to `labelSmall` (11), 13 goes to `bodyMedium` (14). Nothing
in this product needs to be 10px, least of all the category badges, which are
specified at 10px bold and are the smallest type in the app.

## 14. The same two gradients are retyped nine times, three of them at a different angle — **S2** [DONE + ROUTE]

- `[softRose, rosePeach, creamWhite]` — written by hand on four auth screens.
- `[warmCoral, softRose]`, the "this is selected" fill — five onboarding
  surfaces, and **three of the five omit `begin`/`end`**, so the same selection
  state is lit from a different direction depending on which screen you are on.
  Nobody would specify that. It is just what happens to a value with no name.

[DONE] `AppColors.authBackdrop` and `AppColors.selectedFill`.

[ROUTE] Replace all nine. Note that `selectedFill` carries text on five screens
and that text is currently white — see item 1.

## 15. Twenty-five hand-rolled `BoxShadow`s under a zero-elevation theme — **S2** [DONE + ROUTE]

All 48 `elevation:` declarations in the app are `0`, so Material elevation is
genuinely disciplined. Depth is then faked with `BoxShadow` in 25 places, each
with its own blur, offset and alpha. Same drift, different noun.

[DONE] `AppShadow.resting` and `AppShadow.floating` in `app_dimens.dart`. Two,
and a stated preference for neither — this palette separates surfaces by warmth
and a hairline and does not need to lift them off the page. A shadow should mean
*floating above the content*: a sheet, a dialog, a toast, the paywall. Nothing
else.

[ROUTE] `glowing_orb.dart:24,29,34` stacks three; that one is deliberate and can
stay, subject to item 8. The other 22 collapse to the two tokens.

## 16. Nineteen icon sizes; the same empty-state glyph at 56, 64 and 72 — **S2** [DONE + ROUTE]

6, 13, 14, 15, 16, 18, 19, 20, 21, 22, 24, 26, 32, 40, 48, 56, 64, 72, 80 — with
16/18/20 roughly tied for most common, so there is no default to fall back to.

[DONE] `AppIconSize.sm/md/lg/hero` (16 / 20 / 28 / 64) and a theme-level
`iconTheme` default of 20.

[ROUTE] Snap every explicit size to the nearest token. `size: 6` at one site is
almost certainly a bug.

## 17. Five stroke widths, and the sign-in flow is drawn heavier than the app — **S2** [DONE + ROUTE]

1.5px dominates `shared/widgets` and the auth screens; the rest of the app uses
the 1px default. So the first thing a new user sees is drawn in a slightly
heavier hand than the product behind it — a small thing that reads, subliminally,
as two products.

[DONE] `AppStroke.hairline` (1) / `edge` (1.5) / `focus` (2.5), and two border
*colours* rather than one: `AppColors.hairline` for decoration and
`AppColors.borderStrong` (3.36:1) for any boundary that carries meaning. WCAG
1.4.11 asks 3:1 of the second and nothing of the first; they were previously the
same near-invisible value, which meant every *meaningful* border was invisible.

## 18. The card shell exists at four radii — **S2** [partly DONE]

`AppCard` is the canonical shell at radius 20, and it is well made. Alongside it:
raw `Card()` at radius 16 in seven files, `rsq_screen.dart:113` at 16 with a
tinted fill, `safety_protocol_modal.dart:53` with no shape override falling
through to the old theme default of 24.

[DONE] `cardTheme` now matches `AppCard` — radius 20, white, hairline border,
no surface tint — so raw `Card()`s at least stop being a visibly third shape.

[ROUTE] Convert all eight raw `Card()`s to `AppCard`.

## 19. Eighty-two raw Material swatches across nineteen files — **S2** [ROUTE]

Zero raw hex outside `core/theme` — that battle was won. But `Colors.grey`,
`Colors.red`, `Colors.blue`, `Colors.indigo`, `Colors.orange`, `Colors.amber`,
`Colors.green` remain in 19 files, concentrated in **chat and consent** — which
is to say, in the paid feature and in the screens where our trustworthiness
about data is being judged.

Mapping, exhaustive:

| Raw | Token |
|---|---|
| `Colors.grey`, `.shade100`, `.grey[100]` | `AppColors.neutralSurface` |
| `Colors.grey.shade200/300`, `BorderSide` uses | `AppColors.hairline` (decorative) or `AppColors.borderStrong` (meaningful) |
| `Colors.grey.shade600/700`, `.grey[500]/[600]`, bare `Colors.grey` as text | `AppColors.mutedInk` |
| `Colors.grey[300]/[400]` as empty-state icon | `AppColors.rosePeach` |
| `Colors.red` / `.red[700]` / `.red[900]` as text | `AppColors.onErrorContainer` |
| `Colors.red[50]` / `.red[100]` / `red.withValues(0.05)` as fill | `AppColors.errorContainer` |
| `Colors.orange` (destructive-ish actions: "Step out", "Leave session") | `AppColors.noticeInk` |
| `Colors.amber.shade50` | `AppColors.noticeSurface` |
| `Colors.amber.shade300` | `AppColors.goldDark` |
| `Colors.blue*` (NVC reframe card, streaming cursor) | `AppColors.seenTick` on `AppColors.calmSurface` |
| `Colors.indigo.shade50/700` (`chat_screen.dart:378,381`) | `AppColors.calmSurface` / `AppColors.softCharcoal` |
| `Colors.green` (consent zones, lock icons) | `AppColors.categorySage` |

`nvc_reframe_card.dart` is the worst single file — seven blue values and three
greys, a card entirely in a palette we do not use, sitting inside the
counselling session. `memory_transparency_panel.dart` is second, and its
green/orange zone tabs are also a colour-only state distinction (see
`accessibility.md` §5).

## 20. Two `Row`s and one app-bar title will overflow on a long name — **S2** [ROUTE]

- `chat/widgets/chat_header.dart:51` — `Text('Session with ${partnerFirstName}')`
  nested two `Row`s deep with no `Expanded` anywhere in the chain.
- `relationship/our_story_screen.dart:264` — `_buildFactRow` puts two unbounded
  `Text`s in a `spaceBetween` `Row`; the values are user-entered.
- `couple_chat/views/couple_chat_screen.dart:486` — app-bar title with no
  `maxLines`, in a file whose *message bubbles* handle this correctly at lines
  759 and 1019.

Wrap in `Expanded` + `maxLines: 1` + `TextOverflow.ellipsis`. The specific
reason this is worth doing now rather than later: our first cohorts are
Catholic and evangelical premarital programmes across the US, UK, Canada and
Australia, and a global product will meet names longer than "Ada" on week one.
A yellow-and-black overflow stripe in front of a facilitator is not a bug
report, it is the end of the evaluation.

## 21. Nothing stops any of this recurring — **S2** [ROUTE]

Every item above was fixed once already in some form; the comments in
`app_colors.dart` describe a previous cleanup of exactly these categories. It
came back because nothing enforces it.

The support-icon spec (`support-icon-coverage.md` §6) has the right pattern: a
static test that fails **in both directions**. Same construction here. One CI
step, greps only, no new tooling:

```
FAIL if, outside mobile/lib/core/theme/:
  Colors\.(red|blue|green|purple|indigo|orange|amber|pink|teal|
           cyan|lime|yellow|brown|blueGrey|grey)
  Color\(0x
  BorderRadius\.circular\([0-9]
  Duration\(milliseconds: [0-9]+\)   # inside an Animation/Tween context
```

with an allowlist file carrying a one-line reason per exemption, so an
exception becomes a visible decision in a diff rather than an omission. This is
the single highest-leverage item in the document, because it is the only one
that is still true in six months.

---

## What is genuinely good, and should be copied

Worth recording, because an audit that only lists faults teaches the wrong
lesson about which files to imitate.

- **`shared/widgets/app_card.dart`** — one shell, documented, ink ripple
  clipped to the radius, an escape hatch (`borderColor`) that is explained
  rather than just exposed. The model.
- **`home/views/today_hero.dart`** — tokens throughout, no inline styles, keys
  on the interactive elements. The only screen that reads as though the design
  system exists.
- **`shared/widgets/support_action.dart`** — the comment explaining why a
  full-width `#B71C1C` bar on nine screens was replaced by one quiet icon is the
  best design reasoning in the repository. *"In an otherwise soft palette that
  made the loudest thing in the app an alarm that never stopped sounding."*
  That is the brand, correctly applied, by someone who understood it.
- **The category-ink comment block** — three constraints stated, one
  deliberately refused, and the refusal (colour is never the only carrier)
  explained. Two of its numbers were wrong, which is item-level; the *method*
  was right and is what the rest of the palette needed.
- **`rsq_screen.dart:109`** — refusing to pre-select a neutral "3" so an
  unanswered item is never silently submitted. A small correctness decision
  with a real ethical spine, in the middle of an otherwise unremarkable screen.
