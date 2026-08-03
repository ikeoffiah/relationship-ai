# Accessibility — the audit, the contrast reference, and the fix list

Owner: design (`local_81faf803`). Written 2026-08-03.

This is a design failure, not an engineering one, and it should be recorded as
such. Nobody specified the labels, so nobody built them.

---

## 0. The state of it, in numbers

| | Count |
|---|---|
| `Semantics` / `semanticLabel` usages | **3**, across 53 screens |
| `SemanticsService.announce` | **0** |
| `MediaQuery.disableAnimations` honoured | **0** of 47 animations |
| `textScaler` / text-scaling handling | **0** |
| `autofillHints` on password and email fields | **0** |
| `IconButton`s without a `tooltip` | 13 of 31 |
| Text fields with `hintText` and no `labelText` | 24 vs 9 |
| Palette values that fail AA as text on cream | **11 of 17** |

The three existing `Semantics` usages are in `calendar_screen.dart`,
`couple_chat_screen.dart` and `sticker_picker_sheet.dart`. That last one is
genuinely good — the sticker picker wraps each glyph in
`Semantics(button: true, label: …)` with a comment explaining that an emoji
must be named rather than read as a glyph. **The reaction picker sitting two
files away does not.** That is the pattern of this whole audit: the right
answer already exists in the codebase, next to the place it wasn't applied.

---

## 1. Why this one matters more than it does for most products

Three reasons, and the third is commercial.

**The population.** The users of a couples-counselling product are
disproportionately depleted, distracted, or upset when they open it. Every
accessibility affordance is also a *low-attention* affordance: a named control
is easier to find when you are crying, larger text is easier when your hands
are shaking, and no motion is better when you have not slept.

**The route to help.** `SupportAction` is an icon-only control with no visible
label. It has a `tooltip`, which VoiceOver reads — good, and deliberate. But the
claim in App Store copy is *"support resources are one tap from every screen"*,
and for a screen-reader user the honesty of that claim rests entirely on that
one `tooltip:` string. It is the single most load-bearing accessible name in the
product.

**The buyer.** Our first cohorts are Catholic marriage-prep offices and
evangelical premarital programmes in the US, UK, Canada and Australia. These are
institutions — several of them subject to procurement rules that ask about
accessibility directly, and all of them serving congregations whose age
distribution is not a tech product's. A facilitator running a parish programme
will have couples in their sixties in the room. **A 10px badge at 4.2:1 is not
an abstraction to that buyer.**

---

## 2. The two worst surfaces, both of them the ones we ask people to use most

### 2.1 The daily check-in is five unlabelled emoji

`home/views/today_hero.dart:256` and
`engagement/views/daily_ritual_screen.dart:308` — `['😞','😕','😐','🙂','😍']`,
no labels, in a `Row`.

To VoiceOver this is five buttons named "disappointed face", "confused face",
"neutral face", "slightly smiling face", "smiling face with heart-eyes" — the
Unicode names, which are descriptions of *drawings*, not of what the control
means. Nothing conveys that these are a 1–5 scale, that they are ordered, or
what they are a scale *of*. The question ("How connected do you feel today?")
is a sibling `Text`, not associated with the group.

**Required, as part of the extraction in `audit.md` item 6:**

```dart
const _labels = [
  'Not connected at all',
  'A little disconnected',
  'Neither',
  'Fairly connected',
  'Very connected',
];

Semantics(
  container: true,
  label: 'How connected do you feel today?',
  child: Row(children: [
    for (var i = 0; i < 5; i++)
      Semantics(
        button: true,
        selected: value == i + 1,
        label: '${_labels[i]}. ${i + 1} of 5.',
        excludeSemantics: true,          // suppress the emoji's Unicode name
        child: /* the tile */,
      ),
  ]),
)
```

`excludeSemantics: true` is the load-bearing part. Without it the emoji's own
name is announced *in addition to* the label, and the user hears
"disappointed face, not connected at all, 1 of 5" — which is worse than either
alone.

Words, not numbers, and in that order: the label first and the position second.
A person hearing "1 of 5" first has to hold a number in mind until the scale
arrives. And the words are deliberately flat — *"Neither"*, not *"Okay"*. The
midpoint of a connection scale is not okay-ness; that is the app forming an
opinion about a 3.

