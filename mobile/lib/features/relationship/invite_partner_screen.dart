import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/shared/widgets/animated_button.dart';
import 'package:mobile/features/relationship/relationship_viewmodel.dart';

class InvitePartnerScreen extends StatefulWidget {
  const InvitePartnerScreen({super.key});

  @override
  State<InvitePartnerScreen> createState() => _InvitePartnerScreenState();
}

class _InvitePartnerScreenState extends State<InvitePartnerScreen> {
  final TextEditingController _emailController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _handleInvite(RelationshipViewModel vm) async {
    if (_formKey.currentState!.validate()) {
      final success = await vm.sendInvite(_emailController.text);
      if (success && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Invite sent successfully!'),
            backgroundColor: AppColors.calmTeal,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<RelationshipViewModel>();

    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Connect with Partner'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        foregroundColor: AppColors.softCharcoal,
      ),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Journey Together',
              style: TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.bold,
                color: AppColors.softCharcoal,
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'Invite your partner to share this therapeutic space. Many features like joint sessions and shared insights require a connection.',
              style: TextStyle(
                fontSize: 16,
                color: AppColors.softCharcoal,
                height: 1.5,
              ),
            ),
            const SizedBox(height: 40),
            if (vm.status == RelationshipStatus.pending)
              _buildPendingState(vm)
            else
              _buildInviteForm(vm),
          ],
        ),
      ),
    );
  }

  Widget _buildInviteForm(RelationshipViewModel vm) {
    return Form(
      key: _formKey,
      child: Column(
        children: [
          TextFormField(
            controller: _emailController,
            decoration: InputDecoration(
              labelText: "Partner's Email",
              hintText: "email@example.com",
              prefixIcon: const Icon(Icons.email_outlined),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: const BorderSide(color: AppColors.warmCoral, width: 2),
              ),
            ),
            keyboardType: TextInputType.emailAddress,
            validator: (value) {
              if (value == null || value.isEmpty) return 'Please enter an email';
              if (!value.contains('@')) return 'Please enter a valid email';
              return null;
            },
          ),
          const SizedBox(height: 24),
          if (vm.errorMessage != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 16.0),
              child: Text(
                vm.errorMessage!,
                style: const TextStyle(color: AppColors.error),
              ),
            ),
          AnimatedButton(
            label: vm.isActionLoading ? 'Sending...' : 'Send Invitation',
            onTap: vm.isActionLoading ? null : () => _handleInvite(vm),
            isFilled: true,
            height: 56,
            borderRadius: 14,
          ),
        ],
      ),
    );
  }

  Widget _buildPendingState(RelationshipViewModel vm) {
    final invitee = vm.currentRelationship?['invitee_email'] ?? 'your partner';
    
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.rosePeach.withValues(alpha: 0.3),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.softRose),
      ),
      child: Column(
        children: [
          const Icon(Icons.hourglass_empty, size: 48, color: AppColors.warmCoral),
          const SizedBox(height: 16),
          Text(
            'Waiting for $invitee to accept...',
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: AppColors.softCharcoal,
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Invites expire in 72 hours. You can cancel this invite to send a new one.',
            textAlign: TextAlign.center,
            style: TextStyle(color: AppColors.softCharcoal),
          ),
          const SizedBox(height: 24),
          TextButton(
            onPressed: vm.isActionLoading ? null : () => vm.dissolveRelationship(),
            child: const Text(
              'Cancel Invitation',
              style: TextStyle(color: AppColors.error),
            ),
          ),
        ],
      ),
    );
  }
}
