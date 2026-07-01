import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/features/consent/consent_dashboard_screen.dart';
import 'package:mobile/features/relationship/relationship_viewmodel.dart';

import 'package:mobile/features/home/views/home_screen.dart';
import 'package:mobile/features/history/session_history_screen.dart';
import 'package:mobile/features/settings/settings_screen.dart';

class MainNavigationScreen extends StatefulWidget {
  const MainNavigationScreen({super.key});

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  int _selectedIndex = 0;

  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
    });
  }

  @override
  Widget build(BuildContext context) {
    context.watch<AuthViewModel>();
    final relationshipViewModel = context.watch<RelationshipViewModel>();

    final List<Widget> screens = [
      const HomeScreen(),
      const SessionHistoryScreen(),
      const ConsentDashboardScreen(),
      const SettingsScreen(),
    ];

    final isPending =
        relationshipViewModel.status == RelationshipStatus.pending;
    final pendingEmail =
        relationshipViewModel.currentRelationship?['invitee_email'] ??
        'your partner';

    return Scaffold(
      body: Column(
        children: [
          _buildAIDisclosureBanner(),
          if (isPending) _buildPendingInviteBanner(pendingEmail),
          Expanded(
            child: IndexedStack(index: _selectedIndex, children: screens),
          ),
        ],
      ),
      floatingActionButton: _selectedIndex == 2 ? null : _buildCrisisButton(),
      bottomNavigationBar: BottomNavigationBar(
        items: const <BottomNavigationBarItem>[
          BottomNavigationBarItem(
            icon: Icon(Icons.home_outlined),
            activeIcon: Icon(Icons.home),
            label: 'Home',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.history_outlined),
            activeIcon: Icon(Icons.history),
            label: 'History',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.lock_outline_rounded),
            activeIcon: Icon(Icons.lock_rounded),
            label: 'Privacy',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.settings_outlined),
            activeIcon: Icon(Icons.settings),
            label: 'Settings',
          ),
        ],
        currentIndex: _selectedIndex,
        selectedItemColor: AppColors.warmCoral,
        unselectedItemColor: AppColors.softCharcoal.withValues(alpha: 0.5),
        onTap: _onItemTapped,
        backgroundColor: Colors.white,
        elevation: 8,
        type: BottomNavigationBarType.fixed,
      ),
    );
  }

  Widget _buildAIDisclosureBanner() {
    return Container(
      width: double.infinity,
      color: Colors.amber[50],
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      child: Row(
        children: [
          Icon(Icons.info_outline, size: 16, color: Colors.amber[900]),
          const SizedBox(width: 12),
          const Expanded(
            child: Text(
              'You are talking to an AI, not a licensed therapist.',
              style: TextStyle(
                fontSize: 12,
                color: Colors.black87,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCrisisButton() {
    return FloatingActionButton.extended(
      onPressed: () => _launchSafetyResources(),
      backgroundColor: Colors.red[700],
      icon: const Text('🆘', style: TextStyle(fontSize: 18)),
      label: const Text(
        'Get Help Now',
        style: TextStyle(fontWeight: FontWeight.bold),
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

  void _launchSafetyResources() {
    Navigator.of(context).pushNamed('/safety');
  }
}
