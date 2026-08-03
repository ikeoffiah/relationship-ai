# The design system — the rules

Owner: design (`local_81faf803`). Written 2026-08-03.

The tokens live in `mobile/lib/core/theme/` and are documented at length in the
source, which is the right place for them. **This file is the short list of
rules that the tokens cannot enforce on their own** — the things a reviewer
checks, and the things CI should eventually check.

Index: `audit.md` (what has drifted) · `accessibility.md` (contrast reference
and a11y fix list) · `facilitator-report.md` (print) · `web-surfaces.md`
(landing and checkout) · `safety-surfaces.md` (paywall and video-call support).

---

## The position, and what it obliges

This product removed its streak counter. Its connection score can fall and hides
itself on a bad week. It refuses to show one partner an inference about the
other. The differentiator is **restraint**.

Restraint is not the absence of design; it is a set of things we spend on and a
set we decline. Warmth without saccharine, calm without blandness. **Every rule
below is that position made checkable.** Where a rule seems fussy, the test is:
would a couple who noticed this conclude that we are careful, or that we are
selling to them?

---

## 1. Colour

1. **Brand hues are fills. They are never inks.** Coral, rose, peach, teal,
   sage and all three golds sit at 1.3–2.1:1 on cream. No text, no icon, no
   glyph, ever. → `AppColors.onBrand` on a fill; `softCharcoal` or
   `mutedInk` on a surface.
2. **`Colors.white` never appears on a brand fill.** White on coral is 2.04:1.
3. **No `withValues(alpha:)` on an ink colour.** Everything below 0.8 fails AA,
   and 0.8 is indistinguishable from `mutedInk`. Quieter is a size and a
   position, not a fade.
4. **No raw Material swatch outside `core/theme/`.** `Colors.grey`,
   `Colors.red`, `Colors.blue` and friends belong to a different design system.
   Mapping table: `audit.md` item 19.
5. **No raw hex outside `core/theme/`.** Currently true. Keep it true.
6. **`AppColors.crisis` is reserved.** Support screen, emergency affordances.
   Never ambient, never a form error, never an accent. Form errors take
   `onErrorContainer`.
7. **Colour is never the only carrier of meaning.** If desaturating a screenshot
   loses information, the screen is not finished.
8. **New colours require a measured row in `accessibility.md` §3** before they
   are added. Not after.

## 2. Type

9. Use a `textTheme` slot. The ladder is continuous: 11 · 12 · 14 · 15 · 16 ·
   18 · 20 · 22 · 24 · 28 · 32. There is no legitimate `fontSize:` literal in a
   feature file.
10. **Nothing below 11px.** The 10px category badges are the current violation.
11. Body text keeps its `height` — 1.6 for `bodyLarge`/`bodyMedium`. The
    counsellor's replies are the longest text in the product and currently the
    only string with no line height set.
12. **`labelText`, never `hintText` alone.** A placeholder is not a label.

## 3. Space and shape

13. `AppSpacing` and `AppRadii`. No literal in `SizedBox(height:)`,
    `EdgeInsets`, or `BorderRadius.circular()`.
14. One card: `AppCard`. Radius 20. Not `Card()`, not a hand-rolled `Container`
    with a `BoxDecoration`.
15. Two borders, and they mean different things: `hairline` for decoration,
    `borderStrong` for any boundary that carries meaning (WCAG 1.4.11, 3:1).
16. Two shadows: `AppShadow.resting`, `AppShadow.floating`, and a preference for
    neither. A shadow means *floating above the content* and nothing else.
17. Four icon sizes: 16 / 20 / 28 / 64.

## 4. Motion

18. Four durations: `AppMotion.instant` 120 · `quick` 220 · `settle` 360 ·
    `reveal` 640. One ambient loop at 3s.
19. Four curves, and **none of them overshoot.** `Curves.elasticOut` and
    `Curves.easeOutBack` are banned outright: overshoot is a celebration
    gesture, it is the motion signature of the gamified product this one
    deliberately is not, and it is worst on the screens where it currently runs.
20. **Reduced motion is honoured.** `AppMotion.duration(context, d)` and
    `AppMotion.allowAmbient(context)`. Movement becomes cross-fade; ambient
    loops stop; opacity and colour are left alone.
21. Nothing celebratory on a transactional or emotional surface. No confetti, no
    success bounce, no haptic on a paywall.

## 5. Touch and reach

22. **48×48 minimum** on everything tappable, with 8pt between adjacent targets.
    A 20pt icon in a 48pt target is correct; do not grow the glyph.
23. Every interactive control has an accessible name — a `tooltip`, a visible
    label, or a `Semantics(label:)`.
24. Emoji used as a control gets `excludeSemantics: true` plus a real label.
    Its Unicode name describes a drawing, not a meaning.
25. A container holding text gets `minHeight`, never `height`. Never clamp the
    text scaler.

## 6. The four things that are never designed prettier

26. **Anything on the crisis path is never gated, never conditional, never
    auto-hiding, and never styled as fine print.** D7. `safety-surfaces.md`
    is the treatment for the two hardest cases.
27. **No dark patterns, named.** No countdown, scarcity claim, social-proof
    count, strikethrough price, confirmshame, pre-ticked box, bundled consent,
    or de-emphasised decline. The decline is a real button at the same size as
    the accept. FTC *Bringing Dark Patterns to Light* and EDPB Guidelines 3/2022
    are the reference taxonomies; `safety-surfaces.md` §1.4 maps each ban to a
    named pattern so a reviewer can cite one.
28. **No number, score, percentage, bar, gauge or plotted position in the
    facilitator report.** Including a 2×2 with the couple on it, which is a
    score with better graphic design. `facilitator-report.md` §4a.
29. **Faith surfaces carry no tradition's iconography in their chrome.** The
    tagging is the feature; the frame stays neutral and the content carries the
    tradition. A single symbol tells every other tradition that the tagging is
    decoration over a default.

## 7. The rule that outranks the rest

30. **Where a visual defect is downstream of a functional one, spec it and flag
    it — do not fix the appearance.** The ugliness is the evidence. Three items
    are currently held on this basis: the counselling session's empty state, the
    session-history screens, and the memory transparency panel. Each is recorded
    in `audit.md` with the functional defect it waits on.

---

## Making it stick

Every rule above was true once before. `app_colors.dart`'s comments describe a
previous cleanup of exactly these categories, and the categories came back,
because nothing enforced them.

**The single highest-leverage item in all of these documents is `audit.md`
item 21** — a CI grep, with an allowlist carrying a one-line reason per
exemption, failing in both directions. Same construction as the support-icon
static test and the `boundary.py` import test, both of which this repository
already has and both of which work.

Design review does not scale to 187 files. A grep does.
