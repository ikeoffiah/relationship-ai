import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/app_card.dart';
import '../engagement_models.dart';
import '../engagement_viewmodel.dart';

/// Shared goals a couple works on together (fitness, savings, habits). Logging
/// progress is a daily reason to return and awards points toward the streak.
class SharedGoalsScreen extends StatefulWidget {
  const SharedGoalsScreen({super.key});

  @override
  State<SharedGoalsScreen> createState() => _SharedGoalsScreenState();
}

class _SharedGoalsScreenState extends State<SharedGoalsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback(
      (_) => context.read<EngagementViewModel>().loadGoals(),
    );
  }

  static const _categoryEmoji = {
    'relationship': '💞',
    'health': '💪',
    'financial': '💰',
    'learning': '📚',
    'home': '🏡',
    'adventure': '✈️',
    'custom': '🎯',
  };

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<EngagementViewModel>();
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Shared goals', style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: AppColors.creamWhite,
        elevation: 0,
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: AppColors.warmCoral,
        onPressed: () => _openCreateSheet(context),
        icon: const Icon(Icons.add, color: Colors.white),
        label: const Text('New goal', style: TextStyle(color: Colors.white)),
      ),
      body: vm.isLoading && vm.goals.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : vm.goals.isEmpty
              ? _empty()
              : RefreshIndicator(
                  onRefresh: () => vm.loadGoals(),
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      for (final g in vm.goals) ...[
                        _GoalCard(goal: g, emoji: _categoryEmoji[g.category] ?? '🎯'),
                        const SizedBox(height: 12),
                      ],
                    ],
                  ),
                ),
    );
  }

  Widget _empty() => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('🎯', style: TextStyle(fontSize: 48)),
              const SizedBox(height: 16),
              const Text('No shared goals yet',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              Text(
                'Set something to work on together — a savings target, a fitness habit, a trip. Log progress daily to keep your streak alive.',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppColors.softCharcoal.withValues(alpha: 0.7)),
              ),
            ],
          ),
        ),
      );

  void _openCreateSheet(BuildContext context) {
    final titleCtrl = TextEditingController();
    final targetCtrl = TextEditingController();
    final unitCtrl = TextEditingController();
    String category = 'health';
    final vm = context.read<EngagementViewModel>();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.creamWhite,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (sheetCtx) => StatefulBuilder(
        builder: (sheetCtx, setSheet) => Padding(
          padding: EdgeInsets.only(
            left: 20,
            right: 20,
            top: 20,
            bottom: MediaQuery.of(sheetCtx).viewInsets.bottom + 20,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('New shared goal',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 16),
              TextField(
                controller: titleCtrl,
                decoration: _dec('Goal title (e.g. Save for Japan)'),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                children: [
                  for (final c in _categoryEmoji.entries)
                    ChoiceChip(
                      label: Text('${c.value} ${c.key}'),
                      selected: category == c.key,
                      onSelected: (_) => setSheet(() => category = c.key),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              Row(children: [
                Expanded(
                  child: TextField(
                    controller: targetCtrl,
                    keyboardType: TextInputType.number,
                    decoration: _dec('Target (optional)'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextField(
                    controller: unitCtrl,
                    decoration: _dec('Unit (mi, \$…)'),
                  ),
                ),
              ]),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.warmCoral,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  onPressed: () async {
                    final title = titleCtrl.text.trim();
                    if (title.isEmpty) return;
                    final ok = await vm.createGoal(
                      title: title,
                      category: category,
                      targetValue: double.tryParse(targetCtrl.text.trim()),
                      unit: unitCtrl.text.trim(),
                    );
                    if (sheetCtx.mounted && ok) Navigator.of(sheetCtx).pop();
                  },
                  child: const Text('Create goal', style: TextStyle(color: Colors.white)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  InputDecoration _dec(String hint) => InputDecoration(
        hintText: hint,
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
      );
}

class _GoalCard extends StatelessWidget {
  final SharedGoal goal;
  final String emoji;
  const _GoalCard({required this.goal, required this.emoji});

  @override
  Widget build(BuildContext context) {
    final isDone = goal.status == 'completed';
    return AppCard(
      child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Text(emoji, style: const TextStyle(fontSize: 22)),
              const SizedBox(width: 8),
              Expanded(
                child: Text(goal.title,
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              ),
              if (isDone)
                const Icon(Icons.check_circle, color: AppColors.calmTeal),
            ]),
            if (goal.targetValue != null) ...[
              const SizedBox(height: 12),
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: LinearProgressIndicator(
                  value: goal.progressFraction,
                  minHeight: 8,
                  backgroundColor: AppColors.softCharcoal.withValues(alpha: 0.08),
                  valueColor: const AlwaysStoppedAnimation(AppColors.calmTeal),
                ),
              ),
              const SizedBox(height: 6),
              Text(
                '${_fmt(goal.currentValue)} / ${_fmt(goal.targetValue!)} ${goal.unit}',
                style: TextStyle(color: AppColors.softCharcoal.withValues(alpha: 0.7), fontSize: 12),
              ),
            ],
            if (!isDone) ...[
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                  onPressed: () => _logProgress(context),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: AppColors.calmTeal),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  child: const Text('Log progress', style: TextStyle(color: AppColors.softCharcoal)),
                ),
              ),
            ],
          ],
      ),
    );
  }

  String _fmt(double v) => v == v.roundToDouble() ? v.toInt().toString() : v.toStringAsFixed(1);

  void _logProgress(BuildContext context) {
    final ctrl = TextEditingController(text: goal.targetValue == null ? '1' : '');
    final vm = context.read<EngagementViewModel>();
    showDialog(
      context: context,
      builder: (dialogCtx) => AlertDialog(
        backgroundColor: AppColors.creamWhite,
        title: Text('Log progress · ${goal.title}'),
        content: TextField(
          controller: ctrl,
          keyboardType: TextInputType.number,
          autofocus: true,
          decoration: InputDecoration(
            hintText: goal.targetValue == null ? 'Count (e.g. 1)' : 'Amount to add ${goal.unit}',
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(dialogCtx).pop(), child: const Text('Cancel')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.calmTeal),
            onPressed: () async {
              final value = double.tryParse(ctrl.text.trim()) ?? 0;
              if (value <= 0) return;
              final ok = await vm.logGoalProgress(goalId: goal.id, value: value);
              if (dialogCtx.mounted && ok) Navigator.of(dialogCtx).pop();
            },
            child: const Text('Add', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }
}
