import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/consent/models/consent_model.dart';
import 'package:mobile/features/consent/viewmodels/consent_viewmodel.dart';

/// A persistent lock icon badge shown in the chat app bar.
///
/// Per Section 14.1: always visible in the chat interface.
/// Tapping opens an inline revocation panel without ending the session.
class ConsentBadge extends StatelessWidget {
  final String userId;

  const ConsentBadge({super.key, required this.userId});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      key: const Key('consent_badge'),
      onTap: () => _showInlinePanel(context),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: AppColors.calmTeal.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: AppColors.calmTeal.withValues(alpha: 0.4),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.lock_outline,
              color: AppColors.calmTeal,
              size: 16,
            ),
            const SizedBox(width: 5),
            Text(
              'Consent',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: AppColors.calmTeal,
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showInlinePanel(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => ChangeNotifierProvider.value(
        value: context.read<ConsentViewModel>(),
        child: _ConsentInlinePanel(userId: userId),
      ),
    );
  }
}

/// Compact revocation panel opened by tapping the [ConsentBadge].
///
/// Single-tap revocation — changes take effect immediately via API.
/// Session is NOT ended or restarted on any permission change.
class _ConsentInlinePanel extends StatelessWidget {
  final String userId;

  const _ConsentInlinePanel({required this.userId});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 0, 12, 12),
      decoration: BoxDecoration(
        color: AppColors.creamWhite,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.08),
            blurRadius: 20,
            offset: const Offset(0, -4),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(height: 12),
            Container(
              width: 36,
              height: 4,
              decoration: BoxDecoration(
                color: AppColors.softCharcoal.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(height: 16),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Row(
                children: [
                  const Icon(
                    Icons.lock_outline,
                    color: AppColors.calmTeal,
                    size: 18,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'Privacy settings',
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                  const Spacer(),
                  IconButton(
                    key: const Key('close_inline_panel'),
                    icon: const Icon(Icons.close, size: 20),
                    onPressed: () => Navigator.pop(context),
                    color: AppColors.softCharcoal.withValues(alpha: 0.5),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 4),
            Consumer<ConsentViewModel>(
              builder: (context, vm, _) {
                final consent = vm.consent;
                if (vm.isLoading || consent == null) {
                  return const Padding(
                    padding: EdgeInsets.all(24),
                    child: CircularProgressIndicator(color: AppColors.calmTeal),
                  );
                }
                return Column(
                  children: [
                    _InlinePanelRow(
                      icon: '💬',
                      label: 'Session history',
                      value: ConsentModel.labelFor(
                        consent.sessionTranscriptRetention,
                      ),
                      onRevoke: () => vm.updateField(
                        userId,
                        'session_transcript_retention',
                        'per_session',
                      ),
                      isRevocable: consent.sessionTranscriptRetention !=
                          'per_session',
                    ),
                    _InlinePanelRow(
                      icon: '🔗',
                      label: 'Partner insights',
                      value: ConsentModel.labelFor(
                        consent.crossPartnerInsightSharing,
                      ),
                      onRevoke: () => vm.updateField(
                        userId,
                        'cross_partner_insight_sharing',
                        'never',
                      ),
                      isRevocable:
                          consent.crossPartnerInsightSharing != 'never',
                    ),
                    _InlinePanelRow(
                      icon: '👥',
                      label: 'Joint sessions',
                      value: ConsentModel.labelFor(
                        consent.jointSessionParticipation,
                      ),
                      onRevoke: () => vm.updateField(
                        userId,
                        'joint_session_participation',
                        'not_enrolled',
                      ),
                      isRevocable:
                          consent.jointSessionParticipation != 'not_enrolled',
                    ),
                    _InlinePanelRow(
                      icon: '📋',
                      label: 'Therapist access',
                      value: consent.therapistSummaryAccess ? 'On' : 'Off',
                      onRevoke: () => vm.updateField(
                        userId,
                        'therapist_summary_access',
                        false,
                      ),
                      isRevocable: consent.therapistSummaryAccess,
                    ),
                    if (vm.errorMessage != null)
                      Padding(
                        padding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
                        child: Text(
                          vm.errorMessage!,
                          style: const TextStyle(
                            color: AppColors.error,
                            fontSize: 12,
                          ),
                        ),
                      ),
                  ],
                );
              },
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}

/// A single row in the inline consent panel with immediate revocation.
class _InlinePanelRow extends StatelessWidget {
  final String icon;
  final String label;
  final String value;
  final VoidCallback onRevoke;
  final bool isRevocable;

  const _InlinePanelRow({
    required this.icon,
    required this.label,
    required this.value,
    required this.onRevoke,
    required this.isRevocable,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      child: Row(
        children: [
          Text(icon, style: const TextStyle(fontSize: 18)),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppColors.softCharcoal.withValues(alpha: 0.6),
                        fontWeight: FontWeight.w500,
                      ),
                ),
                const SizedBox(height: 2),
                Text(
                  value,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                        color: AppColors.softCharcoal,
                      ),
                ),
              ],
            ),
          ),
          if (isRevocable)
            TextButton(
              key: Key('revoke_${label.toLowerCase().replaceAll(' ', '_')}'),
              onPressed: onRevoke,
              style: TextButton.styleFrom(
                foregroundColor: AppColors.error,
                padding: const EdgeInsets.symmetric(horizontal: 10),
              ),
              child: const Text(
                'Revoke',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
              ),
            )
          else
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              child: Text(
                'Off',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                  color: AppColors.softCharcoal.withValues(alpha: 0.35),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
