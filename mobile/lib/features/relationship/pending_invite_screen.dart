import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/shared/widgets/animated_button.dart';
import 'package:mobile/features/relationship/relationship_viewmodel.dart';

class PendingInviteScreen extends StatelessWidget {
  const PendingInviteScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<RelationshipViewModel>();
    final invitee = vm.currentRelationship?['invitee_email'] ?? 'your partner';
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Invitation Pending'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        foregroundColor: AppColors.softCharcoal,
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.hourglass_empty, size: 80, color: AppColors.warmCoral),
              const SizedBox(height: 16),
              Text(
                'Waiting for $invitee to accept...',
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w600,
                  color: AppColors.softCharcoal,
                ),
              ),
              const SizedBox(height: 12),
              const Text(
                'Invites expire in 72 hours. You can cancel this invite to send a new one.',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppColors.softCharcoal),
              ),
              const SizedBox(height: 24),
              AnimatedButton(
                label: vm.isActionLoading ? 'Cancelling...' : 'Cancel Invitation',
                onTap: vm.isActionLoading ? null : () => vm.dissolveRelationship(),
                isFilled: true,
                height: 56,
                borderRadius: 14,
                fillColor: AppColors.error,

              ),
            ],
          ),
        ),
      ),
    );
  }
}
