import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/history/models/session_history_model.dart';
import 'package:mobile/features/history/viewmodels/session_history_viewmodel.dart';
import 'package:mobile/features/history/viewmodels/session_detail_viewmodel.dart';
import 'package:mobile/features/history/session_detail_screen.dart';
import 'package:mobile/shared/widgets/get_help_now_button.dart';

class SessionHistoryScreen extends StatefulWidget {
  const SessionHistoryScreen({super.key});

  @override
  State<SessionHistoryScreen> createState() => _SessionHistoryScreenState();
}

class _SessionHistoryScreenState extends State<SessionHistoryScreen> {
  final _scrollController = ScrollController();
  static const _filters = ['all', 'individual', 'joint', 'relay'];
  static const _filterLabels = ['All', 'Individual', 'Joint', 'Relay'];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<SessionHistoryViewModel>().loadSessions();
    });
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 200) {
      context.read<SessionHistoryViewModel>().loadMore();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Your sessions'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: false,
      ),
      body: Column(
        children: [
          const GetHelpNowButton(),
          _buildFilterTabs(),
          Expanded(child: _buildBody()),
        ],
      ),
    );
  }

  Widget _buildFilterTabs() {
    return Consumer<SessionHistoryViewModel>(
      builder: (context, vm, _) {
        return Container(
          height: 46,
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(14),
            boxShadow: [
              BoxShadow(
                color: AppColors.warmCoral.withValues(alpha: 0.08),
                blurRadius: 10,
                offset: const Offset(0, 3),
              ),
            ],
          ),
          child: Row(
            children: List.generate(_filters.length, (i) {
              final isSelected = vm.filter == _filters[i];
              return Expanded(
                child: GestureDetector(
                  onTap: () => vm.setFilter(_filters[i]),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    margin: const EdgeInsets.all(4),
                    decoration: BoxDecoration(
                      color: isSelected ? AppColors.warmCoral : Colors.transparent,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      _filterLabels[i],
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: isSelected
                            ? FontWeight.bold
                            : FontWeight.normal,
                        color: isSelected ? Colors.white : AppColors.softCharcoal,
                      ),
                    ),
                  ),
                ),
              );
            }),
          ),
        );
      },
    );
  }

  Widget _buildBody() {
    return Consumer<SessionHistoryViewModel>(
      builder: (context, vm, _) {
        if (vm.isLoading) {
          return const Center(
            child: CircularProgressIndicator(color: AppColors.warmCoral),
          );
        }

        if (vm.error != null) {
          return _buildErrorState(vm);
        }

        if (vm.isEmpty) {
          return _buildEmptyState();
        }

        return RefreshIndicator(
          onRefresh: vm.refresh,
          color: AppColors.warmCoral,
          child: ListView.builder(
            controller: _scrollController,
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 100),
            itemCount: vm.sessions.length + (vm.isLoadingMore ? 1 : 0),
            itemBuilder: (context, index) {
              if (index == vm.sessions.length) {
                return const Padding(
                  padding: EdgeInsets.all(24),
                  child: Center(
                    child: CircularProgressIndicator(color: AppColors.warmCoral),
                  ),
                );
              }
              return _SessionCard(
                item: vm.sessions[index],
                onTap: () => _openDetail(vm.sessions[index]),
              );
            },
          ),
        );
      },
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.history_rounded, size: 72, color: AppColors.warmCoral.withValues(alpha: 0.4)),
            const SizedBox(height: 24),
            const Text(
              'No sessions yet',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: AppColors.softCharcoal,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'Start your first session from the Home tab.',
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

  Widget _buildErrorState(SessionHistoryViewModel vm) {
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
              onPressed: vm.loadSessions,
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

  void _openDetail(SessionHistoryItem item) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ChangeNotifierProvider(
          create: (_) => SessionDetailViewModel() as ChangeNotifier,
          child: SessionDetailScreen(sessionId: item.id),
        ),
      ),
    );
  }
}

// ───────────────────────── Session Card Widget ─────────────────────────

class _SessionCard extends StatelessWidget {
  final SessionHistoryItem item;
  final VoidCallback onTap;

  const _SessionCard({required this.item, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(
              color: _typeColor(item.type).withValues(alpha: 0.08),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Icon badge
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: _typeColor(item.type).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  _typeIcon(item.type),
                  color: _typeColor(item.type),
                  size: 22,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          item.type.label,
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.bold,
                            color: _typeColor(item.type),
                          ),
                        ),
                        const Spacer(),
                        Text(
                          _formatDate(item.dateTime),
                          style: TextStyle(
                            fontSize: 12,
                            color: AppColors.softCharcoal.withValues(alpha: 0.5),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${item.turnCount} turns',
                      style: TextStyle(
                        fontSize: 12,
                        color: AppColors.softCharcoal.withValues(alpha: 0.55),
                      ),
                    ),
                    if (item.summaryPreview.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(
                        '"${item.summaryPreview}"',
                        style: TextStyle(
                          fontSize: 14,
                          fontStyle: FontStyle.italic,
                          color: AppColors.softCharcoal.withValues(alpha: 0.75),
                          height: 1.4,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                    if (item.relayFromPartner != null) ...[
                      const SizedBox(height: 6),
                      Row(
                        children: [
                          Icon(
                            Icons.mail_outline,
                            size: 14,
                            color: AppColors.calmTeal.withValues(alpha: 0.8),
                          ),
                          const SizedBox(width: 4),
                          Text(
                            'From ${item.relayFromPartner}',
                            style: const TextStyle(
                              fontSize: 12,
                              color: AppColors.calmTeal,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Icon(
                Icons.chevron_right_rounded,
                color: AppColors.softCharcoal.withValues(alpha: 0.3),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _typeColor(SessionType type) {
    switch (type) {
      case SessionType.individual:
        return AppColors.warmCoral;
      case SessionType.joint:
        return AppColors.calmTeal;
      case SessionType.relay:
        return const Color(0xFF8B5CF6); // purple
      case SessionType.unknown:
        return AppColors.softCharcoal;
    }
  }

  IconData _typeIcon(SessionType type) {
    switch (type) {
      case SessionType.individual:
        return Icons.person_outline_rounded;
      case SessionType.joint:
        return Icons.people_outline_rounded;
      case SessionType.relay:
        return Icons.mail_outline_rounded;
      case SessionType.unknown:
        return Icons.chat_bubble_outline_rounded;
    }
  }

  String _formatDate(DateTime dt) {
    final now = DateTime.now();
    final diff = now.difference(dt);
    if (diff.inDays == 0) return 'Today, ${_timeStr(dt)}';
    if (diff.inDays == 1) return 'Yesterday, ${_timeStr(dt)}';
    if (diff.inDays < 7) return '${diff.inDays} days ago';
    return '${dt.day}/${dt.month}/${dt.year}';
  }

  String _timeStr(DateTime dt) {
    final h = dt.hour > 12 ? dt.hour - 12 : dt.hour == 0 ? 12 : dt.hour;
    final m = dt.minute.toString().padLeft(2, '0');
    final period = dt.hour >= 12 ? 'PM' : 'AM';
    return '$h:$m $period';
  }
}
