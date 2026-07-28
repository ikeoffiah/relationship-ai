/// Spacing and corner-radius tokens.
///
/// Before these existed, every screen re-declared its own literals: gaps of
/// 4/6/8/10/12/14/16/20/24/28/32 were used interchangeably for the same job,
/// and the identical card shell appeared at radius 14, 16 and 20 in different
/// files. Naming them makes the drift visible and keeps the inner app on the
/// same rhythm as the onboarding flow.
library;

/// Vertical and horizontal spacing steps.
class AppSpacing {
  AppSpacing._();

  /// 4 — hairline separation inside a row.
  static const double xs = 4;

  /// 8 — between tightly related elements (icon and its label).
  static const double sm = 8;

  /// 12 — between elements inside a card.
  static const double md = 12;

  /// 16 — default gap; card interior padding on compact surfaces.
  static const double lg = 16;

  /// 20 — card interior padding.
  static const double xl = 20;

  /// 24 — screen horizontal padding; gap between cards.
  static const double xxl = 24;

  /// 32 — between major sections of a screen.
  static const double xxxl = 32;
}

/// Corner radii.
class AppRadii {
  AppRadii._();

  /// 12 — chips, small buttons, inline fields.
  static const double sm = 12;

  /// 16 — text fields, compact cards.
  static const double md = 16;

  /// 20 — the standard card.
  static const double card = 20;

  /// 24 — bottom sheets, primary CTAs (onboarding's button radius).
  static const double lg = 24;

  /// Fully rounded — pills and indicator dots.
  static const double pill = 999;
}
