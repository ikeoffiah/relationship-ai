import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/history/models/session_history_model.dart';
import 'package:mobile/features/history/viewmodels/session_detail_viewmodel.dart';
import 'package:mobile/shared/widgets/get_help_now_button.dart';

class SessionDetailScreen extends StatefulWidget {
  final String sessionId;

  const SessionDetailScreen({super.key, required this.sessionId});

  @override
  State<SessionDetailScreen> createState() => _SessionDetailScreenState();
}

class _SessionDetailScreenState extends State<SessionDetailScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<SessionDetailViewModel>().loadDetail(widget.sessionId);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<SessionDetailViewModel>(
      builder: (context, vm, _) {
        return Scaffold(
          backgroundColor: AppColors.creamWhite,
          appBar: AppBar(
            title: const Text('Session details'),
            backgroundColor: Colors.transparent,
            elevation: 0,
            leading: const BackButton(),
          ),
          body: Column(
            children: [
              const GetHelpNowButton(),
              Expanded(child: _buildBody(vm)),
            ],
          ),
        );
      },
    );
  }

  Widget _buildBody(SessionDetailViewModel vm) {
    if (vm.isLoading) {
      return const Center(
        child: CircularProgressIndicator(color: AppColors.warmCoral),
      );
    }

    if (vm.error != null && vm.detail == null) {
      return _buildErrorState(vm);
    }

    final detail = vm.detail;
    if (detail == null) return const SizedBox.shrink();

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
      children: [
        _buildHeaderCard(detail),
        const SizedBox(height: 20),
        _buildSummarySection(detail),
        const SizedBox(height: 20),
        if (detail.frameworks.isNotEmpty) ...[
          _buildFrameworkTags(detail.frameworks),
          const SizedBox(height: 20),
        ],
        _buildMemoriesSection(vm),
        if (vm.memories.isNotEmpty) ...[
          const SizedBox(height: 24),
          _buildBulkDeleteButton(vm),
        ],
        if (vm.error != null)
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: Text(
              vm.error!,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.red, fontSize: 13),
            ),
          ),
      ],
    );
  }

  // ─────────────────────── Header Card ────────────────────────
  Widget _buildHeaderCard(SessionDetail detail) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            _typeColor(detail.type).withValues(alpha: 0.15),
            _typeColor(detail.type).withValues(alpha: 0.05),
          ],
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: _typeColor(detail.type).withValues(alpha: 0.2),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(_typeIcon(detail.type), color: _typeColor(detail.type), size: 26),
              const SizedBox(width: 10),
              Text(
                '${detail.type.label} session',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: _typeColor(detail.type),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            _formatFullDate(detail.dateTime),
            style: TextStyle(
              fontSize: 15,
              color: AppColors.softCharcoal.withValues(alpha: 0.7),
            ),
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              _metaBadge('${detail.turnCount} turns', Icons.swap_horiz_rounded),
              const SizedBox(width: 10),
              if (detail.durationMinutes > 0)
                _metaBadge(
                  '${detail.durationMinutes} min',
                  Icons.timer_outlined,
                ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _metaBadge(String label, IconData icon) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: AppColors.softCharcoal.withValues(alpha: 0.5)),
          const SizedBox(width: 5),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              color: AppColors.softCharcoal.withValues(alpha: 0.7),
            ),
          ),
        ],
      ),
    );
  }

  // ──────────────────────── Summary ───────────────────────────
  Widget _buildSummarySection(SessionDetail detail) {
    return _sectionCard(
      icon: Icons.auto_awesome_rounded,
      iconColor: AppColors.warmCoral,
      title: 'AI Summary',
      child: Text(
        detail.summary.isEmpty
            ? 'No summary available for this session.'
            : detail.summary,
        style: TextStyle(
          fontSize: 15,
          height: 1.6,
          color: AppColors.softCharcoal.withValues(alpha: 0.8),
          fontStyle: detail.summary.isEmpty ? FontStyle.italic : FontStyle.normal,
        ),
      ),
    );
  }

  // ──────────────────────── Framework Tags ────────────────────
  Widget _buildFrameworkTags(List<String> frameworks) {
    return _sectionCard(
      icon: Icons.label_outline_rounded,
      iconColor: AppColors.calmTeal,
      title: 'Frameworks used',
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: frameworks
            .map(
              (f) => Chip(
                label: Text(f, style: const TextStyle(fontSize: 12)),
                backgroundColor: AppColors.calmTeal.withValues(alpha: 0.12),
                side: BorderSide(color: AppColors.calmTeal.withValues(alpha: 0.25)),
                visualDensity: VisualDensity.compact,
              ),
            )
            .toList(),
      ),
    );
  }

  // ──────────────────────── Memories ──────────────────────────
  Widget _buildMemoriesSection(SessionDetailViewModel vm) {
    return _sectionCard(
      icon: Icons.psychology_outlined,
      iconColor: const Color(0xFF8B5CF6),
      title: 'Memories stored from this session',
      child: vm.memories.isEmpty
          ? Text(
              'No memories were stored from this session.',
              style: TextStyle(
                fontSize: 14,
                fontStyle: FontStyle.italic,
                color: AppColors.softCharcoal.withValues(alpha: 0.55),
              ),
            )
          : Column(
              children: vm.memories.map((m) => _MemoryItem(memory: m)).toList(),
            ),
    );
  }

  // ─────────────────── Bulk Delete Button ─────────────────────
  Widget _buildBulkDeleteButton(SessionDetailViewModel vm) {
    return Center(
      child: TextButton.icon(
        onPressed: vm.isDeletingAll ? null : () => _confirmBulkDelete(vm),
        icon: vm.isDeletingAll
            ? const SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : const Icon(Icons.delete_sweep_outlined, color: Colors.red),
        label: Text(
          'Delete this session\'s memories',
          style: TextStyle(
            color: vm.isDeletingAll ? Colors.grey : Colors.red,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }

  void _confirmBulkDelete(SessionDetailViewModel vm) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text('Delete session memories?'),
        content: const Text(
          'All memories from this session will be permanently deleted. '
          'This cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () async {
              Navigator.pop(ctx);
              final ok = await vm.deleteAllSessionMemories();
              if (mounted && ok) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('All session memories deleted.'),
                  ),
                );
              }
            },
            child: const Text(
              'Delete',
              style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ),
    );
  }

  // ─────────────────────── Error State ────────────────────────
  Widget _buildErrorState(SessionDetailViewModel vm) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.cloud_off_rounded,
                size: 64, color: AppColors.warmCoral),
            const SizedBox(height: 20),
            Text(
              vm.error!,
              textAlign: TextAlign.center,
              style:
                  TextStyle(color: AppColors.softCharcoal.withValues(alpha: 0.7)),
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: () => vm.loadDetail(widget.sessionId),
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.warmCoral,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ─────────────────── Helper / Section Card ───────────────────
  Widget _sectionCard({
    required IconData icon,
    required Color iconColor,
    required String title,
    required Widget child,
  }) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.04),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: iconColor, size: 20),
              const SizedBox(width: 8),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                  color: AppColors.softCharcoal,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          const Divider(),
          const SizedBox(height: 8),
          child,
        ],
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
        return const Color(0xFF8B5CF6);
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

  String _formatFullDate(DateTime dt) {
    const months = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December',
    ];
    final h = dt.hour > 12 ? dt.hour - 12 : (dt.hour == 0 ? 12 : dt.hour);
    final m = dt.minute.toString().padLeft(2, '0');
    final period = dt.hour >= 12 ? 'PM' : 'AM';
    return '${months[dt.month - 1]} ${dt.day}, ${dt.year} · $h:$m $period';
  }
}

