import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../tone/tone_viewmodel.dart';
import '../tone/vibe_models.dart';

/// A small celebratory sheet showing the day's conversation "vibe" — a playful
/// one-word read (Intimate, Playful, Reconnecting, Quiet…). Just for fun.
class DailyVibeSheet extends StatelessWidget {
  final DailyVibe vibe;
  const DailyVibeSheet({super.key, required this.vibe});

  /// Computes the vibe (showing a loading sheet) then reveals it. No-op reveal
  /// if the call fails — the vibe is a delight, never a blocker.
  static Future<void> open(
    BuildContext context,
    ToneViewModel vm,
    List<Map<String, String>> messages,
  ) async {
    final vibe = await showModalBottomSheet<DailyVibe?>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (_) => FutureBuilder<DailyVibe?>(
        future: vm.readVibe(messages),
        builder: (ctx, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const _Shell(
              child: Padding(
                padding: EdgeInsets.all(28),
                child: Center(child: CircularProgressIndicator()),
              ),
            );
          }
          WidgetsBinding.instance.addPostFrameCallback(
            (_) => Navigator.of(ctx).pop(snap.data),
          );
          return const SizedBox.shrink();
        },
      ),
    );
    if (vibe == null || !context.mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (_) => DailyVibeSheet(vibe: vibe),
    );
  }

  @override
  Widget build(BuildContext context) {
    return _Shell(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text("Today's vibe",
              style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppColors.softCharcoal.withValues(alpha: 0.6))),
          const SizedBox(height: 12),
          Text(vibe.emoji, style: const TextStyle(fontSize: 48)),
          const SizedBox(height: 8),
          Text(vibe.label,
              style: const TextStyle(fontSize: 26, fontWeight: FontWeight.bold)),
          if (vibe.blurb.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(vibe.blurb,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 15, height: 1.4)),
          ],
          const SizedBox(height: 16),
          if (vibe.disclaimer.isNotEmpty)
            Text(vibe.disclaimer,
                textAlign: TextAlign.center,
                style: TextStyle(
                    fontSize: 11,
                    fontStyle: FontStyle.italic,
                    color: AppColors.softCharcoal.withValues(alpha: 0.5))),
          const SizedBox(height: 8),
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }
}

class _Shell extends StatelessWidget {
  final Widget child;
  const _Shell({required this.child});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Container(
        margin: const EdgeInsets.all(12),
        padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 20),
        decoration: BoxDecoration(
          color: AppColors.creamWhite,
          borderRadius: BorderRadius.circular(20),
        ),
        child: child,
      ),
    );
  }
}
