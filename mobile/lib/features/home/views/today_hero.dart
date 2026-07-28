import 'package:flutter/material.dart';

import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_dimens.dart';
import 'package:mobile/features/engagement/engagement_models.dart';
import 'package:mobile/features/engagement/engagement_viewmodel.dart';
import 'package:mobile/shared/widgets/app_card.dart';

/// The one thing today.
///
/// Home used to be five static cards that looked identical every morning, so
/// it could not answer the only question a dashboard exists to answer: *is
/// there anything here for me today?* This resolves to exactly one hero, and —
/// the part that matters — the action happens **here** rather than one screen
/// away.
///
/// The order is deliberate. The reveal outranks everything, because it is what
/// the couple actually came for. "Waiting on your partner" never stands alone,
/// because a dead end is the fastest way to stop opening an app.
enum TodayState { reveal, unanswered, waiting, done }

TodayState resolveTodayState(DailyQuestionState q) {
  if (q.iAnswered && q.partnerAnswered) return TodayState.reveal;
  if (!q.iAnswered && q.promptText != null) return TodayState.unanswered;
  if (q.iAnswered && q.hasPartner && !q.partnerAnswered) return TodayState.waiting;
  return TodayState.done;
}

class TodayHero extends StatefulWidget {
  final EngagementViewModel vm;

  /// Where "something else" leads when the day is done or they are waiting.
  final VoidCallback onElsewhere;

  const TodayHero({required this.vm, required this.onElsewhere, super.key});

  @override
  State<TodayHero> createState() => _TodayHeroState();
}

class _TodayHeroState extends State<TodayHero> {
  final _answer = TextEditingController();
  bool _submitting = false;

  @override
  void dispose() {
    _answer.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final text = _answer.text.trim();
    if (text.isEmpty || _submitting) return;
    setState(() => _submitting = true);
    await widget.vm.answerQuestion(text);
    if (!mounted) return;
    _answer.clear();
    setState(() => _submitting = false);
  }

  Widget _eyebrow(String text, Color color) => Text(
    text.toUpperCase(),
    style: Theme.of(
      context,
    ).textTheme.labelMedium?.copyWith(color: color, fontSize: 11),
  );

  @override
  Widget build(BuildContext context) {
    final q = widget.vm.question;
    switch (resolveTodayState(q)) {
      case TodayState.reveal:
        return AppCard(
          key: const Key('today_reveal'),
          onTap: () => Navigator.of(context).pushNamed('/engagement/daily'),
          borderColor: AppColors.goldDark.withValues(alpha: 0.5),
          child: _body(
            'Ready',
            AppColors.goldDark,
            'You both answered.',
            'See what ${q.partnerName ?? 'your partner'} said.',
          ),
        );

      case TodayState.unanswered:
        return AppCard(
          key: const Key('today_question'),
          borderColor: AppColors.warmCoral.withValues(alpha: 0.45),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _eyebrow("Today's question", AppColors.warmCoral),
              const SizedBox(height: AppSpacing.sm),
              Text(
                q.promptText ?? '',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: AppSpacing.md),
              TextField(
                controller: _answer,
                minLines: 2,
                maxLines: 4,
                textCapitalization: TextCapitalization.sentences,
                decoration: InputDecoration(
                  hintText: 'Answer privately…',
                  filled: true,
                  fillColor: AppColors.creamWhite,
                  contentPadding: const EdgeInsets.all(AppSpacing.md),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(AppRadii.md),
                    borderSide: BorderSide(
                      color: AppColors.softCharcoal.withValues(alpha: 0.12),
                    ),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(AppRadii.md),
                    borderSide: const BorderSide(color: AppColors.warmCoral),
                  ),
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  key: const Key('today_answer_button'),
                  onPressed: _submitting ? null : _submit,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.warmCoral,
                    foregroundColor: Colors.white,
                    elevation: 0,
                    padding: const EdgeInsets.symmetric(vertical: AppSpacing.lg),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppRadii.lg),
                    ),
                  ),
                  child: Text(_submitting ? 'Sending…' : 'Answer'),
                ),
              ),
            ],
          ),
        );

      case TodayState.waiting:
        return Column(
          children: [
            AppCard(
              key: const Key('today_waiting'),
              child: _body(
                "You're in",
                AppColors.calmTeal,
                "${q.partnerName ?? 'Your partner'} hasn't answered yet.",
                "You'll both see them the moment they do.",
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            _elsewhere('While you wait', 'Something light to do on your own.'),
          ],
        );

      case TodayState.done:
        return Column(
          children: [
            AppCard(
              key: const Key('today_done'),
              child: _body(
                'Done for today',
                AppColors.sageGreen,
                "That's everything.",
                'Nothing else is asked of you today.',
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            _elsewhere("If you'd like", 'Something to do together.'),
          ],
        );
    }
  }

  Widget _body(String eyebrow, Color color, String title, String blurb) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _eyebrow(eyebrow, color),
        const SizedBox(height: AppSpacing.sm),
        Text(title, style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: AppSpacing.xs),
        Text(blurb, style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }

  Widget _elsewhere(String eyebrow, String blurb) {
    return AppCard(
      onTap: widget.onElsewhere,
      borderColor: AppColors.calmTeal.withValues(alpha: 0.35),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _eyebrow(eyebrow, AppColors.calmTeal),
                const SizedBox(height: AppSpacing.xs),
                Text(blurb, style: Theme.of(context).textTheme.bodyMedium),
              ],
            ),
          ),
          Icon(
            Icons.chevron_right_rounded,
            color: AppColors.softCharcoal.withValues(alpha: 0.35),
          ),
        ],
      ),
    );
  }
}

/// The connection check-in, inline so logging one is a single tap. It used to
/// require opening another screen first.
class TodayCheckIn extends StatelessWidget {
  final EngagementViewModel vm;

  const TodayCheckIn({required this.vm, super.key});

  @override
  Widget build(BuildContext context) {
    if (vm.summary.didCheckIn) {
      return AppCard(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Row(
          children: [
            const Icon(
              Icons.check_circle_rounded,
              size: 18,
              color: AppColors.sageGreen,
            ),
            const SizedBox(width: AppSpacing.sm),
            Text(
              'Checked in today',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      );
    }

    const faces = ['😞', '😕', '😐', '🙂', '😍'];
    return AppCard(
      key: const Key('today_checkin'),
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'How connected do you feel today?',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: AppSpacing.md),
          Row(
            children: [
              for (var i = 0; i < faces.length; i++)
                Expanded(
                  child: InkWell(
                    key: Key('checkin_${i + 1}'),
                    borderRadius: BorderRadius.circular(AppRadii.sm),
                    onTap: () => vm.checkIn(score: i + 1),
                    child: Container(
                      margin: const EdgeInsets.symmetric(horizontal: 2),
                      padding: const EdgeInsets.symmetric(
                        vertical: AppSpacing.sm,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.softRose.withValues(alpha: 0.16),
                        borderRadius: BorderRadius.circular(AppRadii.sm),
                      ),
                      child: Text(
                        faces[i],
                        textAlign: TextAlign.center,
                        style: const TextStyle(fontSize: 22),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
