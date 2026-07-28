import 'package:flutter/material.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_dimens.dart';

/// The app's standard card surface.
///
/// This shell — zero elevation, white fill, rounded corners, hairline border —
/// was copy-pasted in roughly ten places across home, the daily ritual, games,
/// goals, commitments and faith, drifting to radius 14, 16 and 20 along the
/// way. Having one definition is what keeps the inner app visually consistent
/// with the onboarding flow.
///
/// Pass [onTap] to make the whole card tappable; the ink ripple is clipped to
/// the card's radius rather than overflowing its corners.
class AppCard extends StatelessWidget {
  /// Card contents. Padded by [padding].
  final Widget child;

  /// Makes the entire card tappable when non-null.
  final VoidCallback? onTap;

  /// Interior padding. Defaults to [AppSpacing.xl].
  final EdgeInsetsGeometry padding;

  /// Fill colour. Defaults to white.
  final Color? color;

  /// Optional accent for the border — used to lift a card that carries the
  /// screen's primary action above the others.
  final Color? borderColor;

  /// Optional gradient fill. Takes precedence over [color] when set.
  final Gradient? gradient;

  const AppCard({
    required this.child,
    this.onTap,
    this.padding = const EdgeInsets.all(AppSpacing.xl),
    this.color,
    this.borderColor,
    this.gradient,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    final radius = BorderRadius.circular(AppRadii.card);

    return DecoratedBox(
      decoration: BoxDecoration(
        color: gradient == null ? (color ?? Colors.white) : null,
        gradient: gradient,
        borderRadius: radius,
        border: Border.all(
          color: borderColor ?? AppColors.softCharcoal.withValues(alpha: 0.05),
        ),
      ),
      child: Material(
        type: MaterialType.transparency,
        child: InkWell(
          onTap: onTap,
          borderRadius: radius,
          child: Padding(padding: padding, child: child),
        ),
      ),
    );
  }
}
