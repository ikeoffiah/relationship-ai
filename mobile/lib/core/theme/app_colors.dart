import 'package:flutter/material.dart';

/// Color palette for the couples app
class AppColors {
  // Primary colors - love and warmth
  static const Color warmCoral = Color(0xFFFF9B8A);
  static const Color softRose = Color(0xFFFFB5C5);
  static const Color rosePeach = Color(0xFFFFD4C8);

  // Secondary colors - safety and regulation
  static const Color calmTeal = Color(0xFF7EBDB4);
  static const Color sageGreen = Color(0xFFA8C5B0);

  /// calmTeal darkened until it is legible as a small glyph on [creamWhite].
  /// Used for the "seen" tick, where the whole point is that it reads at a
  /// glance without being loud enough to feel like surveillance.
  ///
  /// **Corrected 2026-08-03.** The previous value was `#3E8E82` and this
  /// comment claimed "about 4.4:1". Measured, `#3E8E82` is **3.77:1** against
  /// [creamWhite] — enough for a large glyph, not enough for the 12–14px tick
  /// it is actually drawn at. Deepened by one step to clear 4.5:1 (4.51:1).
  /// The instinct in the original comment was right; the arithmetic was not.
  static const Color seenTick = Color(0xFF388076);

  // Neutrals
  static const Color creamWhite = Color(0xFFFFFBF5);
  static const Color softIvory = creamWhite;
  static const Color softCharcoal = Color(0xFF4A4A4A);

  // ── Inks ──────────────────────────────────────────────────────────────────
  // The rule this section exists to enforce:
  //
  //   **The brand hues are fills. They are not inks.**
  //
  // Every pastel in the palette above — coral, rose, peach, teal, sage, all
  // three golds — sits between 1.3:1 and 2.1:1 against [creamWhite]. That is
  // fine, and intended, for a *filled shape*. It means none of them may ever
  // carry text or a small glyph on cream, and nothing white may ever be
  // written on top of them. Both were happening, everywhere, before these
  // tokens existed. Measured:
  //
  //   white on warmCoral ................ 2.04:1   (every primary CTA)
  //   white on calmTeal ................. 2.14:1
  //   white on softRose ................. 1.66:1   (selected chips)
  //   warmCoral as text on creamWhite ... 1.98:1
  //   calmTeal  as icon on creamWhite ... 2.07:1
  //
  // 4.5:1 is the AA floor for body text; 3:1 for large text and for any
  // non-text thing that carries meaning. Nothing above clears either.

  /// The ink for text and glyphs sitting **on a brand fill** — a coral button,
  /// a rose chip, a gold notice, the user's own chat bubble.
  ///
  /// A warm near-black rather than pure charcoal, so it belongs to the same
  /// family as the fills it sits on. One value covers every fill in the
  /// palette, which is the point: there is no lookup table to get wrong.
  ///
  ///   on warmCoral 6.68:1 · softRose 8.21:1 · rosePeach 10.05:1
  ///   on calmTeal 6.37:1 · sageGreen 7.31:1 · goldDark 7.92:1
  ///   on goldMedium 8.91:1 · goldLight 10.08:1 · error 5.84:1
  ///
  /// **Not `Colors.white`.** Deepening coral far enough to carry white text
  /// lands on `#E82200`, which is no longer coral — it is a fire-engine red
  /// one step from [crisis], the one colour in this system that is reserved.
  /// Keeping the fill and darkening the ink preserves the brand *and* the
  /// reservation. It also simply looks calmer: dark-on-warm reads as paper,
  /// white-on-warm reads as a notification.
  static const Color onBrand = Color(0xFF3B2A24);

  /// Secondary text — captions, timestamps, helper lines, counts, the
  /// supporting half of a two-line list row.
  ///
  /// Replaces two habits: `softCharcoal.withValues(alpha: 0.6/0.7)`, which
  /// lands at 3.06:1 and 3.88:1 and fails AA at the small sizes it is always
  /// used at; and the ~40 `Colors.grey` / `Colors.grey.shade600` literals,
  /// which are cool grey dropped into a warm palette.
  ///
  /// 5.12:1 on [creamWhite], 5.28:1 on white, 4.74:1 on [neutralSurface] —
  /// so it holds up on every surface in the app, at any size.
  ///
  /// If a design wants text quieter than this, the answer is to make it
  /// smaller or to move it, not to fade it further. Faded text is not restraint;
  /// it is the same information, harder to read, for the people who already
  /// find reading hardest.
  static const Color mutedInk = Color(0xFF6F6B67);

