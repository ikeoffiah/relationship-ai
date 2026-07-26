import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/theme/app_colors.dart';
import '../bliss_format.dart';
import '../bliss_models.dart';
import '../bliss_viewmodel.dart';

/// The couple's shared plan: pending @bliss reminders and events, with
/// swipe-free done/cancel actions.
class BlissPlanScreen extends StatefulWidget {
  const BlissPlanScreen({super.key});

  @override
  State<BlissPlanScreen> createState() => _BlissPlanScreenState();
}

class _BlissPlanScreenState extends State<BlissPlanScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback(
      (_) => context.read<BlissViewModel>().load(),
    );
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<BlissViewModel>();
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Your plan', style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: AppColors.creamWhite,
        elevation: 0,
      ),
      body: RefreshIndicator(
        onRefresh: () => vm.load(),
        child: vm.isLoading && vm.items.isEmpty
            ? const Center(child: CircularProgressIndicator())
            : vm.items.isEmpty
                ? _empty()
                : ListView(
                    padding: const EdgeInsets.all(12),
                    children: [
                      for (final item in vm.items) _BlissTile(item: item),
                    ],
                  ),
      ),
    );
  }

  Widget _empty() => ListView(
        children: [
          const SizedBox(height: 120),
          Icon(Icons.event_note_outlined,
              size: 56, color: AppColors.rosePeach),
          const SizedBox(height: 12),
          const Center(
            child: Text('Nothing planned yet',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
          ),
          const SizedBox(height: 6),
          Center(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 40),
              child: Text(
                'In chat, tag @bliss — e.g. “@bliss remind us to call the venue tomorrow at 5pm”.',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppColors.softCharcoal.withValues(alpha: 0.6)),
              ),
            ),
          ),
        ],
      );
}

class _BlissTile extends StatelessWidget {
  final BlissItem item;
  const _BlissTile({required this.item});

  @override
  Widget build(BuildContext context) {
    final vm = context.read<BlissViewModel>();
    return Card(
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      child: ListTile(
        leading: Text(item.isEvent ? '🗓️' : '⏰', style: const TextStyle(fontSize: 22)),
        title: Text(item.title, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(formatDue(item.dueAt, hasTime: true)),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(
              icon: const Icon(Icons.check_circle_outline, color: AppColors.calmTeal),
              tooltip: 'Done',
              onPressed: () => vm.markDone(item.id),
            ),
            IconButton(
              icon: Icon(Icons.close, color: AppColors.softCharcoal.withValues(alpha: 0.5)),
              tooltip: 'Cancel',
              onPressed: () => vm.cancel(item.id),
            ),
          ],
        ),
      ),
    );
  }
}
