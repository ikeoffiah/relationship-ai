import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/features/auth/views/login_screen.dart';
import 'package:mobile/shared/widgets/animated_button.dart';

class RouteGuardTestScreen extends StatelessWidget {
  const RouteGuardTestScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final authViewModel = context.watch<AuthViewModel>();

    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Route Guard Test'),
        backgroundColor: AppColors.warmCoral,
        foregroundColor: Colors.white,
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(
                Icons.security_rounded,
                size: 80,
                color: AppColors.calmTeal,
              ),
              const SizedBox(height: 24),
              Text(
                'Authenticated Route',
                style: AppTheme.textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: AppColors.softCharcoal,
                ),
              ),
              const SizedBox(height: 16),
              Text(
                'You are currently signed in as:\n${authViewModel.email.isNotEmpty ? authViewModel.email : "Unknown User"}',
                textAlign: TextAlign.center,
                style: AppTheme.textTheme.bodyLarge?.copyWith(
                  color: AppColors.softCharcoal.withValues(alpha: 0.8),
                ),
              ),
              const SizedBox(height: 48),
              AnimatedButton(
                label: 'Sign Out',
                isFilled: true,
                onTap: () async {
                  await authViewModel.logout();
                  if (context.mounted) {
                    Navigator.pushAndRemoveUntil(
                      context,
                      MaterialPageRoute(builder: (_) => const LoginScreen()),
                      (route) => false,
                    );
                  }
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}