**Also required:** minimum 48×48 tap target per face
(`daily_ritual_screen`'s bare `EdgeInsets.all(4)` around a 30px glyph is ~38pt),
and `SemanticsService.announce('Checked in', TextDirection.ltr)` on success,
because the current confirmation is a `SnackBar` that VoiceOver may or may not
reach before it dismisses.

### 2.2 The questionnaire is thirty rows of five bare digits

`onboarding/screens/rsq_screen.dart:135`. Someone has already been here: each
`ChoiceChip` carries `tooltip: _anchorFor(value)`, with a comment noting that a
bare "3" tells a screen-reader user nothing. That is the right instinct and it
is half a fix.

What is still wrong:

1. **The tooltip does not replace the label, it adds to it.** Flutter's
   `Tooltip` wraps its child in `Semantics(label: message)`, and semantics
   merge, so VoiceOver announces the anchor *and* the digit. Tolerable — but it
   also means the tooltip is doing work it was not designed for, and a future
   refactor that swaps `ChoiceChip` for anything else silently deletes the only
   accessible name in the questionnaire. Make it explicit: wrap each chip in
   `Semantics(label: '${_anchorFor(value)}. $value of 5.', excludeSemantics: true)`.

2. **The tap targets are ~32pt.** `ChoiceChip` with `bodySmall` (12px) labels in
   a `spaceEvenly` row. Five of them across a phone, thirty times. This is the
   longest continuous task in the product and it is performed with the smallest
   targets in it. Set `materialTapTargetSize: MaterialTapTargetSize.padded` and
   a `minimumSize` of 48; let the *visual* chip stay small.

3. **Nothing associates the item text with its answer row.** Wrap each card in
   `Semantics(container: true)` so the item and its five options are announced
   as one group. Without it, a user swiping through hears thirty statements and
   150 numbers as a flat list.

4. **Progress is unannounced.** Advancing from item 12 to 13 changes nothing a
   screen reader reports. `SemanticsService.announce('Question 13 of 30')`.

5. **`fontSize: 12` on the chip labels.** These are digits carrying the entire
   answer. `bodyLarge`.

---

## 3. Contrast reference — the whole palette, measured

Every ratio below is computed against the surface the colour is actually drawn
on, not against pure white. Keep this table; it is the reason several of the
values in `app_colors.dart` changed.

### 3.1 Text and glyphs on `creamWhite` (#FFFBF5)

| Colour | Ratio | Verdict |
|---|---|---|
| `softCharcoal` #4A4A4A | **8.60** | Body text. The default. |
| `categoryPlum` #6B4B7A | **6.99** | ✅ |
| `crisis` #B71C1C | **6.37** | ✅ Reserved for the support screen. |
| `categoryRust` #B4462F | **5.28** | ✅ |
| `categoryStone` #6E6A66 | **5.20** | ✅ |
| `categoryTeal` #2C766C | **5.20** | ✅ *(was #2F7D72, 4.74)* |
| `categorySage` #3D764D | **5.23** | ✅ *(was #3F7A50, 4.95)* |
| `categoryAmber` #85661F | **5.20** | ✅ *(was #8A6A22, 4.89)* |
| `mutedInk` #6F6B67 | **5.12** | ✅ New. Secondary text. |
| `noticeInk` #8A6A22 | **4.89** | ✅ |
| `seenTick` #388076 | **4.51** | ✅ *(was #3E8E82 — **3.77**, not the "about 4.4:1" the comment claimed)* |
| `error` #F58C8C | 2.26 | ❌ **Fill only. Never text.** |
| `calmTeal` #7EBDB4 | 2.07 | ❌ **Fill only.** |
| `warmCoral` #FF9B8A | 1.98 | ❌ **Fill only.** |
| `sageGreen` #A8C5B0 | 1.81 | ❌ **Fill only.** |
| `goldDark` #FFB84D | 1.67 | ❌ **Fill only.** |
| `softRose` #FFB5C5 | 1.61 | ❌ **Fill only.** |
| `goldMedium` #FFC870 | 1.48 | ❌ **Fill only.** |
| `rosePeach`, `goldLight` | 1.31 | ❌ **Fill only.** |

### 3.2 Ink on brand fills

| Fill | white | `softCharcoal` | **`onBrand` #3B2A24** |
|---|---|---|---|
| `warmCoral` | 2.04 ❌ | 4.35 ⚠️ | **6.68** ✅ |
| `softRose` | 1.66 ❌ | 5.35 ✅ | **8.21** ✅ |
| `rosePeach` | 1.35 ❌ | 6.54 ✅ | **10.05** ✅ |
| `calmTeal` | 2.14 ❌ | 4.15 ⚠️ | **6.37** ✅ |
| `sageGreen` | 1.86 ❌ | 4.76 ✅ | **7.31** ✅ |
| `goldMedium` | 1.53 ❌ | 5.80 ✅ | **8.91** ✅ |
| `goldDark` | 1.72 ❌ | 5.16 ✅ | **7.92** ✅ |
| `error` | 2.33 ❌ | 3.80 ⚠️ | **5.84** ✅ |
| `crisis` | 6.57 ✅ | — | — |

`crisis` is the one fill in the palette that carries white, and it is the one
that must, because it is red-on-white or it is not an emergency colour.
Everything else takes `onBrand`.

### 3.3 Faded text — why `withValues(alpha:)` is banned on ink

`softCharcoal` over `creamWhite`:

| alpha | composite | ratio |
|---|---|---|
| 0.40 | #B7B4B1 | 2.00 ❌ |
| 0.50 | #A4A2A0 | 2.47 ❌ |
| 0.60 | #92918E | 3.06 ❌ (was in `suggestion_strip`) |
| 0.70 | #807F7D | 3.88 ❌ (was `bodySmall`, inherited app-wide) |
| 0.80 | #6E6D6C | 5.01 ✅ |

Below 0.8 there is nothing usable, and 0.8 is visually indistinguishable from
`mutedInk`. **So there is no legitimate use of an alpha on an ink colour in this
app.** Use `mutedInk`, or make the text smaller, or move it.

### 3.4 Non-text contrast (WCAG 1.4.11, 3:1)

Applies to anything whose *boundary or fill* carries meaning — a selected chip,
a focused field, a toggle, a status dot, a chart mark.

Every brand pastel fails 3:1 against cream (1.31–2.07). This does not make them
unusable as fills; it means **a fill in this palette can never be the only
indicator of state.** Selection needs a border (`borderStrong`, 3.36) or a
checkmark or a text change alongside the colour.

`focusRing` = `onBrand` = 13.2:1 on cream, 6.68 on coral, ≥11 on every semantic
surface. One ring that works on every background and is confusable with
nothing — in particular not with `crisis`, which any accent-derived focus colour
in this palette would have to approach.

---

## 4. Text scaling — nothing handles it, and the shared widgets are the leverage

`textScaler` appears zero times. iOS Dynamic Type goes to 310% and Android to
200%; a person who has set 200% is not an edge case, they are someone over
sixty using their phone as configured.

Every `Container(height: N)` or `SizedBox(height: N)` wrapping a `Text` clips at
that point. The two with the widest blast radius are shared:

- `shared/widgets/animated_button.dart` — used on most screens.
- `shared/widgets/social_sign_in_button.dart` — the first screen anyone sees.

**Rule.** A container holding text gets `minHeight`, never `height`. If a fixed
height is genuinely needed (a nav bar), the text inside gets
`maxLines` + `TextOverflow.ellipsis` *and* a `Semantics(label:)` carrying the
full string, so what is visually truncated is still announced in full.

**Do not clamp the scaler.** `MediaQuery(textScaler: TextScaler.noScaling)` is a
tempting one-line fix and it is the accessibility equivalent of muting a smoke
alarm. Fix the layout.

**One place a cap is defensible:** the five check-in emoji, where the glyph is
an illustration rather than text and scaling it to 310% breaks the row. Cap that
one glyph at `TextScaler.linear(1.4)` and let the labels beside it scale freely.

---

## 5. Colour as the only carrier of meaning

The category-ink comment already gets this right — every badge carries its label
as text — and it is the one place in the app where it was thought about. Two
places where it wasn't:

- **`consent/widgets/memory_transparency_panel.dart:135,137,297,300`** — memory
  zones distinguished by `Colors.green` / `Colors.orange`. On the privacy panel.
  A user who cannot separate those hues cannot tell which of their memories is
  shared with their partner and which is not, and *that specific distinction* is
  the product's central promise. Add an icon per zone (`Icons.people_outline` /
  `Icons.lock_outline` / `Icons.medical_services_outlined`) and the zone name as
  text. This is not a nicety; it is the boundary rule, rendered.
