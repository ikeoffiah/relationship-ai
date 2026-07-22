import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/relationship/relationship_viewmodel.dart';
import 'package:mobile/shared/widgets/animated_button.dart';

class OurStoryScreen extends StatefulWidget {
  const OurStoryScreen({super.key});

  @override
  State<OurStoryScreen> createState() => _OurStoryScreenState();
}

class _OurStoryScreenState extends State<OurStoryScreen> {
  final _goalController = TextEditingController();
  final _repairController = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      final vm = context.read<RelationshipViewModel>();
      // Shared context is keyed on the current relationship, which is only
      // loaded by the Home tab. Load it here too so this screen works when
      // reached directly from Settings.
      if (vm.currentRelationship == null) {
        await vm.fetchRelationshipStatus();
      }
      await vm.fetchSharedContext();
    });
  }

  @override
  void dispose() {
    _goalController.dispose();
    _repairController.dispose();
    super.dispose();
  }

  void _addGoal(RelationshipViewModel vm) {
    if (_goalController.text.trim().isNotEmpty) {
      vm.addGoal(_goalController.text.trim());
      _goalController.clear();
      Navigator.pop(context);
    }
  }

  void _addRepair(RelationshipViewModel vm) {
    if (_repairController.text.trim().isNotEmpty) {
      vm.addRepairEvent(_repairController.text.trim(), "manual_entry");
      _repairController.clear();
      Navigator.pop(context);
    }
  }

  void _showAddDialog(BuildContext context, RelationshipViewModel vm, String type) {
    final isGoal = type == 'goal';
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text(isGoal ? 'Add Shared Goal' : 'Log Repair Moment'),
          content: TextField(
            controller: isGoal ? _goalController : _repairController,
            decoration: InputDecoration(
              hintText: isGoal ? 'e.g. Save for a house' : 'e.g. We communicated well today',
            ),
            maxLines: 3,
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
            AnimatedButton(
              label: 'Save',
              onTap: () => isGoal ? _addGoal(vm) : _addRepair(vm),
              isFilled: true,
              height: 40,
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<RelationshipViewModel>();
    final sharedContext = vm.sharedContext;

    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Our Story', style: TextStyle(color: AppColors.softCharcoal)),
        backgroundColor: Colors.transparent,
        elevation: 0,
        iconTheme: const IconThemeData(color: AppColors.softCharcoal),
      ),
      body: _buildBody(context, vm, sharedContext),
    );
  }

  Widget _buildBody(
    BuildContext context,
    RelationshipViewModel vm,
    Map<String, dynamic>? sharedContext,
  ) {
    // A shared story only exists once both partners are connected. Without an
    // active relationship, guide the user to connect rather than spinning
    // forever (fetchSharedContext no-ops when there is no relationship).
    if (vm.status != RelationshipStatus.loading &&
        vm.status != RelationshipStatus.active) {
      return _buildNoRelationship(context);
    }

    if (sharedContext == null) {
      return const Center(child: CircularProgressIndicator());
    }

    return RefreshIndicator(
              onRefresh: vm.fetchSharedContext,
              child: ListView(
                padding: const EdgeInsets.all(16.0),
                children: [
                  _buildSectionCard(
                    title: 'Relationship Overview',
                    icon: Icons.info_outline,
                    children: [
                      _buildFactRow('Duration', '${sharedContext['structural_facts']?['relationship_duration_months'] ?? 'Not set'} months'),
                      _buildFactRow('Cohabiting', sharedContext['structural_facts']?['cohabiting'] == true ? 'Yes' : 'No'),
                      _buildFactRow('Children', '${sharedContext['structural_facts']?['children'] ?? '0'}'),
                    ],
                  ),
                  const SizedBox(height: 16),
                  _buildSectionCard(
                    title: 'Named Conflicts',
                    icon: Icons.warning_amber_rounded,
                    children: _buildConflicts(sharedContext['named_recurring_conflicts'] as List?),
                  ),
                  const SizedBox(height: 16),
                  _buildSectionCard(
                    title: 'Shared Goals',
                    icon: Icons.flag_outlined,
                    actionIcon: Icons.add,
                    onAction: () => _showAddDialog(context, vm, 'goal'),
                    children: _buildList(sharedContext['agreed_goals_and_values'] as List?, 'description'),
                  ),
                  const SizedBox(height: 16),
                  _buildSectionCard(
                    title: 'Repair Moments',
                    icon: Icons.favorite_border,
                    actionIcon: Icons.add,
                    onAction: () => _showAddDialog(context, vm, 'repair'),
                    children: _buildList(sharedContext['repair_history'] as List?, 'description'),
                  ),
                ],
              ),
            );
  }

  Widget _buildNoRelationship(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.auto_stories_outlined,
                size: 56, color: AppColors.warmCoral),
            const SizedBox(height: 16),
            const Text(
              'Your shared story starts together',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: AppColors.softCharcoal,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Connect with your partner to build shared goals and a record '
              'of your repair moments.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: AppColors.softCharcoal.withValues(alpha: 0.6),
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () =>
                  Navigator.pushNamed(context, '/relationship/invite'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.warmCoral,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12)),
              ),
              child: const Text('Connect with partner',
                  style: TextStyle(color: Colors.white)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionCard({
    required String title,
    required IconData icon,
    List<Widget>? children,
    IconData? actionIcon,
    VoidCallback? onAction,
  }) {
    return Container(
      padding: const EdgeInsets.all(20),
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
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Icon(icon, color: AppColors.calmTeal, size: 24),
                  const SizedBox(width: 8),
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: AppColors.softCharcoal,
                    ),
                  ),
                ],
              ),
              if (actionIcon != null && onAction != null)
                IconButton(
                  icon: Icon(actionIcon, color: AppColors.calmTeal),
                  onPressed: onAction,
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                )
            ],
          ),
          const SizedBox(height: 16),
          if (children != null && children.isNotEmpty) ...children else const Text('No data recorded yet.', style: TextStyle(color: Colors.grey)),
        ],
      ),
    );
  }

  Widget _buildFactRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: AppColors.softCharcoal, fontSize: 16)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.softCharcoal, fontSize: 16)),
        ],
      ),
    );
  }

  List<Widget> _buildList(List<dynamic>? items, String key) {
    if (items == null || items.isEmpty) return [];
    return items.map((item) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 12.0),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Padding(
              padding: EdgeInsets.only(top: 6.0, right: 8.0),
              child: Icon(Icons.circle, size: 6, color: AppColors.calmTeal),
            ),
            Expanded(
              child: Text(
                item[key] ?? '',
                style: const TextStyle(color: AppColors.softCharcoal, fontSize: 15, height: 1.4),
              ),
            ),
          ],
        ),
      );
    }).toList();
  }

  List<Widget> _buildConflicts(List<dynamic>? items) {
    if (items == null || items.isEmpty) return [];
    // Only show if acknowledged_by_both is true
    final validItems = items.where((i) => i['acknowledged_by_both'] == true).toList();
    if (validItems.isEmpty) return [const Text('No acknowledged conflicts.', style: TextStyle(color: Colors.grey))];

    return validItems.map((item) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              item['label'] ?? 'Unknown Conflict',
              style: const TextStyle(fontWeight: FontWeight.bold, color: AppColors.softCharcoal, fontSize: 15),
            ),
            const SizedBox(height: 4),
            Text(
              item['description'] ?? '',
              style: const TextStyle(color: AppColors.softCharcoal, fontSize: 14, height: 1.4),
            ),
          ],
        ),
      );
    }).toList();
  }
}
