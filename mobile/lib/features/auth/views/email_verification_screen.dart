import 'package:flutter/material.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/shared/widgets/animated_button.dart';
import 'package:mobile/features/auth/views/login_screen.dart';

class EmailVerificationScreen extends StatelessWidget {
  final String email;

  const EmailVerificationScreen({super.key, this.email = ''});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Verify Email'),
        backgroundColor: AppColors.creamWhite,
        elevation: 0,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 40.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              const Icon(
                Icons.mark_email_read_outlined,
                size: 80,
                color: AppColors.warmCoral,
              ),
              const SizedBox(height: 32),
              Text(
                'Check your email',
                textAlign: TextAlign.center,
                style: AppTheme.textTheme.displaySmall?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: AppColors.softCharcoal,
                ),
              ),
              const SizedBox(height: 16),
              Text(
                'We have sent a verification link to\n${email.isNotEmpty ? email : "your email address"}',
                textAlign: TextAlign.center,
                style: AppTheme.textTheme.bodyLarge?.copyWith(
                  color: AppColors.softCharcoal.withValues(alpha: 0.7),
                  height: 1.5,
                ),
              ),
              const Spacer(),
              AnimatedButton(
                label: 'Back to Login',
                isFilled: true,
                height: 56,
                borderRadius: 14,
                onTap: () {
                  Navigator.pushAndRemoveUntil(
                    context,
                    MaterialPageRoute(builder: (_) => const LoginScreen()),
                    (route) => false,
                  );
                },
              ),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}
