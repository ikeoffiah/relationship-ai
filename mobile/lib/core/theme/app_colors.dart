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

  /// calmTeal darkened until it is legible as a small glyph on [creamWhite]
  /// (about 4.4:1, where calmTeal itself manages 1.9:1). Used for the "seen"
  /// tick, where the whole point is that it reads at a glance without being
  /// loud enough to feel like surveillance.
  static const Color seenTick = Color(0xFF3E8E82);

  // Neutrals
  static const Color creamWhite = Color(0xFFFFFBF5);
  static const Color softIvory = creamWhite;
  static const Color softCharcoal = Color(0xFF4A4A4A);

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
  // They are rendered as 10px bold text on a 10%-alpha wash of themselves, so
  // each clears 4.5:1 against [creamWhite] — which is why they are deepened
  // rather than taken raw from the pastel brand hues, the same move as
  // [seenTick]. Swapping one for a pastel will look right in a mock and be
  // unreadable on a phone.
  //
  // They sit at deliberately *similar* luminance, so no category shouts louder
  // than another; a memory about a trigger is not more urgent than one about a
  // stated need. They are told apart by hue.
  //
  // And they are not the only carrier of meaning — every badge using them also
  // carries its label as text, which is what actually makes this legible to
  // someone who cannot separate the hues.

  /// How this person communicates.
  static const Color categoryTeal = Color(0xFF2F7D72);

  /// Something that sets them off. Distinct from [crisis], which is reserved.
  static const Color categoryRust = Color(0xFFB4462F);

  /// A recurring pattern in how conflict goes.
  static const Color categoryAmber = Color(0xFF8A6A22);

  /// A repair that landed.
  static const Color categorySage = Color(0xFF3F7A50);

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

}
