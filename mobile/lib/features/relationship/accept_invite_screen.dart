import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/shared/widgets/animated_button.dart';
import 'package:mobile/features/relationship/relationship_viewmodel.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';

class AcceptInviteScreen extends StatefulWidget {
  final String token;

  const AcceptInviteScreen({super.key, required this.token});

  @override
  State<AcceptInviteScreen> createState() => _AcceptInviteScreenState();
}

class _AcceptInviteScreenState extends State<AcceptInviteScreen> {
  @override
  void initState() {
    super.initState();
    // In a real app, we might fetch the inviter's name here using the token
  }

  Future<void> _handleAccept(RelationshipViewModel vm) async {
    final success = await vm.acceptInvite(widget.token);
    if (success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Relationship connected!'),
          backgroundColor: AppColors.calmTeal,
        ),
      );
      // Navigate to home or dashboard
      Navigator.of(context).popUntil((route) => route.isFirst);
    }
  }

  @override
  Widget build(BuildContext context) {
    final authVm = context.watch<AuthViewModel>();
    final relVm = context.watch<RelationshipViewModel>();

    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(32.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.favorite, size: 80, color: AppColors.warmCoral),
              const SizedBox(height: 32),
              const Text(
                'Connect with Partner',
                style: TextStyle(
                  fontSize: 26,
                  fontWeight: FontWeight.bold,
                  color: AppColors.softCharcoal,
                ),
              ),
              const SizedBox(height: 16),
              const Text(
                'Your partner has invited you to join them on RelationshipAI. Connecting will allow you to share therapeutic context and participate in joint sessions.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 16,
                  color: AppColors.softCharcoal,
                  height: 1.5,
                ),
              ),
              const SizedBox(height: 48),
              if (authVm.user != null)
                _buildAcceptAction(relVm)
              else
                _buildLoginRequiredState(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAcceptAction(RelationshipViewModel vm) {
    return Column(
      children: [
        if (vm.errorMessage != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 16.0),
            child: Text(
              vm.errorMessage!,
              style: const TextStyle(color: AppColors.error),
            ),
          ),
        AnimatedButton(
          label: vm.isActionLoading ? 'Connecting...' : 'Accept and Connect',
          onTap: vm.isActionLoading ? null : () => _handleAccept(vm),
          isFilled: true,
          height: 60,
          borderRadius: 16,
        ),
      ],
    );
  }

  Widget _buildLoginRequiredState() {
    return Column(
      children: [
        const Text(
          'Please sign in or create an account to accept this invitation.',
          textAlign: TextAlign.center,
          style: TextStyle(fontWeight: FontWeight.w500),
        ),
        const SizedBox(height: 24),
        AnimatedButton(
          label: 'Get Started',
          onTap: () {
            // Save token to secure storage for later use after signup
            // and navigate to welcome/signup
            Navigator.of(context).pushNamed('/signup');
          },
          isFilled: true,
          height: 56,
          borderRadius: 14,
        ),
      ],
    );
  }
}
