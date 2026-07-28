import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/features/auth/viewmodels/splash_viewmodel.dart';
import 'package:mobile/features/auth/models/splash_config.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/shared/widgets/glowing_orb.dart';
import 'package:mobile/features/auth/views/welcome_screen.dart';
import 'package:mobile/features/auth/views/auth_landing_screen.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';

/// Splash screen with animated glowing orbs
/// Implements gentle, calming design principles
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with TickerProviderStateMixin {
  @override
  void initState() {
    super.initState();

    // Initialize ViewModel after first frame
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final viewModel = context.read<SplashViewModel>();
      final size = MediaQuery.of(context).size;
      viewModel.initialize(
        this,
        size,
        onAnimationComplete: () async {
          // Restore a saved session if there is one, so a logged-in user isn't
          // sent back to the welcome/login flow on every app start.
          final authVM = context.read<AuthViewModel>();
          final restored = await authVM.tryRestoreSession();
          if (!mounted) return;
          Navigator.of(context).pushReplacement(
            PageRouteBuilder(
              pageBuilder: (context, animation, secondaryAnimation) =>
                  restored ? const AuthLandingScreen() : const WelcomeScreen(),
              transitionsBuilder:
                  (context, animation, secondaryAnimation, child) {
                    return FadeTransition(opacity: animation, child: child);
                  },
              transitionDuration: const Duration(milliseconds: 800),
            ),
          );
        },
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        // Full-screen gradient background (rose → peach)
        decoration: const BoxDecoration(gradient: AppColors.splashGradient),
        child: Stack(
          children: [
            // Animated orbs
            Consumer<SplashViewModel>(
              builder: (context, viewModel, child) {
                if (!viewModel.isInitialized) {
                  return const SizedBox.shrink();
                }

                return Stack(
                  children: [
                    // Orb 1
                    if (viewModel.orb1 != null)
                      GlowingOrb(orb: viewModel.orb1!),

                    // Orb 2
                    if (viewModel.orb2 != null)
                      GlowingOrb(orb: viewModel.orb2!),
                  ],
                );
              },
            ),

            // Text content
            Positioned(
              left: 0,
              right: 0,
              bottom: SplashConfig.textBottomPadding,
              child: Consumer<SplashViewModel>(
                builder: (context, viewModel, child) {
                  if (!viewModel.isInitialized) {
                    return const SizedBox.shrink();
                  }

                  return FadeTransition(
                    opacity: viewModel.getTextFadeAnimation(),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        // Main text
                        Text(
                          SplashConfig.mainText,
                          textAlign: TextAlign.center,
                          style: AppTheme.textTheme.displaySmall?.copyWith(
                            color: Colors.white,
                            fontWeight: FontWeight.w600,
                          ),
                        ),

                        SizedBox(height: SplashConfig.textSpacing),

                        // Subtext
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 40),
                          child: Text(
                            SplashConfig.subText,
                            textAlign: TextAlign.center,
                            style: AppTheme.textTheme.bodyMedium?.copyWith(
                              color: Colors.white.withValues(alpha: 0.95),
                              height: 1.5,
                            ),
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