// ─────────────────── Memory Item (inline edit/delete) ─────────────────────

class _MemoryItem extends StatefulWidget {
  final SessionMemory memory;
  const _MemoryItem({required this.memory});

  @override
  State<_MemoryItem> createState() => _MemoryItemState();
}

class _MemoryItemState extends State<_MemoryItem> {
  late TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.memory.content);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.read<SessionDetailViewModel>();
    final memory = widget.memory;

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (memory.isEditing)
            TextField(
              controller: _controller,
              maxLines: null,
              autofocus: true,
              decoration: InputDecoration(
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 10,
                ),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide:
                      BorderSide(color: AppColors.warmCoral.withValues(alpha: 0.5)),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: AppColors.warmCoral),
                ),
              ),
            )
          else
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('• ',
                    style: TextStyle(
                        color: AppColors.warmCoral, fontWeight: FontWeight.bold)),
                Expanded(
                  child: Text(
                    memory.content,
                    style: const TextStyle(
                      fontSize: 14,
                      color: AppColors.softCharcoal,
                      height: 1.5,
                    ),
                  ),
                ),
              ],
            ),
          const SizedBox(height: 6),
          Row(
            children: [
              if (memory.isEditing) ...[
                _actionButton(
                  label: 'Save',
                  color: AppColors.calmTeal,
                  onTap: () => vm.saveMemory(memory.id, _controller.text.trim()),
                ),
                const SizedBox(width: 8),
                _actionButton(
                  label: 'Cancel',
                  color: Colors.grey,
                  onTap: () {
                    _controller.text = memory.content;
                    vm.toggleEditMode(memory.id);
                  },
                ),
              ] else ...[
                _actionButton(
                  label: 'Edit',
                  color: AppColors.calmTeal,
                  onTap: () {
                    _controller.text = memory.content;
                    vm.toggleEditMode(memory.id);
                  },
                ),
                const SizedBox(width: 8),
                _actionButton(
                  label: 'Delete',
                  color: Colors.red,
                  onTap: () => _confirmDelete(context, vm, memory),
                ),
              ],
            ],
          ),
          const Divider(height: 20),
        ],
      ),
    );
  }

  Widget _actionButton({
    required String label,
    required Color color,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: color.withValues(alpha: 0.3)),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: color,
          ),
        ),
      ),
    );
  }

  void _confirmDelete(
    BuildContext context,
    SessionDetailViewModel vm,
    SessionMemory memory,
  ) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text('Delete this memory?'),
        content: Text(
          '"${memory.content}"\n\nThis cannot be undone.',
          style: const TextStyle(fontSize: 14),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              vm.deleteMemory(memory.id);
            },
            child: const Text(
              'Delete',
              style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ),
    );
  }
}
