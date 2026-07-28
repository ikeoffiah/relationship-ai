import 'package:flutter/material.dart';

import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/hubs/hub_scaffold.dart';

/// Everything the couple does *together* — playful, opt-in, no wrong answers.
///
/// Games, Focus, Commitments and Goals used to be icon buttons inside the
/// Daily Ritual app bar, which is a navigation menu disguised as chrome. Two
/// Truths sat one level below that again, and the @bliss plan was reachable
/// only through a snackbar that appeared once, after you had already used it.
class UsScreen extends StatelessWidget {
  const UsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    void go(String route) => Navigator.of(context).pushNamed(route);

    return HubScaffold(
      title: 'Us',
      intro: 'Light things to do together. Nothing here is homework.',
      destinations: [
        HubDestination(
          icon: Icons.videogame_asset_outlined,
          title: 'Games',
          blurb: 'Answer about yourself, then guess each other.',
          accent: AppColors.warmCoral,
          onTap: () => go('/engagement/games'),
        ),
        HubDestination(
          icon: Icons.psychology_alt_outlined,
          title: 'Two Truths & a Lie',
          blurb: 'Write three. See if they can spot the lie.',
          accent: AppColors.softRose,
          onTap: () => go('/engagement/two-truths'),
        ),
        HubDestination(
          icon: Icons.spa_outlined,
          title: 'Focus together',
          blurb: 'Put the phones down for a while. Either of you can end it.',
          accent: AppColors.calmTeal,
          onTap: () => go('/engagement/focus'),
        ),
        HubDestination(
          icon: Icons.favorite_border_rounded,
          title: 'Commitments',
          blurb: 'Little promises — a surprise for them, or one you keep together.',
          accent: AppColors.warmCoral,
          onTap: () => go('/engagement/commitments'),
        ),
        HubDestination(
          icon: Icons.flag_outlined,
          title: 'Shared goals',
          blurb: 'Something you are working toward, and how it is going.',
          accent: AppColors.goldDark,
          onTap: () => go('/engagement/goals'),
        ),
        HubDestination(
          icon: Icons.event_available_outlined,
          title: 'Your plan',
          blurb: 'Reminders and dates you asked Bliss to keep for you.',
          accent: AppColors.sageGreen,
          onTap: () => go('/engagement/bliss'),
        ),
        HubDestination(
          icon: Icons.auto_stories_outlined,
          title: 'Our story',
          blurb: 'What you are building, and the repairs along the way.',
          accent: AppColors.softRose,
          onTap: () => go('/our-story'),
        ),
      ],
    );
  }
}
