import 'package:flutter/material.dart';

import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/hubs/hub_scaffold.dart';

/// Yours alone.
///
/// Faith already promised "your partner never sees it", and reflections,
/// history, privacy and settings are all things you consult rather than things
/// you do — which is why they no longer take three of the four navigation
/// slots between them.
class YouScreen extends StatelessWidget {
  const YouScreen({super.key});

  @override
  Widget build(BuildContext context) {
    void go(String route) => Navigator.of(context).pushNamed(route);

    return HubScaffold(
      title: 'You',
      intro: 'Private to you. Your partner sees none of this.',
      destinations: [
        HubDestination(
          icon: Icons.self_improvement_outlined,
          title: 'Faith',
          blurb: 'A gentle daily rhythm. Take what serves you.',
          accent: AppColors.goldDark,
          onTap: () => go('/engagement/faith'),
        ),
        HubDestination(
          icon: Icons.auto_awesome_outlined,
          title: 'Your portrait',
          blurb: 'What Bliss has understood about how you connect.',
          accent: AppColors.softRose,
          onTap: () => go('/onboarding/portrait'),
        ),
        HubDestination(
          icon: Icons.history_rounded,
          title: 'Past sessions',
          blurb: 'Everything you have talked through before.',
          accent: AppColors.calmTeal,
          onTap: () => go('/history'),
        ),
        HubDestination(
          icon: Icons.lock_outline_rounded,
          title: 'Privacy',
          blurb: 'What is stored, what is shared, and what you can delete.',
          accent: AppColors.sageGreen,
          onTap: () => go('/consent'),
        ),
        HubDestination(
          icon: Icons.settings_outlined,
          title: 'Settings',
          blurb: 'Account, security, notifications.',
          accent: AppColors.softCharcoal,
          onTap: () => go('/settings'),
        ),
      ],
    );
  }
}
