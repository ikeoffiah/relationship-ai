/// Spacing and corner-radius tokens.
///
/// Before these existed, every screen re-declared its own literals: gaps of
/// 4/6/8/10/12/14/16/20/24/28/32 were used interchangeably for the same job,
/// and the identical card shell appeared at radius 14, 16 and 20 in different
/// files. Naming them makes the drift visible and keeps the inner app on the
/// same rhythm as the onboarding flow.
library;

import 'package:flutter/painting.dart';

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

/// Icon sizes.
///
/// The app currently draws icons at nineteen distinct sizes — 6, 13, 14, 15,
/// 16, 18, 19, 20, 21, 22, 24, 26, 32, 40, 48, 56, 64, 72, 80 — with 16, 18 and
/// 20 all roughly equally common, so there is no default to fall back on. The
/// worst of it is in the empty states, where the same "nothing here yet"
/// illustration is 56pt on one screen, 64pt on another and 72pt on a third.
///
/// Four sizes. An icon that does not fit one of them is either decoration
/// (make it [hero]) or it is trying to be text.
class AppIconSize {
  AppIconSize._();

  /// 16 — inline with body text: a lock beside a label, a chevron in a row.
  /// Never interactive on its own; a 16pt icon cannot be a 48pt target
  /// without padding that makes the row look broken.
  static const double sm = 16;

  /// 20 — the default. App-bar actions, list leading icons, buttons.
  static const double md = 20;

  /// 28 — an icon that is the main content of its own control: a call
  /// control, a large toggle, a feature tile.
  static const double lg = 28;

  /// 64 — the single illustrative size, for empty states and status screens.
  /// One value, so "nothing here yet" is the same weight everywhere it
  /// appears. Draw it at [AppColors.rosePeach] or [AppColors.mutedInk], never
  /// at full-strength charcoal — an empty state should be quiet.
  static const double hero = 64;
}

/// Stroke widths.
///
/// Five widths are currently in use (hairline, 1, 1.5, 2, 3) with no rule for
/// which means what: 1.5 dominates `shared/widgets` and the auth screens while
/// the rest of the app uses the 1px default, so the sign-in flow is drawn
/// slightly heavier than the product behind it.
class AppStroke {
  AppStroke._();

  /// 1 — decorative separation. Pair with [AppColors.hairline].
  static const double hairline = 1;

  /// 1.5 — a boundary carrying meaning: an input outline, an unselected
  /// segment. Pair with [AppColors.borderStrong].
  static const double edge = 1.5;

  /// 2.5 — selected, active, or focused. Must be paired with a change that is
  /// not the border, because a stroke-weight change alone is invisible to a
  /// significant number of people. Pair with [AppColors.focusRing].
  static const double focus = 2.5;
}

/// Touch targets.
class AppTouch {
  AppTouch._();

  /// 48 — the minimum height *and* width of anything tappable.
  ///
  /// Both platform guidelines land here (Apple states 44pt, Material 48dp;
  /// WCAG 2.2 SC 2.5.8 sets 24 CSS px as an absolute floor and 44 as the
  /// enhanced level). 48 satisfies all three, so there is one number.
  ///
  /// This is a *target* size, not a *visual* size. A 20pt icon inside a 48pt
  /// tap area is correct and is what [AppIconSize.md] assumes. Use
  /// `MaterialTapTargetSize.padded`, or wrap in a `SizedBox`; do not grow the
  /// glyph.
  ///
  /// The rows of five `ChoiceChip`s in the questionnaire, and the five-emoji
  /// check-in, are the two places this is most clearly violated today — and
  /// they are, respectively, the longest task in the app and the one it asks
  /// people to do every day.
  static const double min = 48;

  /// 8 — minimum gap between two adjacent targets. Two 48pt targets flush
  /// against each other are one 96pt target as far as a shaking hand is
  /// concerned.
  static const double gap = 8;
}

/// Shadows.
///
/// The card theme sets `elevation: 0` and every one of the 48 `elevation:`
/// declarations in the app respects it — so Material elevation is genuinely
/// under control. Depth then gets faked with `BoxShadow` in 25 places instead,
/// each with its own blur, offset and alpha, which is the same drift wearing a
/// different name.
///
/// Two shadows, and a strong preference for neither. This palette separates
/// surfaces by warmth and a hairline; it does not need to lift them off the
/// page. A shadow here should mean *this is floating above the content* — a
/// sheet, a toast, a menu — and nothing else.
class AppShadow {
  AppShadow._();

  /// Something resting on the page that needs its edge found: a bottom nav, a
  /// sticky header. Barely there by design.
  static const List<BoxShadow> resting = [
    BoxShadow(
      color: Color(0x0F3B2A24),
      blurRadius: 12,
      offset: Offset(0, 2),
    ),
  ];

  /// Something genuinely floating over the content: a bottom sheet, a dialog,
  /// a toast, the paywall.
  static const List<BoxShadow> floating = [
    BoxShadow(
      color: Color(0x1A3B2A24),
      blurRadius: 28,
      offset: Offset(0, 8),
    ),
  ];
}
