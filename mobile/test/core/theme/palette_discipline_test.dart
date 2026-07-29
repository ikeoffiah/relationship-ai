import 'dart:io';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/theme/app_colors.dart';

/// Guards against the palette drifting again.
///
/// The inner app had accumulated ten hardcoded colours that were Tailwind's
/// defaults — a different design system's palette, in screens where every
/// neighbouring case already used this one. Nobody did that on purpose; it
/// happens one `Color(0xFF8B5CF6)` at a time, when the palette has no obvious
/// token for the case in hand and the deadline is closer than the style guide.
///
/// A lint is the only thing that actually holds a line like this.
void main() {
  /// Contrast ratio per WCAG 2.1, which is what "4.5:1" in the design notes
  /// means. Computed rather than asserted, because a comment claiming a ratio
  /// is worth nothing once someone nudges the hex.
  double contrast(Color a, Color b) {
    double channel(double c) =>
        c <= 0.03928 ? c / 12.92 : math.pow((c + 0.055) / 1.055, 2.4).toDouble();
    double luminance(Color c) =>
        0.2126 * channel(c.r) + 0.7152 * channel(c.g) + 0.0722 * channel(c.b);

    final la = luminance(a);
    final lb = luminance(b);
    final hi = la > lb ? la : lb;
    final lo = la > lb ? lb : la;
    return (hi + 0.05) / (lo + 0.05);
  }

  test('no colour literals live outside the theme', () {
    final offenders = <String>[];
    for (final entity in Directory('lib').listSync(recursive: true)) {
      if (entity is! File || !entity.path.endsWith('.dart')) continue;
      if (entity.path.contains('core/theme')) continue;
      final source = entity.readAsStringSync();
      for (final match in RegExp(r'Color\(0x[0-9a-fA-F]{8}\)').allMatches(source)) {
        offenders.add('${entity.path}: ${match.group(0)}');
      }
    }
    expect(
      offenders,
      isEmpty,
      reason:
          'Hardcoded colours belong in AppColors with a name saying what they '
          'are for. If none of the existing tokens fit, that is a signal the '
          'palette is missing a role — add the token, do not inline the hex.\n'
          '${offenders.join('\n')}',
    );
  });

  test('category inks stay legible as small text on cream', () {
    // They render as 10px bold on a 10%-alpha wash of themselves, so a pastel
    // that looks right in a mock is unreadable on a phone.
    const inks = {
      'categoryTeal': AppColors.categoryTeal,
      'categoryRust': AppColors.categoryRust,
      'categoryAmber': AppColors.categoryAmber,
      'categorySage': AppColors.categorySage,
      'categoryPlum': AppColors.categoryPlum,
      'categoryStone': AppColors.categoryStone,
    };
    inks.forEach((name, ink) {
      expect(
        contrast(ink, AppColors.creamWhite),
        greaterThanOrEqualTo(4.5),
        reason: '$name is too pale to read at badge size',
      );
    });
  });

  test('no category ink collides with the crisis red', () {
    // crisis is reserved for genuine emergency affordances. A category badge
    // that reads as the emergency colour spends urgency the product cannot
    // then get back when it actually needs it.
    const inks = [
      AppColors.categoryTeal,
      AppColors.categoryRust,
      AppColors.categoryAmber,
      AppColors.categorySage,
      AppColors.categoryPlum,
      AppColors.categoryStone,
    ];
    for (final ink in inks) {
      expect(ink, isNot(AppColors.crisis));
    }
  });
}
