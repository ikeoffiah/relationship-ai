import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_dimens.dart';
import 'package:mobile/shared/widgets/app_card.dart';
import 'safety_resources_data.dart';

/// Support resources — hotlines and crisis services.
///
/// Every resource, phone number, availability line and disclaimer here is
/// unchanged. What changed is the framing: this screen used to open under a
/// full-bleed `#B71C1C` app bar titled "Get Help Now 🆘", matching a red bar
/// that was stamped onto nine other screens. Reaching help is still one tap
/// from anywhere, but the app no longer looks like it is bracing for
/// catastrophe on the games screen.
///
/// Emergency red is retained for the emergency-services block specifically,
/// where the urgency is real and the colour carries meaning.
class SafetyResourcesScreen extends StatelessWidget {
  const SafetyResourcesScreen({super.key});

  Future<void> _launchResource(SafetyResource resource) async {
    if (resource.phoneNumber != null &&
        resource.chatUrl == null &&
        resource.textNumber == null) {
      // Phone call
      final Uri uri = Uri(scheme: 'tel', path: resource.phoneNumber);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri);
      }
    } else if (resource.textNumber != null) {
      // SMS
      final Uri uri = Uri(
        scheme: 'sms',
        path: resource.textNumber,
        queryParameters: {'body': resource.textKeyword ?? ''},
      );
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri);
      }
    } else if (resource.chatUrl != null) {
      // Web chat
      final Uri uri = Uri.parse(resource.chatUrl!);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.inAppBrowserView);
      }
    }
  }

  Widget _buildSectionHeading(BuildContext context, String text) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.xxl,
        AppSpacing.xxl,
        AppSpacing.xxl,
        AppSpacing.md,
      ),
      child: Text(text, style: Theme.of(context).textTheme.titleLarge),
    );
  }

  Widget _buildResourceCard(BuildContext context, SafetyResource resource) {
    // The emergency block keeps the urgent colour. Everything else sits on the
    // app's own palette so the screen reads as care rather than alarm.
    final bool isEmergency = resource.category == 'Emergency';
    final Color accent = isEmergency ? AppColors.crisis : AppColors.calmTeal;

    return Padding(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.xxl,
        0,
        AppSpacing.xxl,
        AppSpacing.md,
      ),
      child: AppCard(
        borderColor: accent.withValues(alpha: isEmergency ? 0.45 : 0.3),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              resource.name,
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(color: accent),
            ),
            if (resource.description != null) ...[
              const SizedBox(height: AppSpacing.xs),
              Text(
                resource.description!,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
            const SizedBox(height: AppSpacing.xs),
            Text(
              'Available: ${resource.available}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: AppSpacing.lg),
            Wrap(
              spacing: AppSpacing.sm,
              runSpacing: AppSpacing.sm,
              children: [
                if (resource.phoneNumber != null)
                  _action(
                    context,
                    icon: Icons.phone,
                    label: resource.category == 'DomesticViolence'
                        ? 'Call'
                        : 'Call ${resource.phoneNumber}',
                    accent: accent,
                    filled: true,
                    onPressed: () => _launchResource(
                      SafetyResource(
                        category: resource.category,
                        name: resource.name,
                        phoneNumber: resource.phoneNumber,
                        available: resource.available,
                      ),
                    ),
                  ),
                if (resource.textNumber != null)
                  _action(
                    context,
                    icon: Icons.message_outlined,
                    label: 'Text',
                    accent: accent,
                    filled: false,
                    onPressed: () => _launchResource(
                      SafetyResource(
                        category: resource.category,
                        name: resource.name,
                        textNumber: resource.textNumber,
                        textKeyword: resource.textKeyword,
                        available: resource.available,
                      ),
                    ),
                  ),
                if (resource.chatUrl != null)
                  _action(
                    context,
                    icon: Icons.chat_bubble_outline_rounded,
                    label: 'Chat online',
                    accent: accent,
                    filled: false,
                    onPressed: () => _launchResource(
                      SafetyResource(
                        category: resource.category,
                        name: resource.name,
                        chatUrl: resource.chatUrl,
                        available: resource.available,
                      ),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _action(
    BuildContext context, {
    required IconData icon,
    required String label,
    required Color accent,
    required bool filled,
    required VoidCallback onPressed,
  }) {
    return ElevatedButton.icon(
      icon: Icon(icon, size: 18),
      label: Text(label),
      onPressed: onPressed,
      style: ElevatedButton.styleFrom(
        backgroundColor: filled ? accent : accent.withValues(alpha: 0.12),
        foregroundColor: filled ? Colors.white : accent,
        elevation: 0,
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.lg,
          vertical: AppSpacing.md,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.sm),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    // Check if there are arguments passed (e.g., from safety overlay)
    final String? prependedMessage =
        ModalRoute.of(context)?.settings.arguments as String?;

    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: const BackButton(color: AppColors.softCharcoal),
        title: Text('Support', style: Theme.of(context).textTheme.titleLarge),
      ),
      body: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (prependedMessage != null)
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.xxl,
                  0,
                  AppSpacing.xxl,
                  AppSpacing.lg,
                ),
                child: AppCard(
                  color: AppColors.noticeSurface,
                  borderColor: AppColors.noticeInk.withValues(alpha: 0.25),
                  child: Text(
                    prependedMessage,
                    style: Theme.of(context).textTheme.bodyLarge,
                  ),
                ),
              ),
            Padding(
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.xxl,
                0,
                AppSpacing.xxl,
                AppSpacing.lg,
              ),
              child: Text(
                "If you're in immediate danger, please call emergency services:",
                style: Theme.of(context).textTheme.bodyLarge,
              ),
            ),
            ...safetyResources
                .where((r) => r.category == 'Emergency')
                .map((r) => _buildResourceCard(context, r)),

            _buildSectionHeading(context, 'Crisis support'),
            ...safetyResources
                .where((r) => r.category == 'Crisis')
                .map((r) => _buildResourceCard(context, r)),

            _buildSectionHeading(context, 'Domestic violence & safety'),
            ...safetyResources
                .where((r) => r.category == 'DomesticViolence')
                .map((r) => _buildResourceCard(context, r)),

            _buildSectionHeading(context, 'About this app'),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xxl),
              child: Text(
                'Bliss is an AI system, not a licensed therapist. It cannot provide emergency support.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(AppSpacing.xxl),
              child: TextButton(
                onPressed: () => Navigator.of(context).pop(),
                style: TextButton.styleFrom(
                  foregroundColor: AppColors.softCharcoal.withValues(
                    alpha: 0.7,
                  ),
                ),
                child: const Text('Return to app'),
              ),
            ),
            const SizedBox(height: AppSpacing.xxxl),
          ],
        ),
      ),
    );
  }
}
