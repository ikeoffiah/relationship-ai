import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../bliss_format.dart';
import '../bliss_models.dart';

/// A bottom sheet confirming a parsed @bliss draft before it is saved. The user
/// can tweak the title and confirm, or dismiss. Returns the (possibly edited)
/// draft on confirm, or null.
class BlissConfirmSheet extends StatefulWidget {
  final BlissDraft draft;
  const BlissConfirmSheet({super.key, required this.draft});

  static Future<BlissDraft?> open(BuildContext context, BlissDraft draft) {
    return showModalBottomSheet<BlissDraft>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
        child: BlissConfirmSheet(draft: draft),
      ),
    );
  }

  @override
  State<BlissConfirmSheet> createState() => _BlissConfirmSheetState();
}

class _BlissConfirmSheetState extends State<BlissConfirmSheet> {
  late final TextEditingController _title =
      TextEditingController(text: widget.draft.title);

  @override
  void dispose() {
    _title.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.draft;
    final isEvent = d.kind == 'event';
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
            Row(
              children: [
                const Text('🌸  ', style: TextStyle(fontSize: 18)),
                Text(
                  isEvent ? 'Add to your plan' : 'Set a reminder',
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _title,
              maxLength: 200,
              decoration: InputDecoration(
                labelText: 'What',
                counterText: '',
                filled: true,
                fillColor: Colors.white,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Icon(isEvent ? Icons.event : Icons.alarm,
                    size: 18, color: AppColors.calmTeal),
                const SizedBox(width: 8),
                Text(formatDue(d.dueAt, hasTime: d.hasTime),
                    style: const TextStyle(fontSize: 14)),
              ],
            ),
            const SizedBox(height: 20),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Not now'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: FilledButton(
                    style: FilledButton.styleFrom(backgroundColor: AppColors.warmCoral),
                    onPressed: () {
                      final title = _title.text.trim();
                      if (title.isEmpty) return;
                      Navigator.of(context).pop(widget.draft.copyWith(title: title));
                    },
                    child: Text(isEvent ? 'Add it' : 'Remind us'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
