import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/features/consent/viewmodels/consent_viewmodel.dart';
import 'package:mobile/features/consent/models/consent_model.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/shared/widgets/animated_button.dart';

class ConsentSummarySheet extends StatefulWidget {
  final VoidCallback onStartSession;
  final bool isFirstSession;

  const ConsentSummarySheet({
    super.key,
    required this.onStartSession,
    this.isFirstSession = false,
  });

  /// Displays the consent summary sheet as a modal bottom sheet.
  /// Returns true if the user tapped "Start session".
  static Future<bool> show(BuildContext context, String userId, {bool isFirstSession = false}) async {
    bool started = false;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      isDismissible: !isFirstSession,
      enableDrag: !isFirstSession,
      backgroundColor: Colors.transparent,
      builder: (_) => ConsentSummarySheet(
        isFirstSession: isFirstSession,
        onStartSession: () {
          started = true;
          Navigator.pop(context);
        },
      ),
    );
    return started;
  }

  @override
  State<ConsentSummarySheet> createState() => _ConsentSummarySheetState();
}

class _ConsentSummarySheetState extends State<ConsentSummarySheet> {
  bool _canDismiss = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final viewModel = context.read<ConsentViewModel>();
      viewModel.fetchConsent();
      viewModel.logSummaryShown();
    });

    if (!widget.isFirstSession) {
      Future.delayed(const Duration(seconds: 2), () {
        if (mounted) setState(() => _canDismiss = true);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final viewModel = context.watch<ConsentViewModel>();
    final consent = viewModel.consent;

    return PopScope(
      canPop: _canDismiss,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.lock_outline, color: AppColors.warmCoral),
                const SizedBox(width: 12),
                Text(
                  'Before we begin',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: AppColors.softCharcoal,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            const Text(
              'Here\'s what\'s active for this session:',
              style: TextStyle(fontSize: 16, color: Colors.grey),
            ),
            const SizedBox(height: 24),
            if (viewModel.isLoading)
              const Center(child: Padding(
                padding: EdgeInsets.all(40.0),
                child: CircularProgressIndicator(),
              ))
            else if (viewModel.errorMessage != null)
              _buildErrorState(viewModel)
            else if (consent != null)
              _buildConsentList(context, consent)
            else
              const SizedBox(height: 200),
            
            const Divider(height: 48),
            
            TextButton(
              onPressed: () => Navigator.pushNamed(context, '/consent')
                  .then((_) {
                    if (context.mounted) context.read<ConsentViewModel>().fetchConsent();
                  }),
              child: const Text('View full privacy settings', 
                style: TextStyle(color: AppColors.warmCoral, fontWeight: FontWeight.bold)),
            ),
            const SizedBox(height: 16),
            AnimatedButton(
              label: 'Start session',
              onTap: viewModel.consent == null ? null : () {
                if (mounted) widget.onStartSession();
              },
              useGoldGradient: true,
            ),
            SizedBox(height: MediaQuery.of(context).viewInsets.bottom),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorState(ConsentViewModel viewModel) {
    return Column(
      children: [
        Text(viewModel.errorMessage!, style: const TextStyle(color: Colors.red), textAlign: TextAlign.center),
        const SizedBox(height: 16),
        TextButton(
          onPressed: () => viewModel.fetchConsent(),
          child: const Text('Try again'),
        ),
      ],
    );
  }

  Widget _buildConsentList(BuildContext context, ConsentModel consent) {
    final summary = consent.plainLanguageSummary;
    return Column(
      children: [
        _buildConsentItem(
          icon: Icons.folder_outlined,
          title: 'Session storage',
          description: summary['session_transcript_retention'] ?? 'Loading...',
          onEdit: () => _openDashboard(context),
        ),
        _buildConsentItem(
          icon: Icons.handshake_outlined,
          title: 'Sharing with your partner',
          description: summary['cross_partner_insight_sharing'] ?? 'Loading...',
          onEdit: () => _openDashboard(context),
        ),
        _buildConsentItem(
          icon: Icons.person_outline,
          title: 'Joint sessions',
          description: summary['joint_session_participation'] ?? 'Loading...',
          onEdit: () => _openDashboard(context),
        ),
        _buildConsentItem(
          icon: Icons.local_hospital_outlined,
          title: 'Therapist access',
          description: summary['therapist_summary_access'] ?? 'Loading...',
          onEdit: () => _openDashboard(context),
        ),
      ],
    );
  }

  Widget _buildConsentItem({
    required IconData icon,
    required String title,
    required String description,
    required VoidCallback onEdit,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 20.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 24, color: AppColors.calmTeal),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
                Text(description, style: const TextStyle(fontSize: 13, color: Colors.grey)),
              ],
            ),
          ),
          TextButton(
            onPressed: onEdit,
            child: const Text('Edit', style: TextStyle(fontSize: 13)),
          ),
        ],
      ),
    );
  }

  void _openDashboard(BuildContext context) {
    Navigator.pushNamed(context, '/consent')
        .then((_) {
          if (context.mounted) context.read<ConsentViewModel>().fetchConsent();
        });
  }
}
