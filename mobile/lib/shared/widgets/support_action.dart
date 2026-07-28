import 'package:flutter/material.dart';
import 'package:mobile/core/theme/app_colors.dart';

/// A quiet, always-available route to the support resources.
///
/// This replaces `GetHelpNowButton`, which painted a full-width `#B71C1C` bar
/// across nine screens while a second red floating button sat on top of it on
/// three tabs — neither tied to any risk signal. In an otherwise soft palette
/// that made the loudest thing in the app an alarm that never stopped
/// sounding, which read as bracing for catastrophe rather than offering care.
///
/// Nothing about the destination changes: the same screen, the same hotlines,
/// the same one tap away from anywhere. Only the volume changes. Emergency red
/// still appears — inside the support screen, on the emergency-services row,
/// where it means something.
class SupportAction extends StatelessWidget {
  const SupportAction({super.key});

  @override
  Widget build(BuildContext context) {
    return IconButton(
      icon: const Icon(Icons.volunteer_activism_outlined, size: 21),
      color: AppColors.softCharcoal.withValues(alpha: 0.55),
      tooltip: 'Support',
      // Named so screen readers announce a calm, meaningful destination.
      onPressed: () => Navigator.of(context).pushNamed('/safety'),
    );
  }
}
