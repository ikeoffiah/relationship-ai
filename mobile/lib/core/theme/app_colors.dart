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
