import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:provider/provider.dart' as provider;
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/shared/widgets/app_card.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/features/relationship/relationship_viewmodel.dart';
import 'package:mobile/features/home/home_notifier.dart';
import 'package:mobile/features/notifications/viewmodels/notification_viewmodel.dart';
import 'package:mobile/core/services/push_service.dart';
import 'package:mobile/shared/widgets/support_action.dart';
import 'package:mobile/features/engagement/engagement_viewmodel.dart';
import 'package:mobile/features/home/views/today_hero.dart';
import 'package:mobile/features/home/views/connection_score_card.dart';
import 'package:mobile/features/home/views/insights_card.dart';
import 'package:mobile/features/couple_chat/couple_chat_viewmodel.dart';
import 'package:mobile/features/couple_chat/views/couple_chat_screen.dart';

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
      final relVM = provider.Provider.of<RelationshipViewModel>(
        context,
        listen: false,
      );
      final authVM = provider.Provider.of<AuthViewModel>(context, listen: false);
      final userId = authVM.user?.id;
      ref.read(homeProvider.notifier).fetchHomeData(relVM, userId: userId);
      provider.Provider.of<EngagementViewModel>(context, listen: false).loadRitual();
      if (userId != null) {
        provider.Provider.of<NotificationViewModel>(context, listen: false).fetchUnreadCount(userId);
        // Register this device for push now that we have an authenticated
        // session (the token POST needs the JWT). Idempotent + best-effort.
        pushService.register();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final homeState = ref.watch(homeProvider);
    final authVM = provider.Provider.of<AuthViewModel>(context);
    final relVM = provider.Provider.of<RelationshipViewModel>(context);
    final firstName = authVM.user?.name.split(' ').first ?? 'User';

    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: Text('Bliss', style: Theme.of(context).textTheme.titleLarge),
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          const SupportAction(),
          provider.Consumer<NotificationViewModel>(
            builder: (context, notifVM, _) {
              return Stack(
                children: [
                  IconButton(
                    icon: const Icon(
                      Icons.notifications_outlined,
                      color: AppColors.softCharcoal,
                      size: 26,
                    ),
                    onPressed: () {
                      Navigator.pushNamed(context, '/notifications');
                    },
                  ),
                  if (notifVM.unreadCount > 0)
                    Positioned(
                      right: 6,
                      top: 6,
                      child: Container(
                        padding: const EdgeInsets.all(4),
                        decoration: const BoxDecoration(
                          color: AppColors.warmCoral,
                          shape: BoxShape.circle,
                        ),
                        constraints: const BoxConstraints(
                          minWidth: 16,
                          minHeight: 16,
                        ),
                        child: Text(
                          '${notifVM.unreadCount}',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                          ),
                          textAlign: TextAlign.center,
                        ),
                      ),
                    ),
                ],
              );
            },
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 8),
              Text(
                'Good day,',
                style: TextStyle(
                  fontSize: 16,
                  color: AppColors.softCharcoal.withValues(alpha: 0.6),
                ),
              ),
              Text(
                firstName,
                style: const TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: AppColors.softCharcoal,
                ),
              ),
              const SizedBox(height: 24),
              Expanded(
                child: provider.Consumer<EngagementViewModel>(
                  builder: (context, engagement, _) => ListView(
                    children: [
                      // One quiet line instead of the gold streak banner —
                      // consistency, not a chain that resets to zero and tells
                      // a couple they failed each other on a hard week.
                      if (engagement.summary.daysActive30 > 0)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: Text(
                            'Together ${engagement.summary.daysActive30} of the '
                            'last ${engagement.summary.windowDays} days',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ),
                      // Above the ritual, below the "together N of 30" line.
                      // It renders nothing at all when the server says
                      // `hidden`, which is most of a new couple's first
                      // fortnight and any couple who has gone quiet.
                      Padding(
                        padding: EdgeInsets.only(
                          bottom: engagement.connection.isVisible ? 12 : 0,
                        ),
                        child: ConnectionScoreCard(
                          score: engagement.connection,
                          onOpenChat: () => _openCoupleChat(relVM, authVM),
                        ),
                      ),
                      // Under the score, above the ritual. Renders nothing at
                      // all when there is nothing to say, which is most weeks
                      // for most couples.
                      if (engagement.insights.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: InsightsCard(insights: engagement.insights),
                        ),
                      TodayHero(
                        vm: engagement,
                        onElsewhere: () => Navigator.of(
                          context,
                        ).pushNamed('/engagement/games'),
                      ),
                      const SizedBox(height: 12),
                      TodayCheckIn(vm: engagement),
                      const SizedBox(height: 16),
                      // What's live — only what needs attention.
                      _buildCoupleChatCard(homeState, relVM, authVM),
                      _buildAsyncRelayCard(homeState),
                      _buildPartnerConnectionBanner(homeState),
                      const SizedBox(height: 32),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Open the couple's thread. Extracted so the score card's quiet state can
  /// send somebody to the thing that helps rather than only to the number.
  void _openCoupleChat(RelationshipViewModel relVM, AuthViewModel authVM) {
    final relationshipId = relVM.currentRelationship?['id'] as String?;
    final userId = authVM.user?.id;
    if (relationshipId == null || userId == null) return;
    final partnerName =
        relVM.currentRelationship?['partner_name'] as String? ?? 'your partner';

    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => provider.ChangeNotifierProvider(
          create: (_) => CoupleChatViewModel(
            relationshipId: relationshipId,
            userId: userId,
          ),
          child: CoupleChatScreen(
            relationshipId: relationshipId,
            userId: userId,
            partnerName: partnerName,
          ),
        ),
      ),
    );
  }

  /// The couple's own conversation — the surface they open daily. Shown only
  /// once a partner is connected, since a thread needs two people.
  Widget _buildCoupleChatCard(
    dynamic homeState,
    RelationshipViewModel relVM,
    AuthViewModel authVM,
  ) {
    final relationshipId = relVM.currentRelationship?['id'] as String?;
    final userId = authVM.user?.id;
    if (relationshipId == null ||
        userId == null ||
        homeState.relationshipStatus != RelationshipStatus.active) {
      return const SizedBox.shrink();
    }
    final partnerName =
        relVM.currentRelationship?['partner_name'] as String? ?? 'your partner';

    return AppCard(
      borderColor: AppColors.warmCoral.withValues(alpha: 0.35),
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => provider.ChangeNotifierProvider(
            create: (_) => CoupleChatViewModel(
              relationshipId: relationshipId,
              userId: userId,
            ),
            child: CoupleChatScreen(
              relationshipId: relationshipId,
              userId: userId,
              partnerName: partnerName,
            ),
          ),
        ),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.chat_bubble_outline_rounded,
            color: AppColors.warmCoral,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Chat with $partnerName',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 4),
                Text(
                  'Your conversation, with Bliss alongside.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.softCharcoal.withValues(alpha: 0.7),
                  ),
                ),
              ],
            ),
          ),
          const Icon(Icons.chevron_right, color: AppColors.softCharcoal),
        ],
      ),
    );
  }

  Widget _buildAsyncRelayCard(HomeState homeState) {
    if (homeState.relationshipStatus != RelationshipStatus.active ||
        homeState.pendingRelayMessageCount == 0) {
      return const SizedBox.shrink();
    }

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.mail_outline_rounded, color: AppColors.goldMedium),
              SizedBox(width: 8),
              // The copy pass renamed this surface to "Say it better" but
              // missed its entry point here, so home still called it the
              // relay — our word for our plumbing, in the one place a user
              // meets it first.
              Text(
                'Something waiting for you',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            homeState.pendingRelayMessageCount == 1
                ? 'They wrote you one message.'
                : 'They wrote you '
                      '${homeState.pendingRelayMessageCount} messages.',
          ),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: () {
              Navigator.of(context).pushNamed('/relay/inbox');
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.goldMedium,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: const Text('Read it', style: TextStyle(color: Colors.white)),
          ),
        ],
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
          style: TextStyle(
            color: AppColors.softCharcoal,
            fontWeight: FontWeight.w500,
          ),
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
              Text(
                '🔗 Connect with your partner',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 8),
          const Text(
            'Invite them to unlock joint sessions and shared insights.',
            style: TextStyle(color: Colors.grey),
          ),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: () {
              Navigator.of(context).pushNamed('/relationship/invite');
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.warmCoral,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: const Text(
              'Send invite',
              style: TextStyle(color: Colors.white),
            ),
          ),
        ],
      ),
    );
  }
}
