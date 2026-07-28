import 'package:flutter/material.dart';

import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_dimens.dart';
import 'package:mobile/shared/widgets/app_card.dart';
import 'package:mobile/shared/widgets/support_action.dart';

/// One destination inside a hub.
class HubDestination {
  final IconData icon;
  final String title;

  /// What the person gets, in their words — not what the feature is called.
  final String blurb;
  final Color accent;
  final VoidCallback onTap;

  /// Optional short status ("2 waiting", "Sam's turn") shown as a chip.
  final String? badge;

  const HubDestination({
    required this.icon,
    required this.title,
    required this.blurb,
    required this.accent,
    required this.onTap,
    this.badge,
  });
}

/// The shared layout for the Us / Talk / You tabs.
///
/// These exist because eleven features previously had nowhere to live and were
/// reachable only through icon buttons inside another feature's app bar. A hub
/// is deliberately a short, flat, readable list rather than a grid of icons:
/// the point is that someone can see everything available to them at a glance,
/// which was the whole failure of the old arrangement.
class HubScaffold extends StatelessWidget {
  final String title;
  final String intro;
  final List<HubDestination> destinations;

  const HubScaffold({
    required this.title,
    required this.intro,
    required this.destinations,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text(title, style: Theme.of(context).textTheme.titleLarge),
        actions: const [SupportAction()],
      ),
      body: SafeArea(
        top: false,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.xxl,
            AppSpacing.sm,
            AppSpacing.xxl,
            AppSpacing.xxxl,
          ),
          children: [
            Text(
              intro,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: AppColors.softCharcoal.withValues(alpha: 0.6),
              ),
            ),
            const SizedBox(height: AppSpacing.xl),
            for (final destination in destinations) ...[
              _HubTile(destination: destination),
              const SizedBox(height: AppSpacing.md),
            ],
          ],
        ),
      ),
    );
  }
}

class _HubTile extends StatelessWidget {
  final HubDestination destination;

  const _HubTile({required this.destination});

  @override
  Widget build(BuildContext context) {
    return AppCard(
      onTap: destination.onTap,
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Row(
        children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              color: destination.accent.withValues(alpha: 0.14),
              borderRadius: BorderRadius.circular(AppRadii.sm),
            ),
            child: Icon(destination.icon, size: 19, color: destination.accent),
          ),
          const SizedBox(width: AppSpacing.lg),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        destination.title,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ),
                    if (destination.badge != null) ...[
                      const SizedBox(width: AppSpacing.sm),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.sm,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: destination.accent.withValues(alpha: 0.16),
                          borderRadius: BorderRadius.circular(AppRadii.pill),
                        ),
                        child: Text(
                          destination.badge!,
                          style: Theme.of(context).textTheme.labelSmall
                              ?.copyWith(color: destination.accent),
                        ),
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  destination.blurb,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
          Icon(
            Icons.chevron_right_rounded,
            color: AppColors.softCharcoal.withValues(alpha: 0.35),
          ),
        ],
      ),
    );
  }
}