  /// Disabled text and icons. The one place low contrast is correct, because
  /// unavailability is the meaning being carried.
  ///
  /// Anything disabled must **also** be non-interactive and announce itself as
  /// disabled to a screen reader — colour alone never communicates it.
  static const Color disabledInk = Color(0xFFB0ABA5);

  // ── Edges ─────────────────────────────────────────────────────────────────
  // Two border tokens, because "border" was doing two unrelated jobs at one
  // value. WCAG 1.4.11 asks 3:1 of anything whose *boundary* carries meaning
  // — a selected chip, a focused field, a toggle. It asks nothing of a line
  // drawn only to separate two things you can already tell apart.

  /// Decorative separation only: the hairline around a card, a divider between
  /// rows. ~1.1:1 and that is correct — it is texture, not information.
  /// If a border is the only thing telling the user something, use [borderStrong].
  static const Color hairline = Color(0xFFEDE8E1);

  /// A boundary that carries meaning: input field outlines, unselected
  /// segmented controls, the edge of anything the user is expected to find.
  /// 3.36:1 on [creamWhite], 3.46:1 on white, 3.11:1 on [neutralSurface].
  static const Color borderStrong = Color(0xFF8F8981);

  /// The keyboard/switch-control focus indicator. Deliberately the same warm
  /// near-black as [onBrand]: 13.2:1 on cream, 6.68:1 on coral, ≥11:1 on every
  /// semantic surface. One ring that is unmissable on every background in the
  /// app and confusable with nothing — in particular not with [crisis], which
  /// an accent-coloured focus ring in this palette would have to approach.
  static const Color focusRing = onBrand;

  // Accent - growth and milestones
  static const Color goldLight = Color(0xFFFFD89B);
  static const Color goldMedium = Color(0xFFFFC870);
  static const Color goldDark = Color(0xFFFFB84D);

  // Error color
  static const Color error = Color(0xFFF58C8C);

  // ── Semantic surfaces ───────────────────────────────────────────────────────
  // These exist so screens stop reaching for raw Material swatches. Before this,
  // the inner app had invented Colors.grey / amber / blue / indigo locally while
  // onboarding never left the palette — which is most of why the two halves of
  // the app looked like different products.

  /// Gold-tinted background for advisory notices (e.g. the AI disclosure).
  static const Color noticeSurface = Color(0xFFFFF9EC);

  /// Legible ink on [noticeSurface].
  static const Color noticeInk = Color(0xFF8A6A22);

  /// Teal-tinted background for calm/waiting states (turn-hold, "waiting on
  /// your partner").
  static const Color calmSurface = Color(0xFFF0F7F5);

  /// Warm neutral fill, replacing Colors.grey.shade100.
  static const Color neutralSurface = Color(0xFFF6F2ED);

  /// The counsellor's own message bubble.
  ///
  /// This exists because `assistant_message_bubble.dart` reaches for
  /// `colorScheme.surfaceContainerHighest`, and we never set that role — so
  /// Flutter supplies the Material 3 baseline, `#E6E0E9`, a cool lavender-grey
  /// from a different design system. The single most-looked-at surface in the
  /// paid feature is currently the one surface in the app that is not ours,
  /// and it is the wrong temperature against cream.
  ///
  /// Warm, one clear step deeper than [creamWhite] so the bubble has an edge
  /// without needing a stroke, and 11.5:1 under [onBrand] / 7.5:1 under
  /// [softCharcoal].
  static const Color assistantSurface = Color(0xFFF1EBE3);

  /// The user's own bubble in a counselling session, and the fill of a primary
  /// button. Named separately from [warmCoral] so that the pairing with
  /// [onBrand] is stated once rather than remembered at every call site.
  static const Color userBubble = warmCoral;

  /// Scrim for controls floating over video or photography, where the
  /// backdrop is arbitrary and no fill can be assumed legible. White icons on
  /// this read ≥9:1 over any frame content.
  static const Color overlayScrim = Color(0xB3000000);

