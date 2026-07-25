import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/onboarding/onboarding_viewmodel.dart';
import 'package:mobile/features/home/views/main_navigation_screen.dart';

/// Completion screen shown after onboarding submission.
/// Displays computed attachment style and communication style results.
class OnboardingCompleteScreen extends StatefulWidget {
  const OnboardingCompleteScreen({super.key});

  @override
  State<OnboardingCompleteScreen> createState() =>
      _OnboardingCompleteScreenState();
}

class _OnboardingCompleteScreenState extends State<OnboardingCompleteScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnim;
  late Animation<double> _fadeAnim;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );
    _scaleAnim = CurvedAnimation(
      parent: _controller,
      curve: Curves.elasticOut,
    );
    _fadeAnim = CurvedAnimation(
      parent: _controller,
      curve: const Interval(0.3, 1.0, curve: Curves.easeIn),
    );
    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<OnboardingViewModel>();

    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Spacer(flex: 2),

              // ── Celebration icon ─────────────────────────────────
              ScaleTransition(
                scale: _scaleAnim,
                child: Container(
                  width: 100,
                  height: 100,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: const LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [AppColors.warmCoral, AppColors.softRose],
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.warmCoral.withValues(alpha: 0.3),
                        blurRadius: 30,
                        offset: const Offset(0, 10),
                      ),
                    ],
                  ),
                  child: const Icon(Icons.favorite_rounded,
                      color: Colors.white, size: 48),
                ),
              ),
              const SizedBox(height: 32),

              // ── Title ────────────────────────────────────────────
              FadeTransition(
                opacity: _fadeAnim,
                child: Text(
                  'You\'re all set!',
                  style: Theme.of(context).textTheme.displayMedium,
                  textAlign: TextAlign.center,
                ),
              ),
              const SizedBox(height: 12),
              FadeTransition(
                opacity: _fadeAnim,
                child: Text(
                  'We\'ve built a personalized experience just for you.',
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                        color:
                            AppColors.softCharcoal.withValues(alpha: 0.6),
                      ),
                  textAlign: TextAlign.center,
                ),
              ),
              const SizedBox(height: 36),

              // ── Results cards ────────────────────────────────────
              if (vm.attachmentStyle.isNotEmpty)
                FadeTransition(
                  opacity: _fadeAnim,
                  child: _ResultCard(
                    icon: '🔗',
                    title: 'Attachment Style',
                    value: _formatStyle(vm.attachmentStyle),
                    gradient: const [
                      AppColors.warmCoral,
                      AppColors.softRose,
                    ],
                  ),
                ),
              const SizedBox(height: 14),
              if (vm.communicationStyle.isNotEmpty)
                FadeTransition(
                  opacity: _fadeAnim,
                  child: _ResultCard(
                    icon: '💬',
                    title: 'Communication Style',
                    value: _formatStyle(vm.communicationStyle),
                    gradient: const [
                      AppColors.calmTeal,
                      AppColors.sageGreen,
                    ],
                  ),
                ),

              const Spacer(flex: 3),

              // ── Invite partner (primary, but skippable — solo works) ──
              // Peak intent is right here, just after the user felt seen; the
              // invite is an upgrade, not a gate.
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: AppColors.calmTeal.withValues(alpha: 0.10),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Column(
                  children: [
                    const Text('💞', style: TextStyle(fontSize: 28)),
                    const SizedBox(height: 8),
                    const Text(
                      'See how you two fit',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Invite your partner to compare answers, set shared goals, '
                      'and play your first “how well do you know each other” game.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: AppColors.softCharcoal),
                    ),
                    const SizedBox(height: 16),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: () =>
                            Navigator.of(context).pushNamed('/relationship/invite'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.calmTeal,
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(16)),
                          padding: const EdgeInsets.symmetric(vertical: 14),
                        ),
                        child: const Text(
                          'Invite my partner',
                          style: TextStyle(
                              color: Colors.white, fontWeight: FontWeight.w600),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              TextButton(
                onPressed: () {
                  Navigator.of(context).pushAndRemoveUntil(
                    MaterialPageRoute(
                      builder: (_) => const MainNavigationScreen(),
                    ),
                    (route) => false,
                  );
                },
                child: Text(
                  'Explore on my own for now',
                  style: TextStyle(
                    color: AppColors.softCharcoal.withValues(alpha: 0.7),
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }

  String _formatStyle(String raw) {
    return raw
        .replaceAll('_', ' ')
        .split(' ')
        .map((w) =>
            w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
        .join(' ');
  }
}

class _ResultCard extends StatelessWidget {
  final String icon;
  final String title;
  final String value;
  final List<Color> gradient;

  const _ResultCard({
    required this.icon,
    required this.title,
    required this.value,
    required this.gradient,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        gradient: LinearGradient(
          colors: [
            gradient[0].withValues(alpha: 0.12),
            gradient[1].withValues(alpha: 0.08),
          ],
        ),
        border: Border.all(
          color: gradient[0].withValues(alpha: 0.2),
        ),
      ),
      child: Row(
        children: [
          Text(icon, style: const TextStyle(fontSize: 28)),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppColors.softCharcoal.withValues(alpha: 0.6),
                        fontWeight: FontWeight.w600,
                      ),
                ),
                const SizedBox(height: 2),
                Text(
                  value,
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                        fontWeight: FontWeight.w700,
                        color: gradient[0],
                      ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
