import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/features/consent/viewmodels/consent_viewmodel.dart';
import 'package:mobile/core/theme/app_colors.dart';

class InSessionConsentBanner extends StatelessWidget {
  const InSessionConsentBanner({super.key});

  @override
  Widget build(BuildContext context) {
    final consent = context.watch<ConsentViewModel>().consent;
    if (consent == null) return const SizedBox.shrink();

    // Condensed status text
    final isPrivate = consent.crossPartnerInsightSharing == 'never';
    final sharingStatus = isPrivate ? 'Nothing shared' : 'Sharing active';
    final sessionType = 'Private session'; 

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
      decoration: BoxDecoration(
        color: AppColors.softRose.withValues(alpha: 0.1),
        border: Border(
          bottom: BorderSide(color: AppColors.softRose.withValues(alpha: 0.3)),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.lock, size: 14, color: AppColors.warmCoral),
          const SizedBox(width: 8),
          Text(
            '$sessionType · $sharingStatus',
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
          ),
          const SizedBox(width: 8),
          GestureDetector(
            onTap: () {
              Navigator.pushNamed(context, '/consent')
                  .then((_) {
                    if (context.mounted) {
                      context.read<ConsentViewModel>().fetchConsent();
                    }
                  });
            },
            child: const Text(
              'Change',
              style: TextStyle(
                fontSize: 12,
                color: AppColors.warmCoral,
                fontWeight: FontWeight.bold,
                decoration: TextDecoration.underline,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
