/// What Bliss has noticed about the pair — or, almost always, nothing.
///
/// Empty is the ordinary state and this widget renders nothing at all for it:
/// no "no insights yet", no empty illustration, no placeholder. Most couples
/// have no recurring theme and no perception gap, the detectors are built to
/// say so, and a card announcing that we looked and found nothing would turn
/// an honest silence into a weekly reminder of being assessed.
///
/// An insight is heavier than the score beside it. The score is a number about
/// a fortnight; an insight is a claim about how two people are getting on, and
/// the couple did not ask for it. So it is worded as an observation rather than
/// a diagnosis, and it never carries an action — "here is what you should do
/// about it" is a therapist's job and this is not one.
library;

import 'package:flutter/material.dart';

import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/relationship/relationship_insight.dart';
import 'package:mobile/shared/widgets/app_card.dart';

class InsightsCard extends StatelessWidget {
  const InsightsCard({super.key, required this.insights});

  final List<RelationshipInsight> insights;

  /// At most this many. There are only two detectors today, but a home screen
  /// that can grow an unbounded list of things we have noticed about you is a
  /// different and worse product than one that surfaces the odd observation.
  static const _maxShown = 2;

  @override
  Widget build(BuildContext context) {
    final shown = insights.where((i) => i.isPresentable).take(_maxShown).toList();
    if (shown.isEmpty) return const SizedBox.shrink();

    return AppCard(
      key: const Key('insights_card'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.lightbulb_outline_rounded,
                size: 16,
                color: AppColors.warmCoral.withValues(alpha: 0.8),
              ),
              const SizedBox(width: 6),
              Text(
                'Something we noticed',
                style: Theme.of(context).textTheme.titleSmall,
              ),
            ],
          ),
          const SizedBox(height: 10),
          for (final insight in shown) ...[
            _InsightLine(insight: insight),
            if (insight != shown.last) const SizedBox(height: 12),
          ],
        ],
      ),
    );
  }
}

class _InsightLine extends StatelessWidget {
  const _InsightLine({required this.insight});

  final RelationshipInsight insight;

  /// The framing sentence around the server's shape.
  ///
  /// Kept here rather than on the server because it is presentation, and kept
  /// deliberately flat: no "you two really need to talk about…", no severity,
  /// no count. The shape itself carries the finding.
  String get _sentence => switch (insight.kind) {
    InsightKind.recurringTheme =>
      'The same disagreement has come back a few times — ${insight.theme}.',
    // Direction is absent from the payload on purpose and must not be implied
    // here either. "One of you has been finding it harder" would hand each
    // partner the other's private check-in score by subtraction.
    InsightKind.perceptionGap =>
      'You have been seeing ${insight.theme} differently.',
    InsightKind.other => insight.theme,
  };

  @override
  Widget build(BuildContext context) {
    return Text(
      _sentence,
      key: Key('insight_${insight.id}'),
      style: TextStyle(
        fontSize: 13,
        height: 1.35,
        color: AppColors.softCharcoal.withValues(alpha: 0.75),
      ),
    );
  }
}
