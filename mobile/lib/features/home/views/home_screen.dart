import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:provider/provider.dart' as provider;
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/features/relationship/relationship_viewmodel.dart';
import 'package:mobile/features/home/home_notifier.dart';
import 'package:mobile/shared/widgets/get_help_now_button.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final relVM = provider.Provider.of<RelationshipViewModel>(context, listen: false);
      ref.read(homeProvider.notifier).fetchHomeData(relVM);
    });
  }

  @override
  Widget build(BuildContext context) {
    final homeState = ref.watch(homeProvider);
    final authVM = provider.Provider.of<AuthViewModel>(context);
    final relVM = provider.Provider.of<RelationshipViewModel>(context);
    final firstName = authVM.user?.name?.split(' ').first ?? 'User';

    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 24),
              Text(
                'Good day,',
                style: TextStyle(fontSize: 16, color: AppColors.softCharcoal.withValues(alpha: 0.6)),
              ),
              Text(
                firstName,
                style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: AppColors.softCharcoal),
              ),
              const SizedBox(height: 24),
              Expanded(
                child: ListView(
                  children: [
                    _buildIndividualSessionCard(),
                    const SizedBox(height: 16),
                    _buildJointSessionCard(homeState, relVM),
                    const SizedBox(height: 16),
                    _buildAsyncRelayCard(homeState),
                    const SizedBox(height: 16),
                    _buildPartnerConnectionBanner(homeState),
                    const SizedBox(height: 32),
                  ],
                ),
              ),
              const GetHelpNowButton(),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildIndividualSessionCard() {
    return Card(
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(color: AppColors.softCharcoal.withValues(alpha: 0.05)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.lock_outline_rounded, color: AppColors.calmTeal),
                SizedBox(width: 8),
                Text('🟢 Individual session', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              ],
            ),
            const SizedBox(height: 8),
            const Text('Start a private reflection session with your AI guide.', style: TextStyle(color: Colors.grey)),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () {
                // Navigate to ChatScreen
                Navigator.of(context).pushNamed('/chat');
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.calmTeal,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: const Text('Begin session', style: TextStyle(color: Colors.white)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildJointSessionCard(HomeState homeState, RelationshipViewModel relVM) {
    if (homeState.relationshipStatus != RelationshipStatus.active) {
      return const SizedBox.shrink();
    }

    final isEnrolled = homeState.partnerJointSessionEnrolled;
    final partnerName = homeState.partnerDisplayName ?? 'Partner';

    return Card(
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(color: AppColors.softCharcoal.withValues(alpha: 0.05)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.people_outline_rounded, color: AppColors.warmCoral),
                SizedBox(width: 8),
                Text('👥 Joint session', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              isEnrolled ? '$partnerName is enrolled.' : '$partnerName hasn\'t enabled joint sessions.',
              style: const TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: isEnrolled
                  ? () {
                      Navigator.of(context).pushNamed('/chat', arguments: {'isJoint': true});
                    }
                  : null,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.warmCoral,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: const Text('Start joint session', style: TextStyle(color: Colors.white)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAsyncRelayCard(HomeState homeState) {
    if (homeState.relationshipStatus != RelationshipStatus.active || homeState.pendingRelayMessageCount == 0) {
      return const SizedBox.shrink();
    }

    return Card(
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(color: AppColors.softCharcoal.withValues(alpha: 0.05)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.mail_outline_rounded, color: AppColors.goldMedium),
                SizedBox(width: 8),
                Text('📨 Async relay', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              ],
            ),
            const SizedBox(height: 8),
            Text('${homeState.pendingRelayMessageCount} message waiting'),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () {
                Navigator.of(context).pushNamed('/relay/inbox');
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.goldMedium,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: const Text('View relay inbox', style: TextStyle(color: Colors.white)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPartnerConnectionBanner(HomeState homeState) {
    if (homeState.relationshipStatus == RelationshipStatus.active) {
      return const SizedBox.shrink();
    }

    if (homeState.relationshipStatus == RelationshipStatus.pending) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.calmTeal.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(16),
        ),
        child: const Text(
          'Waiting for your partner to accept your invite.',
          style: TextStyle(color: AppColors.softCharcoal, fontWeight: FontWeight.w500),
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.warmCoral.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.link_rounded, color: AppColors.warmCoral),
              SizedBox(width: 8),
              Text('🔗 Connect with your partner', style: TextStyle(fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 8),
          const Text('Invite them to unlock joint sessions and shared insights.', style: TextStyle(color: Colors.grey)),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: () {
              Navigator.of(context).pushNamed('/relationship/invite');
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.warmCoral,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            child: const Text('Send invite', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }
}
