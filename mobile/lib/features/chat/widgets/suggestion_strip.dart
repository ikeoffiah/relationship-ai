import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';

/// A horizontal strip of tappable auto-suggestions shown just above the message
/// input. Tapping one hands the text back to the composer. Renders nothing when
/// there are no suggestions.
class SuggestionStrip extends StatelessWidget {
  final List<String> suggestions;
  final bool loading;
  final ValueChanged<String> onTap;
  final VoidCallback? onDismiss;

  const SuggestionStrip({
    super.key,
    required this.suggestions,
    required this.onTap,
    this.loading = false,
    this.onDismiss,
  });

  @override
  Widget build(BuildContext context) {
    if (suggestions.isEmpty) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
      color: AppColors.creamWhite,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.auto_awesome, size: 13, color: AppColors.calmTeal),
              const SizedBox(width: 4),
              Text('Suggestions',
                  style: TextStyle(
                      fontSize: 11,
                      color: AppColors.softCharcoal.withValues(alpha: 0.6))),
              const Spacer(),
              if (onDismiss != null)
                GestureDetector(
                  onTap: onDismiss,
                  child: Icon(Icons.close,
                      size: 14, color: AppColors.softCharcoal.withValues(alpha: 0.5)),
                ),
            ],
          ),
          const SizedBox(height: 6),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                for (final s in suggestions)
                  Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: ActionChip(
                      label: Text(s, style: const TextStyle(fontSize: 13)),
                      backgroundColor: Colors.white,
                      side: const BorderSide(color: AppColors.rosePeach),
                      onPressed: () => onTap(s),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
