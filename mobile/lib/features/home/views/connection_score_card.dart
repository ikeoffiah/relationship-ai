/// The connection score on the home screen — or not, which is half the point.
///
/// `presentation` on the server returns how prominent this should be, and this
/// widget's only real job is to honour that. Three shapes:
///
///   hidden   nothing at all. Not a placeholder, not "—/100", not a zero. A
///            couple who joined on Tuesday, or one who has gone quiet, must not
///            be shown a number, because any number reads as a verdict to
///            somebody already anxious about it.
///   quiet    the number is present and small, under a line that offers
///            something to do. The morning after a fight, a low mark is the
///            least useful thing that could be on the screen.
///   feature  the number leads.
///
/// Rendering all three the same size would undo the design, which is why this
/// is built around `emphasis` rather than around `score`.
library;

import 'package:flutter/material.dart';

import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/relationship/connection_score.dart';
import 'package:mobile/shared/widgets/app_card.dart';

class ConnectionScoreCard extends StatelessWidget {
  const ConnectionScoreCard({super.key, required this.score, this.onOpenChat});

  final ConnectionScore score;

  /// Where "quiet" sends somebody. A low week should offer the thing that
  /// helps rather than the number that grades.
  final VoidCallback? onOpenChat;

  @override
  Widget build(BuildContext context) {
    if (!score.isVisible) return const SizedBox.shrink();
    return score.emphasis == ScoreEmphasis.feature
        ? _feature(context)
        : _quiet(context);
  }

  // ── feature ─────────────────────────────────────────────────────────
  Widget _feature(BuildContext context) {
    return AppCard(
      key: const Key('connection_score_feature'),
      child: Row(
        children: [
          Text(
            '${score.score}',
            key: const Key('connection_score_value'),
            style: Theme.of(context).textTheme.displaySmall?.copyWith(
              color: AppColors.warmCoral,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(width: 4),
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              '/100',
              style: TextStyle(
                color: AppColors.softCharcoal.withValues(alpha: 0.4),
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Your connection',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const SizedBox(height: 2),
                _TrendLine(direction: score.direction),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ── quiet ───────────────────────────────────────────────────────────
  Widget _quiet(BuildContext context) {
    return AppCard(
      key: const Key('connection_score_quiet'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // The offer comes first and the number second, deliberately. This is
          // the state a couple is in on a hard week, and leading with the mark
          // would be grading them when they came looking for help.
          Text(
            'It has been a quieter stretch',
            style: Theme.of(context).textTheme.titleSmall,
          ),
          const SizedBox(height: 4),
          Text(
            'Small things count. A message now is worth more than a good week later.',
            style: TextStyle(
              fontSize: 13,
              color: AppColors.softCharcoal.withValues(alpha: 0.7),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              if (onOpenChat != null)
                TextButton(
                  key: const Key('connection_score_open_chat'),
                  onPressed: onOpenChat,
                  style: TextButton.styleFrom(
                    padding: EdgeInsets.zero,
                    minimumSize: const Size(0, 0),
                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  ),
                  child: const Text('Say something'),
                ),
              const Spacer(),
              Text(
                '${score.score}/100',
                key: const Key('connection_score_value'),
                style: TextStyle(
                  fontSize: 13,
                  color: AppColors.softCharcoal.withValues(alpha: 0.45),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _TrendLine extends StatelessWidget {
  const _TrendLine({required this.direction});

  final ScoreDirection? direction;

  @override
  Widget build(BuildContext context) {
    // No direction is the normal state for a couple's first weeks — the trend
    // is weekly, so there is nothing to compare against until there is a
    // second week. Say nothing rather than inventing "steady".
    if (direction == null) return const SizedBox.shrink();

    final (icon, label) = switch (direction!) {
      ScoreDirection.up => (Icons.trending_up_rounded, 'up on last week'),
      ScoreDirection.down => (Icons.trending_down_rounded, 'down on last week'),
      ScoreDirection.steady => (Icons.trending_flat_rounded, 'steady'),
    };

    return Row(
      key: const Key('connection_score_trend'),
      children: [
        Icon(
          icon,
          size: 14,
          color: AppColors.softCharcoal.withValues(alpha: 0.5),
        ),
        const SizedBox(width: 4),
        Flexible(
          child: Text(
            label,
            style: TextStyle(
              fontSize: 12,
              color: AppColors.softCharcoal.withValues(alpha: 0.5),
            ),
          ),
        ),
      ],
    );
  }
}
