import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/consent/models/consent_model.dart';
import 'package:mobile/features/consent/viewmodels/consent_viewmodel.dart';

/// Displays the per-session consent summary before any session content.
///
/// Per Section 4.2: shown at the start of EVERY session. Blocks session
/// start until the user explicitly taps "Start session". Cannot be
/// dismissed by dragging.
///
/// Usage: call [ConsentSummarySheet.show] and await its result.
/// Returns `true` when the user taps "Start session", `false` on error.
class ConsentSummarySheet extends StatefulWidget {
  final String userId;

  const ConsentSummarySheet({super.key, required this.userId});

  /// Shows the sheet and returns [true] when the user taps "Start session".
  static Future<bool> show(BuildContext context, String userId) async {
    final result = await showModalBottomSheet<bool>(
      context: context,
      // Prevent accidental dismissal — only "Start session" closes this.
      isDismissible: false,
      enableDrag: false,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => ChangeNotifierProvider.value(
        value: context.read<ConsentViewModel>(),
        child: ConsentSummarySheet(userId: userId),
      ),
    );
    return result ?? false;
  }

  @override
  State<ConsentSummarySheet> createState() => _ConsentSummarySheetState();
}

class _ConsentSummarySheetState extends State<ConsentSummarySheet> {
  @override
  void initState() {
    super.initState();
    // Fetch fresh consent on every sheet open — no cache.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ConsentViewModel>().fetchConsent(widget.userId);
    });
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.55,
      minChildSize: 0.55,
      maxChildSize: 0.75,
      // Prevent snap-to-dismiss by keeping minChildSize at 55%
      snap: false,
      builder: (context, scrollController) {
        return _SheetContent(
          userId: widget.userId,
          scrollController: scrollController,
        );
      },
    );
  }
}

class _SheetContent extends StatelessWidget {
  final String userId;
  final ScrollController scrollController;

