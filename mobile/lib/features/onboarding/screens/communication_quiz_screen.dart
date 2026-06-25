import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/onboarding/onboarding_viewmodel.dart';

/// Screen 4: Communication quiz — multi-choice scenarios.
class CommunicationQuizScreen extends StatelessWidget {
  final Future<void> Function() onSubmit;

  const CommunicationQuizScreen({required this.onSubmit, super.key});

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<OnboardingViewModel>();
    final questions = vm.communicationQuiz;

    return SafeArea(
      child: Column(
        children: [
          Expanded(
            child: ListView(
              padding:
                  const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              children: [
                Text(
                  'Communication quiz',
                  style: Theme.of(context).textTheme.displaySmall,
                ),
                const SizedBox(height: 6),
                Text(
                  'Choose the response that feels most natural to you in each scenario.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color:
                            AppColors.softCharcoal.withValues(alpha: 0.6),
                      ),
                ),
                const SizedBox(height: 24),
                ...questions.asMap().entries.map((entry) {
                  final index = entry.key;
                  final q = entry.value;
                  final qId = q['id'].toString();
                  final prompt = q['prompt'] as String? ?? '';
                  final options =
                      List<Map<String, dynamic>>.from(q['options'] ?? []);
                  final selected = vm.communicationQuizResponses[qId];

                  return Padding(
                    padding: const EdgeInsets.only(bottom: 24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Question number badge + prompt
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              width: 28,
                              height: 28,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                gradient: const LinearGradient(
                                  colors: [
                                    AppColors.warmCoral,
                                    AppColors.softRose,
                                  ],
                                ),
                              ),
                              alignment: Alignment.center,
                              child: Text(
                                '${index + 1}',
                                style: Theme.of(context)
                                    .textTheme
                                    .bodySmall
                                    ?.copyWith(
                                      color: Colors.white,
                                      fontWeight: FontWeight.w700,
                                    ),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                prompt,
                                style: Theme.of(context)
                                    .textTheme
                                    .bodyLarge
                                    ?.copyWith(
                                        fontWeight: FontWeight.w500),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),

                        // Options
                        ...options.map((opt) {
                          final val = opt['value']?.toString() ?? '';
                          final label =
                              opt['label'] as String? ?? '';
                          final isSelected = selected == val;

                          return Padding(
                            padding:
                                const EdgeInsets.only(bottom: 8),
                            child: GestureDetector(
                              onTap: () =>
                                  vm.setCommunicationQuizAnswer(
                                      int.parse(qId), val),
                              child: AnimatedContainer(
                                duration: const Duration(
                                    milliseconds: 200),
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 16, vertical: 12),
                                decoration: BoxDecoration(
                                  borderRadius:
                                      BorderRadius.circular(14),
                                  gradient: isSelected
                                      ? const LinearGradient(
                                          colors: [
                                              AppColors.calmTeal,
                                              AppColors.sageGreen,
                                            ])
                                      : null,
                                  color: isSelected
                                      ? null
                                      : AppColors.sageGreen
                                          .withValues(alpha: 0.12),
                                  border: Border.all(
                                    color: isSelected
                                        ? Colors.transparent
                                        : AppColors.softCharcoal
                                            .withValues(alpha: 0.08),
                                  ),
                                ),
                                child: Row(
                                  children: [
                                    Expanded(
                                      child: Text(
                                        label,
                                        style: Theme.of(context)
                                            .textTheme
                                            .bodyMedium
                                            ?.copyWith(
                                              color: isSelected
                                                  ? Colors.white
                                                  : AppColors
                                                      .softCharcoal,
                                              fontWeight: isSelected
                                                  ? FontWeight.w600
                                                  : FontWeight.w400,
                                            ),
                                      ),
                                    ),
                                    if (isSelected)
                                      const Icon(
                                          Icons
                                              .check_circle_rounded,
                                          color: Colors.white,
                                          size: 20),
                                  ],
                                ),
                              ),
                            ),
                          );
                        }),
                      ],
                    ),
                  );
                }),
              ],
            ),
          ),

          // ── Submit button ────────────────────────────────────────
          Padding(
            padding:
                const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            child: SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: vm.isLoading
                    ? null
                    : () async => await onSubmit(),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.warmCoral,
                  disabledBackgroundColor:
                      AppColors.warmCoral.withValues(alpha: 0.4),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(24)),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
                child: vm.isLoading
                    ? const SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(
                          color: Colors.white,
                          strokeWidth: 2.5,
                        ),
                      )
                    : Text(
                        'Finish & Get My Results',
                        style: Theme.of(context)
                            .textTheme
                            .bodyLarge
                            ?.copyWith(color: Colors.white),
                      ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
