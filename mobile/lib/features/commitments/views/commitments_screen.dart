import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/theme/app_colors.dart';
import '../commitment_models.dart';
import '../commitment_viewmodel.dart';

/// Partner commitments: little promises you make *for* your partner and ones you
/// make *with* each other, each with an optional reminder.
class CommitmentsScreen extends StatefulWidget {
  const CommitmentsScreen({super.key});

  @override
  State<CommitmentsScreen> createState() => _CommitmentsScreenState();
}

class _CommitmentsScreenState extends State<CommitmentsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance
        .addPostFrameCallback((_) => context.read<CommitmentViewModel>().load());
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<CommitmentViewModel>();
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Commitments', style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: AppColors.creamWhite,
        elevation: 0,
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: AppColors.warmCoral,
        onPressed: () => _AddCommitmentSheet.open(context),
        icon: const Icon(Icons.add, color: Colors.white),
        label: const Text('Add', style: TextStyle(color: Colors.white)),
      ),
      body: vm.isLoading && vm.items.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: () => vm.load(),
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 90),
                children: [
                  if (vm.items.isEmpty) _empty(),
                  if (vm.forPartner.isNotEmpty) ...[
                    _sectionHeader('💝  For your partner', 'Little things you want to do for them'),
                    for (final c in vm.forPartner) _CommitmentTile(item: c),
                    const SizedBox(height: 16),
                  ],
                  if (vm.withPartner.isNotEmpty) ...[
                    _sectionHeader('💞  Together', 'Things you want to do with each other'),
                    for (final c in vm.withPartner) _CommitmentTile(item: c),
                  ],
                ],
              ),
            ),
    );
  }

  Widget _sectionHeader(String title, String subtitle) => Padding(
        padding: const EdgeInsets.only(bottom: 8, top: 4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            Text(subtitle,
                style: TextStyle(
                    fontSize: 12, color: AppColors.softCharcoal.withValues(alpha: 0.6))),
          ],
        ),
      );

  Widget _empty() => Padding(
        padding: const EdgeInsets.only(top: 100),
        child: Column(
          children: [
            const Text('💞', style: TextStyle(fontSize: 44)),
            const SizedBox(height: 12),
            const Center(
              child: Text('No commitments yet',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            ),
            const SizedBox(height: 6),
            Center(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 40),
                child: Text(
                  'Add a little promise for your partner, or one you want to keep together.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: AppColors.softCharcoal.withValues(alpha: 0.6)),
                ),
              ),
            ),
          ],
        ),
      );
}

class _CommitmentTile extends StatelessWidget {
  final Commitment item;
  const _CommitmentTile({required this.item});

  String? _reminderLabel() {
    final r = item.remindAt?.toLocal();
    if (r == null) return null;
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    final h = r.hour % 12 == 0 ? 12 : r.hour % 12;
    final ampm = r.hour < 12 ? 'am' : 'pm';
    return '${months[r.month - 1]} ${r.day}, $h:${r.minute.toString().padLeft(2, '0')}$ampm';
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.read<CommitmentViewModel>();
    final reminder = _reminderLabel();
    return Card(
      elevation: 0,
      color: Colors.white,
      margin: const EdgeInsets.only(bottom: 10),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      child: ListTile(
        title: Text(item.text),
        subtitle: reminder == null
            ? null
            : Row(children: [
                const Icon(Icons.alarm, size: 14, color: AppColors.calmTeal),
                const SizedBox(width: 4),
                Text(reminder, style: const TextStyle(fontSize: 12)),
              ]),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(
              tooltip: 'Done',
              icon: const Icon(Icons.check_circle_outline, color: AppColors.calmTeal),
              onPressed: () => vm.markDone(item.id),
            ),
            IconButton(
              tooltip: 'Remove',
              icon: Icon(Icons.close, color: AppColors.softCharcoal.withValues(alpha: 0.5)),
              onPressed: () => vm.cancel(item.id),
            ),
          ],
        ),
      ),
    );
  }
}