  const _SheetContent({
    required this.userId,
    required this.scrollController,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      // Ensure the sheet content has a defined height to avoid layout issues in tests
      constraints: BoxConstraints(
        maxHeight: MediaQuery.of(context).size.height * 0.75,
      ),
      decoration: const BoxDecoration(
        color: AppColors.creamWhite,
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const SizedBox(height: 12),
          Container(
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: AppColors.softCharcoal.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(height: 20),
          Expanded(
            child: Consumer<ConsentViewModel>(
              builder: (context, vm, _) {
                if (vm.isLoading) {
                  return const Center(
                    child: CircularProgressIndicator(color: AppColors.warmCoral),
                  );
                }

                final consent = vm.consent;
                if (consent == null) {
                  return const _ErrorState();
                }

                return ListView(
                  controller: scrollController,
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  physics: const ClampingScrollPhysics(),
                  children: [
                    _Header(),
                    const SizedBox(height: 8),
                    _ConsentDivider(),
                    const SizedBox(height: 16),
                    _ConsentRow(
                      icon: '💬',
                      label: 'Session history',
                      value: ConsentModel.labelFor(consent.sessionTranscriptRetention),
                      field: 'session_transcript_retention',
                      options: const ['per_session', '30_days', '1_year', 'indefinite'],
                      userId: userId,
                    ),
                    _ConsentRow(
                      icon: '🔗',
                      label: 'Partner insights',
                      value: ConsentModel.labelFor(consent.crossPartnerInsightSharing),
                      field: 'cross_partner_insight_sharing',
                      options: const ['never', 'anonymized', 'named'],
                      userId: userId,
                    ),
                    _ConsentRow(
                      icon: '👥',
                      label: 'Joint sessions',
                      value: ConsentModel.labelFor(consent.jointSessionParticipation),
                      field: 'joint_session_participation',
                      options: const ['not_enrolled', 'enrolled'],
                      userId: userId,
                    ),
                    _ConsentRow(
                      icon: '📋',
                      label: 'Therapist access',
                      value: consent.therapistSummaryAccess ? 'On' : 'Off',
                      field: 'therapist_summary_access',
                      options: null,
                      isBool: true,
                      userId: userId,
                    ),
                    const SizedBox(height: 24),
                    _FooterActions(userId: userId),
                    const SizedBox(height: 30),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _Header extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.lock_outline, color: AppColors.calmTeal, size: 22),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'Your current privacy settings',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: AppColors.softCharcoal,
                    ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Text(
          'Review what is stored and shared before starting your session.',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: AppColors.softCharcoal.withValues(alpha: 0.6),
              ),
        ),
      ],
    );
  }
}

class _ConsentDivider extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Divider(
      color: AppColors.softCharcoal.withValues(alpha: 0.1),
      height: 1,
    );
  }
}

/// A single consent permission row with an inline tap-to-change target.
class _ConsentRow extends StatelessWidget {
  final String icon;
  final String label;
  final String value;
  final String field;
  final List<String>? options;
  final bool isBool;
  final String userId;

  const _ConsentRow({
    required this.icon,
    required this.label,
    required this.value,
    required this.field,
    required this.options,
    required this.userId,
    this.isBool = false,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        children: [
          Text(icon, style: const TextStyle(fontSize: 20)),
          const SizedBox(width: 14),
          Expanded(
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w500,
                    color: AppColors.softCharcoal,
                  ),
            ),
          ),
          _ValueChip(
            value: value,
            onTap: () => _showPicker(context),
          ),
        ],
      ),
    );
  }

  void _showPicker(BuildContext context) {
    final vm = context.read<ConsentViewModel>();
    if (isBool) {
      // Toggle boolean — current value is derived from label "On"/"Off"
      final current = value == 'On';
      vm.updateField(userId, field, !current);
      return;
    }
    if (options == null) return;
    showModalBottomSheet<void>(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(height: 8),
            Container(
              width: 36,
              height: 4,
              decoration: BoxDecoration(
                color: AppColors.softCharcoal.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(height: 8),
            for (final opt in options!)
              ListTile(
                key: Key('consent_option_$opt'),
                title: Text(ConsentModel.labelFor(opt)),
                trailing: value == ConsentModel.labelFor(opt)
                    ? const Icon(Icons.check, color: AppColors.calmTeal)
                    : null,
                onTap: () {
                  vm.updateField(userId, field, opt);
                  Navigator.pop(context);
                },
              ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }
}

/// Tap target chip showing the current consent value.
class _ValueChip extends StatelessWidget {
  final String value;
  final VoidCallback onTap;

  const _ValueChip({required this.value, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: AppColors.calmTeal.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: AppColors.calmTeal.withValues(alpha: 0.3),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Flexible(
              child: Text(
                value,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppColors.calmTeal,
                      fontWeight: FontWeight.w600,
                    ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(width: 4),
            const Icon(
              Icons.keyboard_arrow_down_rounded,
              size: 16,
              color: AppColors.calmTeal,
            ),
          ],
        ),
      ),
    );
  }
}

/// Bottom action buttons — "Change settings" and "Start session".
class _FooterActions extends StatelessWidget {
  final String userId;

  const _FooterActions({required this.userId});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: OutlinedButton(
            key: const Key('change_settings_button'),
            onPressed: () {
              // REL-34: push ConsentDashboardScreen
              // For now, show a snack bar as a placeholder
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Consent dashboard coming in REL-34'),
                  duration: Duration(seconds: 2),
                ),
              );
            },
            style: OutlinedButton.styleFrom(
              foregroundColor: AppColors.softCharcoal,
              side: BorderSide(
                color: AppColors.softCharcoal.withValues(alpha: 0.3),
              ),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
              ),
              padding: const EdgeInsets.symmetric(vertical: 14),
            ),
            child: const Text('Change settings'),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: ElevatedButton(
            key: const Key('start_session_button'),
            onPressed: () => Navigator.of(context).pop(true),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.warmCoral,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
              ),
              padding: const EdgeInsets.symmetric(vertical: 14),
              elevation: 0,
            ),
            child: const Text(
              'Start session',
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
          ),
        ),
      ],
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, color: AppColors.error, size: 40),
            const SizedBox(height: 12),
            Text(
              'Unable to load consent settings.',
              style: Theme.of(context).textTheme.bodyMedium,
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
