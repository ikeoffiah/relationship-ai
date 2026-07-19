import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/onboarding/onboarding_viewmodel.dart';

/// RSQ (Relationship Style Questionnaire) screen – 30 Likert items.
class RsqScreen extends StatelessWidget {
  final VoidCallback onNext;

  const RsqScreen({required this.onNext, super.key});

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<OnboardingViewModel>();
    final questions = vm.rsqQuestions;

    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: ListView.separated(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                itemCount: questions.length,
                separatorBuilder: (_, _) => const Divider(height: 1, color: Colors.transparent),
                itemBuilder: (context, index) {
                  final q = questions[index];
                  final qId = q['id'].toString();
                  final text = q['text'] as String? ?? '';
                  final selected = vm.rsqResponses[qId] ?? 3;
                  return Card(
                    elevation: 0,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                    color: AppColors.softRose.withValues(alpha: 0.15),
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            text,
                            style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.softCharcoal),
                          ),
                          const SizedBox(height: 8),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                            children: List.generate(5, (i) => i + 1).map((value) {
                              return ChoiceChip(
                                label: Text(value.toString()),
                                selected: selected == value,
                                onSelected: (_) => vm.setRsqResponse(int.parse(qId), value),
                                selectedColor: AppColors.warmCoral,
                                backgroundColor: AppColors.softRose,
                                labelStyle: Theme.of(context).textTheme.bodySmall?.copyWith(
                                  color: selected == value ? Colors.white : AppColors.softCharcoal,
                                ),
                              );
                            }).toList(),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              child: ElevatedButton(
                onPressed: vm.isRsqComplete ? onNext : null,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.warmCoral,
                  disabledBackgroundColor: AppColors.warmCoral.withValues(alpha: 0.4),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
                child: Text(
                  'Continue',
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: Colors.white),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