class _AddCommitmentSheet extends StatefulWidget {
  const _AddCommitmentSheet();

  static Future<void> open(BuildContext context) {
    final vm = context.read<CommitmentViewModel>();
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => ChangeNotifierProvider.value(
        value: vm,
        child: Padding(
          padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
          child: const _AddCommitmentSheet(),
        ),
      ),
    );
  }

  @override
  State<_AddCommitmentSheet> createState() => _AddCommitmentSheetState();
}

class _AddCommitmentSheetState extends State<_AddCommitmentSheet> {
  final _text = TextEditingController();
  String _kind = 'for_partner';
  DateTime? _remindAt;

  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  Future<void> _pickReminder() async {
    final now = DateTime.now();
    final date = await showDatePicker(
      context: context,
      firstDate: now,
      lastDate: now.add(const Duration(days: 365)),
      initialDate: now,
    );
    if (date == null || !mounted) return;
    final time = await showTimePicker(context: context, initialTime: TimeOfDay.now());
    if (time == null) return;
    setState(() => _remindAt =
        DateTime(date.year, date.month, date.day, time.hour, time.minute));
  }

  Future<void> _submit() async {
    final text = _text.text.trim();
    if (text.isEmpty) return;
    final vm = context.read<CommitmentViewModel>();
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    final ok = await vm.add(kind: _kind, text: text, remindAt: _remindAt);
    if (!mounted) return;
    if (ok) {
      navigator.pop();
      messenger.showSnackBar(const SnackBar(content: Text('Commitment added 💞')));
    } else {
      messenger.showSnackBar(SnackBar(content: Text(vm.error ?? "Couldn't save, try again.")));
    }
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<CommitmentViewModel>();
    return SafeArea(
      child: Container(
        margin: const EdgeInsets.all(12),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: AppColors.creamWhite,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('New commitment',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'for_partner', label: Text('For them'), icon: Icon(Icons.card_giftcard)),
                ButtonSegment(value: 'with_partner', label: Text('Together'), icon: Icon(Icons.favorite)),
              ],
              selected: {_kind},
              onSelectionChanged: (s) => setState(() => _kind = s.first),
            ),
            const SizedBox(height: 6),
            Text(
              _kind == 'for_partner'
                  ? 'A private promise — your partner won\'t see it (keep it a surprise).'
                  : 'Shared — your partner will see this and be reminded too.',
              style: TextStyle(fontSize: 12, color: AppColors.softCharcoal.withValues(alpha: 0.7)),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: _text,
              maxLength: 280,
              onChanged: (_) => setState(() {}),
              decoration: InputDecoration(
                hintText: _kind == 'for_partner'
                    ? 'e.g. Bring you coffee in bed'
                    : 'e.g. Cook dinner together Friday',
                counterText: '',
                filled: true,
                fillColor: Colors.white,
                border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                const Icon(Icons.alarm, size: 18, color: AppColors.calmTeal),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    _remindAt == null
                        ? 'No reminder'
                        : 'Reminder set for ${_remindAt!.toLocal()}'.split('.').first,
                    style: const TextStyle(fontSize: 13),
                  ),
                ),
                TextButton(
                  onPressed: _pickReminder,
                  child: Text(_remindAt == null ? 'Add reminder' : 'Change'),
                ),
                if (_remindAt != null)
                  IconButton(
                    icon: const Icon(Icons.close, size: 18),
                    onPressed: () => setState(() => _remindAt = null),
                  ),
              ],
            ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                style: FilledButton.styleFrom(
                  backgroundColor: AppColors.warmCoral,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
                onPressed: (_text.text.trim().isEmpty || vm.submitting) ? null : _submit,
                child: vm.submitting
                    ? const SizedBox(
                        height: 18, width: 18,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Text('Add commitment'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