  /// The single crisis red. Reserved for genuine emergency affordances inside
  /// the Support screen — never for ambient decoration. Previously this existed
  /// as three different hardcoded values (#B71C1C, red[700], red[400]).
  static const Color crisis = Color(0xFFB71C1C);

  // ── Category inks ─────────────────────────────────────────────────────────
  // For badges that distinguish a *kind* of thing: what sort of memory this is,
  // what sort of session that was. They replace ten hardcoded values that were
  // Tailwind's defaults (#6366F1, #EF4444, #F97316, #22C55E, #3B82F6, #8B5CF6)
  // — a different design system's palette, dropped into screens where every
  // neighbouring case already used this one.
  //
  // Two constraints they have to meet, and one they deliberately do not.
  //
  // They are rendered as bold text on a 10%-alpha wash of themselves, which is
  // why they are deepened rather than taken raw from the pastel brand hues —
  // the same move as [seenTick]. Swapping one for a pastel will look right in
  // a mock and be unreadable on a phone.
  //
  // **Corrected 2026-08-03, two things.** The original comment measured them
  // against [creamWhite], where all six cleared 4.5:1 — but that is not where
  // they are drawn. On their own 10% wash, which *is* where they are drawn,
  // four of the six sat between 4.16:1 and 4.36:1. Each has been deepened by
  // one step so the ≥4.5:1 claim is true in the rendering context rather than
  // in a simpler one. Measured on wash: teal 4.53 · rust 4.56 · amber 4.55 ·
  // sage 4.56 · plum 6.02 · stone 4.56.
  //
  // The second correction is the size, and it is not a colour problem. These
  // were specified at **10px**, which is below the floor any of them can be
  // rescued to; a 4.5:1 ratio at 10px is still a badge most people over forty
  // cannot read. Minimum is 11px — `textTheme.labelSmall` is that slot.
  //
  // They sit at deliberately *similar* luminance, so no category shouts louder
  // than another; a memory about a trigger is not more urgent than one about a
  // stated need. They are told apart by hue.
  //
  // And they are not the only carrier of meaning — every badge using them also
  // carries its label as text, which is what actually makes this legible to
  // someone who cannot separate the hues.

  /// How this person communicates.
  static const Color categoryTeal = Color(0xFF2C766C);

  /// Something that sets them off. Distinct from [crisis], which is reserved.
  static const Color categoryRust = Color(0xFFB4462F);

  /// A recurring pattern in how conflict goes.
  static const Color categoryAmber = Color(0xFF85661F);

  /// A repair that landed.
  static const Color categorySage = Color(0xFF3D764D);

  /// Something they have asked for out loud; also the relay session type.
  static const Color categoryPlum = Color(0xFF6B4B7A);

  /// Uncategorised. Quiet on purpose — an unknown should not draw the eye.
  static const Color categoryStone = Color(0xFF6E6A66);

  // ── Video chrome ──────────────────────────────────────────────────────────
  // A call goes dark so the faces carry the frame, which is a deliberate
  // departure from the cream everywhere else rather than an oversight. Named
  // so it reads as a decision instead of two magic hex values.

  /// The backdrop behind a video call.
  static const Color videoChrome = Color(0xFF1A1A1A);

  /// Tiles and controls sitting on [videoChrome].
  static const Color videoSurface = Color(0xFF2A2A2A);

  // Gradient definitions
  static const LinearGradient splashGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [softRose, rosePeach],
  );

  static const LinearGradient goldGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [goldLight, goldMedium, goldDark],
  );

  // ── The two gradients that were being retyped ─────────────────────────────
  // Both of these already exist in the app several times over, written out by
  // hand at each site — which is how they drifted. [authBackdrop] appears
  // verbatim on four auth screens. [selectedFill] appears on five onboarding
  // surfaces, and three of the five omit `begin`/`end`, so the same "this one
  // is chosen" state is lit from a different angle depending on which screen
  // you are standing on. Nobody would specify that; it is just what happens
  // when a value has no name.

  /// Full-bleed backdrop for the auth screens (login, signup, forgot, reset).
  static const LinearGradient authBackdrop = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [softRose, rosePeach, creamWhite],
  );

  /// The "this option is selected" fill used through onboarding.
  /// Anything drawn on it takes [onBrand]: white on this reads 1.7–2.0:1.
  static const LinearGradient selectedFill = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [warmCoral, softRose],
  );
}
