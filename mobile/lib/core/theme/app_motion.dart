import 'package:flutter/material.dart';

/// The motion vocabulary.
///
/// ## Why this file exists
///
/// `AppTheme` has declared `slowFade` (1200ms), `gentleMotion` (1500ms) and
/// `orbAnimation` (4s) since the beginning. **Nothing in the app has ever
/// referenced any of them** — `grep` returns the declarations and nothing
/// else. In their place, 47 animations across the app each picked their own
/// number: fourteen distinct millisecond values (100, 120, 150, 180, 200, 250,
/// 300, 400, 600, 800, 900, 1000, 1200, 1500) and six curves.
///
/// A design system's colours drifting is visible in a screenshot and someone
/// eventually files it. Motion drifting is not visible in a screenshot, so it
/// never gets filed — it is only felt, as the sense that the parts of a
/// product were built by different people. That is exactly the failure this
/// product cannot afford, because its whole claim is that it was made
/// carefully.
///
/// ## The brand argument, which decides the curves
///
/// This product removed its streak counter. Its connection score is allowed to
/// fall and hides itself on a bad week. The one thing every surface has to say
/// is *this will not try to manipulate you*.
///
/// Overshoot says the opposite. `Curves.elasticOut` and `Curves.easeOutBack`
/// — both currently in the app — make an element travel past its destination
/// and spring back. That is a celebration gesture. It is the motion signature
/// of a confetti burst, and it belongs to the class of product that awards you
/// a badge for opening it. In a couples-counselling app it is not merely
/// off-brand: it is at its worst on exactly the screens where it is currently
/// used, because it applies a party trick to somebody's relationship.
///
/// **So: no overshoot. Ever. There is no bouncy curve in this file, and that
/// is the point of the file.**
///
/// ## The durations
///
/// Four steps, and a deliberate refusal to add a fifth. The ratios matter more
/// than the absolute values: each step is roughly 1.6–2× the last, which is
/// far enough apart that a reader can tell two of them apart, and close enough
/// that nothing feels like a different system.
class AppMotion {
  AppMotion._();

  // ── Durations ─────────────────────────────────────────────────────────────

  /// 120ms — the element acknowledges you and nothing else moves.
  /// Press states, ripples, checkbox and switch flips, chip selection.
  ///
  /// Below ~100ms a change reads as a jump cut rather than a movement; above
  /// ~150ms a press state starts to feel like lag on the tap, because the user
  /// is waiting for confirmation they have already earned.
  static const Duration instant = Duration(milliseconds: 120);

  /// 220ms — one thing on screen changes. The default, and the answer whenever
  /// nobody has thought about it. Cards expanding, sheets snapping, list items
  /// settling, a value counting to its new position, tab crossfades.
  static const Duration quick = Duration(milliseconds: 220);

  /// 360ms — a whole surface arrives or leaves: bottom sheets, dialogs, page
  /// transitions, the paywall. Long enough to be followed by the eye, which is
  /// what makes an arriving surface feel offered rather than thrown.
  static const Duration settle = Duration(milliseconds: 360);

  /// 640ms — a deliberately unhurried reveal, used sparingly and only where
  /// slowness is the message. The two-sided daily reveal is the case this
  /// exists for: both partners' answers opening at once is the emotional
  /// centre of the product and should not snap.
  ///
  /// Reach for this maybe five times in the whole app. If a screen has two
  /// [reveal]s on it, one of them is [settle].
  static const Duration reveal = Duration(milliseconds: 640);

  /// 3s, repeating — ambient loops only: the breathing orb, a waiting
  /// shimmer, the slow pulse under "waiting for your partner".
  ///
  /// Ambient motion is the one kind that must be silenced under
  /// [prefersReducedMotion] rather than shortened, because it never stops and
  /// a shortened loop is a faster distraction, not a smaller one.
  static const Duration ambient = Duration(seconds: 3);

  // ── Curves ────────────────────────────────────────────────────────────────

  /// Something entering, or growing. Decelerates into place — fast at the
  /// start, so the response feels immediate, then eases to a stop rather than
  /// hitting one.
  static const Curve enter = Curves.easeOutCubic;

  /// Something leaving. Accelerates away: a departing element does not need
  /// the user's attention and should not hold it.
  static const Curve exit = Curves.easeInCubic;

  /// Something moving from one place on screen to another while staying
  /// present — a reorder, a sheet resizing, a value changing in place.
  static const Curve move = Curves.easeInOutCubic;

  /// Opacity-only changes, where a curve mostly reads as a flicker.
  static const Curve fade = Curves.linear;

  // ── Reduced motion ────────────────────────────────────────────────────────

  /// True when the operating system has been asked to reduce motion — iOS
  /// Settings → Accessibility → Motion → Reduce Motion, or the Android
  /// equivalent.
  ///
  /// This is not a niche preference. It is set by people with vestibular
  /// disorders, for whom a large moving surface causes actual nausea and
  /// dizziness, and by a much larger group who simply find animation tiring.
  /// **The app currently honours it nowhere** — `MediaQuery.disableAnimations`
  /// appears zero times in 187 files — so every one of the 47 animations plays
  /// at full amplitude regardless.
  ///
  /// The correct response is *not* to make everything instant. A UI where
  /// surfaces teleport is harder to follow, not easier. The rule is:
  ///
  ///  - **Movement** (slide, scale, translate, parallax) → replace with a
  ///    cross-fade of the same duration. The change still reads; nothing
  ///    travels.
  ///  - **Ambient loops** → stop entirely. Show the final frame.
  ///  - **Opacity and colour** → leave alone. They cause no vestibular
  ///    response and carry most of the meaning.
  static bool prefersReducedMotion(BuildContext context) =>
      MediaQuery.maybeDisableAnimationsOf(context) ?? false;

  /// The duration to use for [d], honouring the reduced-motion preference.
  ///
  /// Shortens rather than zeroes: `Duration.zero` makes `AnimatedFoo` widgets
  /// rebuild without a transition, which reads as a flash. 80ms is below the
  /// threshold at which most people perceive movement while still letting the
  /// framework interpolate.
  static Duration duration(BuildContext context, Duration d) =>
      prefersReducedMotion(context) ? const Duration(milliseconds: 80) : d;

  /// Whether an ambient loop ([ambient]) should run at all. Always check this
  /// before starting a `repeat()`.
  static bool allowAmbient(BuildContext context) =>
      !prefersReducedMotion(context);
}