- **`notification_center_screen.dart:369`** — `Colors.red[400]` as the sole
  priority indicator. Add a text label.

**Rule, general:** if removing all colour from a screenshot would lose
information, the screen is not finished. This is also the greyscale test the
facilitator report has to pass (see `facilitator-report.md` §4), so it is one
discipline serving two deliverables.

---

## 6. The fix list, ordered

Each row is a routed spec. **P0** items are on the money path or on the safety
path.

| # | Fix | Files | Pri |
|---|---|---|---|
| 6.1 | Check-in: labels, grouping, 48pt targets, announce | `today_hero.dart`, `daily_ritual_screen.dart`, new `connection_check_in.dart` | **P0** |
| 6.2 | Questionnaire: explicit `Semantics`, 48pt targets, group per item, progress announce, 12→16px labels | `rsq_screen.dart` | **P0** |
| 6.3 | Assistant avatar + `Semantics(label: 'Bliss')` — attribution for the AI reply | `assistant_message_bubble.dart` | **P0** |
| 6.4 | `labelText` on all 24 `hintText`-only fields; `autofillHints` on every email/password field | auth screens, `profile_edit_screen.dart`, `message_input.dart` | **P0** |
| 6.5 | Tooltips on the 13 unlabelled `IconButton`s | 13 files | **P0** |
| 6.6 | Reduced motion: cross-fade substitution, stop ambient loops | 47 sites; `glowing_orb.dart` first | P1 |
| 6.7 | Memory-zone icons + text labels | `memory_transparency_panel.dart` | P1 |
| 6.8 | `height:`→`minHeight:` on text containers | `animated_button.dart`, `social_sign_in_button.dart`, then the rest | P1 |
| 6.9 | `Semantics(container: true)` on every card and empty state | `app_card.dart`, new `empty_state.dart` | P1 |
| 6.10 | `SemanticsService.announce` on every state change currently signalled only by `SnackBar` | ~20 sites | P1 |
| 6.11 | Reaction picker gets the treatment `sticker_picker_sheet.dart` already has | `couple_chat_screen.dart`, `message_actions_sheet.dart` | P1 |
| 6.12 | Emoji-as-content: `excludeSemantics` + real labels everywhere | `daily_vibe_sheet.dart`, `shared_goals_screen.dart`, `game_play_screen.dart` | P2 |

