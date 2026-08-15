import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/analytics/analytics.dart';
import 'package:mobile/core/analytics/analytics_event.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/features/relationship/relationship_viewmodel.dart';

import 'package:mobile/features/home/views/home_screen.dart';
import 'package:mobile/features/hubs/talk_screen.dart';
import 'package:mobile/features/hubs/us_screen.dart';
import 'package:mobile/features/hubs/you_screen.dart';
import 'package:mobile/shared/widgets/custom_bottom_nav.dart';

class MainNavigationScreen extends StatefulWidget {
  const MainNavigationScreen({super.key});

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  int _selectedIndex = 0;

  /// The four tabs, in nav order, as analytics surfaces.
  static const _surfaces = [
    AnalyticsSurface.today,
    AnalyticsSurface.us,
    AnalyticsSurface.talk,
    AnalyticsSurface.you,
  ];

  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
    });
    // The cheapest possible answer to "which parts of this product does anyone
    // actually open", which is currently unanswerable for all twenty-one
    // feature areas. Fire-and-forget, and a no-op until consent is granted.
    context.read<Analytics>().record(SurfaceOpened(surface: _surfaces[index]));
  }

  @override
  Widget build(BuildContext context) {
    context.watch<AuthViewModel>();
    final relationshipViewModel = context.watch<RelationshipViewModel>();

    // Four tabs, and three of them are the product rather than admin. The old
    // arrangement spent Home / History / Privacy / Settings — leaving eleven
    // features with nowhere to live while three slots went to screens people
    // open about once a month.
    final List<Widget> screens = [
      const HomeScreen(),
      const UsScreen(),
      const TalkScreen(),
      const YouScreen(),
    ];

    final isPending =
        relationshipViewModel.status == RelationshipStatus.pending;
    final pendingEmail =
        relationshipViewModel.currentRelationship?['invitee_email'] ??
        'your partner';

    return Scaffold(
      body: Column(
        children: [
          // `top: true` only, and it matters. These banners sit above the child
          // screens, each of which has its own SafeArea — so the children were
          // inset correctly and the banners were not, putting the AI disclosure
          // under the Dynamic Island on every one of the four tabs. It rendered
          // as "You are talking to a[…]l therapist", which is the most-seen
          // pixel in the app saying the opposite of what it means.
          //
          // Bottom is left false: the nav bar below handles that inset, and
          // taking it here would add a second gap under the banner.
          SafeArea(
            bottom: false,
            child: Column(
              children: [
                if (isPending) _buildPendingInviteBanner(pendingEmail),
              ],
            ),
          ),
          Expanded(
            child: IndexedStack(index: _selectedIndex, children: screens),
          ),
        ],
      ),
      bottomNavigationBar: CustomBottomNav(
        currentIndex: _selectedIndex,
        onTap: _onItemTapped,
        items: const [
          NavItem(icon: Icons.wb_sunny_rounded, label: 'Today'),
          NavItem(icon: Icons.favorite_rounded, label: 'Us'),
          NavItem(icon: Icons.chat_bubble_rounded, label: 'Talk'),
          NavItem(icon: Icons.person_rounded, label: 'You'),
        ],
      ),
    );
  }

  Widget _buildPendingInviteBanner(String email) {
    return Container(
      width: double.infinity,
      color: AppColors.calmTeal.withValues(alpha: 0.1),
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      child: Row(
        children: [
          const Icon(
            Icons.favorite_outline,
            size: 16,
            color: AppColors.calmTeal,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              'Waiting for $email to accept your invitation.',
              style: const TextStyle(
                fontSize: 12,
                color: AppColors.softCharcoal,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
