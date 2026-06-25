import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/onboarding/onboarding_viewmodel.dart';
import 'package:mobile/features/onboarding/screens/rsq_screen.dart';
import 'package:mobile/features/onboarding/screens/relationship_context_screen.dart';
import 'package:mobile/features/onboarding/screens/cultural_context_screen.dart';
import 'package:mobile/features/onboarding/screens/communication_quiz_screen.dart';

/// Orchestrates the 4-step onboarding flow using a PageView.
class OnboardingFlowScreen extends StatefulWidget {
  const OnboardingFlowScreen({super.key});

  @override
  State<OnboardingFlowScreen> createState() => _OnboardingFlowScreenState();
}

class _OnboardingFlowScreenState extends State<OnboardingFlowScreen> {
  late PageController _pageController;

  @override
  void initState() {
    super.initState();
    _pageController = PageController();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final vm = context.read<OnboardingViewModel>();
      vm.loadQuestionnaire();
      vm.loadProfile();
    });
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _goToPage(int page) {
    _pageController.animateToPage(
      page,
      duration: const Duration(milliseconds: 400),
      curve: Curves.easeInOut,
    );
    context.read<OnboardingViewModel>().setCurrentStep(page);
  }

  void _nextPage() {
    final vm = context.read<OnboardingViewModel>();
    if (vm.currentStep < OnboardingViewModel.totalSteps - 1) {
      _goToPage(vm.currentStep + 1);
    }
  }

  void _prevPage() {
    final vm = context.read<OnboardingViewModel>();
    if (vm.currentStep > 0) {
      _goToPage(vm.currentStep - 1);
    }
  }

  Future<void> _submit() async {
    final vm = context.read<OnboardingViewModel>();
    final success = await vm.submitOnboarding();
    if (!mounted) return;
    if (success) {
      Navigator.of(context).pushNamedAndRemoveUntil(
        '/onboarding/complete',
        (route) => false,
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(vm.error ?? 'Something went wrong'),
          backgroundColor: AppColors.error,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<OnboardingViewModel>(
      builder: (context, vm, _) {
        if (vm.isLoading && vm.rsqQuestions.isEmpty) {
          return Scaffold(
            backgroundColor: AppColors.creamWhite,
            body: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  CircularProgressIndicator(
                    color: AppColors.warmCoral,
                    strokeWidth: 2.5,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Preparing your experience...',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: AppColors.softCharcoal.withValues(alpha: 0.6),
                        ),
                  ),
                ],
              ),
            ),
          );
        }

        return Scaffold(
          backgroundColor: AppColors.creamWhite,
          appBar: AppBar(
            backgroundColor: Colors.transparent,
            elevation: 0,
            leading: vm.currentStep > 0
                ? IconButton(
                    icon: const Icon(Icons.arrow_back_ios_new_rounded,
                        size: 20),
                    color: AppColors.softCharcoal,
                    onPressed: _prevPage,
                  )
                : null,
            title: Text(
              _stepTitle(vm.currentStep),
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            centerTitle: true,
            actions: [
              Padding(
                padding: const EdgeInsets.only(right: 16),
                child: Center(
                  child: Text(
                    '${vm.currentStep + 1}/${OnboardingViewModel.totalSteps}',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          fontWeight: FontWeight.w600,
                          color: AppColors.warmCoral,
                        ),
                  ),
                ),
              ),
            ],
          ),
          body: Column(
            children: [
              // Progress bar
              _ProgressBar(
                current: vm.currentStep,
                total: OnboardingViewModel.totalSteps,
              ),

              // Page content
              Expanded(
                child: PageView(
                  controller: _pageController,
                  physics: const NeverScrollableScrollPhysics(),
                  onPageChanged: (page) => vm.setCurrentStep(page),
                  children: [
                    RsqScreen(onNext: _nextPage),
                    RelationshipContextScreen(onNext: _nextPage),
                    CulturalContextScreen(onNext: _nextPage),
                    CommunicationQuizScreen(onSubmit: _submit),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  String _stepTitle(int step) {
    switch (step) {
      case 0:
        return 'Attachment Style';
      case 1:
        return 'Your Relationship';
      case 2:
        return 'Cultural Context';
      case 3:
        return 'Communication Style';
      default:
        return '';
    }
  }
}

class _ProgressBar extends StatelessWidget {
  final int current;
  final int total;

  const _ProgressBar({required this.current, required this.total});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
      child: Row(
        children: List.generate(total, (index) {
          final isActive = index <= current;
          return Expanded(
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              height: 4,
              margin: EdgeInsets.only(right: index < total - 1 ? 6 : 0),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(2),
                gradient: isActive
                    ? const LinearGradient(
                        colors: [AppColors.warmCoral, AppColors.softRose],
                      )
                    : null,
                color: isActive ? null : AppColors.softCharcoal.withValues(alpha: 0.12),
              ),
            ),
          );
        }),
      ),
    );
  }
}
