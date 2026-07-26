import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../tone/tone_models.dart';
import '../tone/tone_viewmodel.dart';

/// A bottom sheet that coaches the user's current draft: shows how it may land,
/// offers kinder rewrites (tap one to use it), or — if the draft carries harm
/// signals — declines and shows a support message instead.
///
/// Returns the chosen rewrite via [Navigator.pop], or null if the user dismisses
/// without picking one.
class ToneCoachSheet extends StatelessWidget {
  final CoachResult result;

  const ToneCoachSheet({super.key, required this.result});

  /// Runs the coach call (showing a loading sheet) and then the result sheet.
  /// Returns the chosen rewrite, or null.
  static Future<String?> open(
    BuildContext context,
    ToneViewModel vm,
    String draft, {
    String? partnerMood,
  }) async {
    final result = await showModalBottomSheet<CoachResult?>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => FutureBuilder<CoachResult?>(
        future: vm.coach(draft, partnerMood: partnerMood),
        builder: (ctx, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const _SheetShell(
              child: Padding(
                padding: EdgeInsets.all(32),
                child: Center(child: CircularProgressIndicator()),
              ),
            );
          }
          // Hand the coach result back out so we can render it in a sheet that
          // can itself pop with a chosen rewrite.
          WidgetsBinding.instance.addPostFrameCallback(
            (_) => Navigator.of(ctx).pop(snap.data),
          );
          return const SizedBox.shrink();
        },
      ),
    );
    if (result == null || !context.mounted) return null;
    return showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => ToneCoachSheet(result: result),
    );
  }

  @override
  Widget build(BuildContext context) {
    return _SheetShell(child: _body(context));
  }

  Widget _body(BuildContext context) {
    if (result.declined) {
      final msg = result.safety?.message ?? '';
      return Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: const [
              Icon(Icons.favorite_border, color: AppColors.warmCoral),
              SizedBox(width: 8),
              Text('A moment first',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 12),
          Text(msg, style: const TextStyle(fontSize: 15, height: 1.4)),
          const SizedBox(height: 16),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Okay'),
            ),
          ),
        ],
      );
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.spa_outlined, color: AppColors.calmTeal),
            const SizedBox(width: 8),
            const Text('How this might land',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const Spacer(),
            if (result.tone.isNotEmpty)
              Chip(
                label: Text(result.tone, style: const TextStyle(fontSize: 12)),
                backgroundColor: AppColors.goldLight.withValues(alpha: 0.3),
                visualDensity: VisualDensity.compact,
              ),
          ],
        ),
        if (result.read.isNotEmpty) ...[
          const SizedBox(height: 10),
          Text(result.read, style: const TextStyle(fontSize: 15, height: 1.4)),
        ],
        if (result.rewrites.isNotEmpty) ...[
          const SizedBox(height: 18),
          Text('Kinder ways to say it',
              style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: AppColors.softCharcoal.withValues(alpha: 0.7))),
          const SizedBox(height: 8),
          for (final r in result.rewrites) _RewriteTile(text: r),
        ],
        const SizedBox(height: 12),
        Text(result.disclaimer,
            style: TextStyle(
                fontSize: 11,
                fontStyle: FontStyle.italic,
                color: AppColors.softCharcoal.withValues(alpha: 0.6))),
      ],
    );
  }
}

class _RewriteTile extends StatelessWidget {
  final String text;
  const _RewriteTile({required this.text});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => Navigator.of(context).pop(text),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.rosePeach),
          ),
          child: Row(
            children: [
              Expanded(child: Text(text, style: const TextStyle(fontSize: 14, height: 1.4))),
              const SizedBox(width: 8),
              const Icon(Icons.arrow_upward, size: 16, color: AppColors.warmCoral),
            ],
          ),
        ),
      ),
    );
  }
}

class _SheetShell extends StatelessWidget {
  final Widget child;
  const _SheetShell({required this.child});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Container(
        margin: const EdgeInsets.all(12),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: AppColors.creamWhite,
          borderRadius: BorderRadius.circular(20),
        ),
        child: child,
      ),
    );
  }
}
