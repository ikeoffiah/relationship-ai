import 'package:flutter/material.dart';
import 'package:mobile/features/sessions/joint_session_entry_screen.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/features/notifications/models/notification_model.dart';
import 'package:mobile/features/notifications/viewmodels/notification_viewmodel.dart';
import 'package:mobile/shared/widgets/get_help_now_button.dart';

class NotificationCenterScreen extends StatefulWidget {
  const NotificationCenterScreen({super.key});

  @override
  State<NotificationCenterScreen> createState() => _NotificationCenterScreenState();
}

class _NotificationCenterScreenState extends State<NotificationCenterScreen> {
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final userId = context.read<AuthViewModel>().user?.id;
      if (userId != null) {
        context.read<NotificationViewModel>().loadNotifications(userId);
      }
    });
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    final userId = context.read<AuthViewModel>().user?.id;
    if (userId != null &&
        _scrollController.position.pixels >= _scrollController.position.maxScrollExtent - 200) {
      context.read<NotificationViewModel>().loadMore(userId);
    }
  }

  @override
  Widget build(BuildContext context) {
    final userId = context.watch<AuthViewModel>().user?.id ?? '';
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Notifications'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: false,
        actions: [
          Consumer<NotificationViewModel>(
            builder: (context, vm, _) {
              if (vm.unreadCount == 0) return const SizedBox.shrink();
              return TextButton(
                onPressed: () => vm.markAllAsRead(userId),
                child: const Text(
                  'Mark all as read',
                  style: TextStyle(
                    color: AppColors.warmCoral,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              );
            },
          ),
        ],
      ),
      body: Column(
        children: [
          const GetHelpNowButton(),
          Expanded(
            child: Consumer<NotificationViewModel>(
              builder: (context, vm, _) {
                if (vm.isLoading) {
                  return const Center(
                    child: CircularProgressIndicator(color: AppColors.warmCoral),
                  );
                }

                if (vm.error != null) {
                  return _buildErrorState(vm, userId);
                }

                if (vm.isEmpty) {
                  return _buildEmptyState();
                }

                return RefreshIndicator(
                  onRefresh: () => vm.refresh(userId),
                  color: AppColors.warmCoral,
                  child: ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    itemCount: vm.notifications.length + (vm.isLoadingMore ? 1 : 0),
                    itemBuilder: (context, index) {
                      if (index == vm.notifications.length) {
                        return const Padding(
                          padding: EdgeInsets.all(24),
                          child: Center(
                            child: CircularProgressIndicator(color: AppColors.warmCoral),
                          ),
                        );
                      }
                      final notification = vm.notifications[index];
                      return _buildDismissibleCard(context, vm, userId, notification);
                    },
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDismissibleCard(
    BuildContext context,
    NotificationViewModel vm,
    String userId,
    NotificationItem item,
  ) {
    return Dismissible(
      key: Key(item.id),
      direction: DismissDirection.endToStart,
      onDismissed: (direction) => vm.deleteNotification(userId, item.id),
      background: Container(
        margin: const EdgeInsets.only(bottom: 12),
        decoration: BoxDecoration(
          color: Colors.red[100],
          borderRadius: BorderRadius.circular(16),
        ),
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 20),
        child: Icon(Icons.delete_outline, color: Colors.red[700]),
      ),
      child: _NotificationCard(
        item: item,
        onTap: () {
          vm.markAsRead(userId, item.id);
          _handleNavigation(context, item);
        },
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.notifications_none_rounded,
              size: 72,
              color: AppColors.warmCoral.withValues(alpha: 0.4),
            ),
            const SizedBox(height: 24),
            const Text(
              'All caught up!',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: AppColors.softCharcoal,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'No new notifications at this time.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 15,
                color: AppColors.softCharcoal.withValues(alpha: 0.6),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorState(NotificationViewModel vm, String userId) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.cloud_off_rounded, size: 64, color: AppColors.warmCoral),
            const SizedBox(height: 24),
            Text(
              vm.error!,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: AppColors.softCharcoal.withValues(alpha: 0.7),
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: () => vm.loadNotifications(userId),
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.warmCoral,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _handleNavigation(BuildContext context, NotificationItem item) {
    switch (item.type) {
      case NotificationType.sessionReminder:
        Navigator.pushNamed(context, '/chat');
        break;
      case NotificationType.partnerJoined:
        // The partner opened a joint session; enter the lobby as the recipient
        // (non-initiator) so they see the invite and can confirm.
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => JointSessionEntryScreen(
              isInitiator: false,
              partnerName: item.data['partner_name'] ?? 'Your partner',
            ),
          ),
        );
        break;
      case NotificationType.relayReceived:
        // A relay is waiting — that lives in the relay inbox, not history.
        Navigator.pushNamed(context, '/relay/inbox');
        break;
      case NotificationType.insightDetected:
        Navigator.pushNamed(context, '/consent');
        break;
      case NotificationType.safetyFollowup:
        Navigator.pushNamed(context, '/safety');
        break;
      case NotificationType.therapistConnected:
        Navigator.pushNamed(context, '/consent');
        break;
      case NotificationType.system:
        break;
    }
  }
}

class _NotificationCard extends StatelessWidget {
  final NotificationItem item;
  final VoidCallback onTap;

  const _NotificationCard({required this.item, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: _typeColor(item.type).withValues(alpha: 0.06),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
          border: !item.read
              ? const Border(
                  left: BorderSide(
                    color: AppColors.warmCoral,
                    width: 4,
                  ),
                )
              : null,
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: _typeColor(item.type).withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(
                  _typeIcon(item.type),
                  color: _typeColor(item.type),
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: Text(
                            item.title,
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: !item.read ? FontWeight.bold : FontWeight.w600,
                              color: AppColors.softCharcoal,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          _formatDate(item.createdAt),
                          style: TextStyle(
                            fontSize: 11,
                            color: AppColors.softCharcoal.withValues(alpha: 0.5),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      item.body,
                      style: TextStyle(
                        fontSize: 13,
                        color: AppColors.softCharcoal.withValues(alpha: item.read ? 0.6 : 0.8),
                        height: 1.4,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _typeColor(NotificationType type) {
    switch (type) {
      case NotificationType.sessionReminder:
        return AppColors.warmCoral;
      case NotificationType.partnerJoined:
      case NotificationType.therapistConnected:
        return AppColors.calmTeal;
      case NotificationType.relayReceived:
        return const Color(0xFF8B5CF6); // purple
      case NotificationType.insightDetected:
        return AppColors.sageGreen;
      case NotificationType.safetyFollowup:
        return Colors.red[400]!;
      case NotificationType.system:
        return AppColors.softCharcoal;
    }
  }

  IconData _typeIcon(NotificationType type) {
    switch (type) {
      case NotificationType.sessionReminder:
        return Icons.alarm_rounded;
      case NotificationType.partnerJoined:
        return Icons.people_outline_rounded;
      case NotificationType.relayReceived:
        return Icons.mail_outline_rounded;
      case NotificationType.insightDetected:
        return Icons.lightbulb_outline_rounded;
      case NotificationType.safetyFollowup:
        return Icons.security_rounded;
      case NotificationType.therapistConnected:
        return Icons.badge_outlined;
      case NotificationType.system:
        return Icons.info_outline_rounded;
    }
  }

  String _formatDate(DateTime dt) {
    final now = DateTime.now();
    final diff = now.difference(dt);
    if (diff.inMinutes < 60) {
      return diff.inMinutes <= 1 ? 'Just now' : '${diff.inMinutes}m ago';
    }
    if (diff.inHours < 24) {
      return '${diff.inHours}h ago';
    }
    return '${dt.day}/${dt.month}';
  }
}
