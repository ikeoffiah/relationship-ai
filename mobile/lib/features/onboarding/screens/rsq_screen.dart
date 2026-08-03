import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/onboarding/onboarding_viewmodel.dart';

/// RSQ (Relationship Style Questionnaire) screen – 30 Likert items.
class RsqScreen extends StatelessWidget {
  final VoidCallback onNext;

  const RsqScreen({required this.onNext, super.key});

  /// What each point on the scale means, for the chip's own accessible label.
  static String _anchorFor(int value) => switch (value) {
    1 => 'Not like me',
    2 => 'A little like me',
    3 => 'Somewhat like me',
    4 => 'Mostly like me',
    5 => 'Very like me',
    _ => '',
  };

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<OnboardingViewModel>();
    final questions = vm.rsqQuestions;

    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      body: SafeArea(
        child: Column(
          children: [
            // Gentle context so the questionnaire doesn't feel clinical — why
            // we ask, in the same soft, muted style as the rest of onboarding.
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 16, 24, 0),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    Icons.favorite_border_rounded,
                    size: 16,
                    color: AppColors.warmCoral.withValues(alpha: 0.85),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'These reveal your attachment style — how you seek closeness '
                      'and handle distance — so Bliss can make guidance feel personal '
                      'to you. There are no right or wrong answers.',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppColors.softCharcoal.withValues(alpha: 0.6),
                        height: 1.4,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            // The scale legend, and it lives *outside* the ListView on purpose.
            //
            // Until this existed the 30 items rendered as bare chips reading
            // 1 2 3 4 5 with nothing anywhere on the screen saying which end
            // meant what. That is not only a usability defect: a user who read
            // the scale backwards produced an inverted attachment score, and
            // those scores feed prompt modifiers, micro-action selection and
            // the portrait. Silent data corruption in the one instrument the
            // personalisation rests on.
            //
            // A header inside the list would scroll away by item three and
            // leave items 4-30 exactly as ambiguous as before, so it is pinned
            // above the scroll area instead.
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 12, 24, 4),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    '1 — Not like me',
                    key: const Key('rsq_anchor_low'),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppColors.softCharcoal.withValues(alpha: 0.7),
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  Text(
                    '5 — Very like me',
                    key: const Key('rsq_anchor_high'),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppColors.softCharcoal.withValues(alpha: 0.7),
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: ListView.separated(
                padding: const EdgeInsets.symmetric(
                  horizontal: 24,
                  vertical: 16,
                ),
                itemCount: questions.length,
                separatorBuilder: (_, _) =>
                    const Divider(height: 1, color: Colors.transparent),
                itemBuilder: (context, index) {
                  final q = questions[index];
                  final qId = q['id'].toString();
                  final text = q['text'] as String? ?? '';
                  // No pre-selected default: the item stays unanswered (no chip
                  // highlighted) until the user actually taps one, so a neutral
                  // "3" is never silently submitted.
                  final int? selected = vm.rsqResponses[qId];
                  return Card(
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    color: AppColors.softRose.withValues(alpha: 0.15),
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            text,
                            style: Theme.of(context).textTheme.bodyLarge
                                ?.copyWith(color: AppColors.softCharcoal),
                          ),
                          const SizedBox(height: 8),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                            children: List.generate(5, (i) => i + 1).map((
                              value,
                            ) {
                              return ChoiceChip(
                                label: Text(value.toString()),
                                // A bare "3" tells a screen-reader user nothing
                                // at all — the legend above is not announced
                                // with the chip, so each one carries its own
                                // meaning.
                                tooltip: _anchorFor(value),
                                selected: selected == value,
                                onSelected: (_) =>
                                    vm.setRsqResponse(int.parse(qId), value),
                                selectedColor: AppColors.warmCoral,
                                backgroundColor: AppColors.softRose,
                                labelStyle: Theme.of(context)
                                    .textTheme
                                    .bodySmall
                                    ?.copyWith(
                                      color: selected == value
                                          ? Colors.white
                                          : AppColors.softCharcoal,
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
              child: SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: vm.isRsqComplete ? onNext : null,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.warmCoral,
                    disabledBackgroundColor: AppColors.warmCoral.withValues(
                      alpha: 0.4,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(24),
                    ),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                  child: Text(
                    'Continue',
                    style: Theme.of(
                      context,
                    ).textTheme.bodyLarge?.copyWith(color: Colors.white),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