### 6.13 Two things to *not* do

**Do not add an accessibility settings screen.** Everything above should be
correct by default and driven by OS settings the user has already configured.
An in-app "large text" toggle is a way of shipping the bug and charging the user
for the workaround.

**Do not put an accessibility claim in marketing copy until §6.1–6.5 ship.**
Per D3.16, a capability may be claimed only once someone has used it. The
support-icon claim is already one false capability statement in live copy; this
would be a second, in the same paragraph, to the same buyer.

---

## 7. Acceptance criteria

| # | Criterion |
|---|---|
| 7.1 | VoiceOver and TalkBack can complete: sign up → all 30 questionnaire items → daily check-in → send one counselling message, without sighted assistance. Recorded once, by a person, per platform. |
| 7.2 | No interactive target under 48×48 anywhere in the P0 flows. |
| 7.3 | Every screen renders without clipping at iOS text size 310% and Android 200%. |
| 7.4 | With Reduce Motion on: no element translates, scales or rotates; no ambient loop runs. |
| 7.5 | Every colour pairing in the app appears in §3 and passes at its rendered size. New colours may not be introduced without a measured row here. |
| 7.6 | A screenshot of every P0 screen, desaturated, loses no information (§5). |
| 7.7 | `SupportAction` is announced by name from every screen it appears on — this is the accessible half of `support-icon-coverage.md` §7.1 and should be tested in the same pass. |
