import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/home/views/main_navigation_screen.dart';
import 'package:mobile/features/onboarding/onboarding_flow_screen.dart';
import 'package:mobile/features/onboarding/onboarding_viewmodel.dart';

/// Where a freshly-authenticated user should land.
enum PostAuthDestination { onboarding, app }

/// The routing decision, factored out so it can be tested without building the
/// (provider-heavy) destination screens.
///
/// Only trusts [OnboardingViewModel.onboardingCompleted] when the profile
/// actually loaded. A failed lookup routes to the app rather than trapping a
/// returning user in onboarding over a transient error — the backend
/// get_or_creates a profile, so a genuine new user loads successfully with
/// onboarding_completed false and is sent to onboarding.
Future<PostAuthDestination> decidePostAuthDestination(
  OnboardingViewModel vm,
) async {
  final loaded = await vm.loadProfile();
  return (loaded && !vm.onboardingCompleted)
      ? PostAuthDestination.onboarding
      : PostAuthDestination.app;
}

/// Post-authentication gate.
///
/// Every sign-in path lands here so the onboarding decision lives in one
/// place. It reads the user's personalization profile and routes first-time
/// users through onboarding (which populates the AI's prompt_modifiers) and
/// returning users straight into the app.
class AuthLandingScreen extends StatefulWidget {
  const AuthLandingScreen({super.key});

  @override
  State<AuthLandingScreen> createState() => _AuthLandingScreenState();
}

class _AuthLandingScreenState extends State<AuthLandingScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _route());
  }

  Future<void> _route() async {
    final destination =
        await decidePostAuthDestination(context.read<OnboardingViewModel>());

    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(
        builder: (_) => destination == PostAuthDestination.onboarding
            ? const OnboardingFlowScreen()
            : const MainNavigationScreen(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      backgroundColor: AppColors.creamWhite,
      body: Center(child: CircularProgressIndicator()),
    );
  }
}
