/// The insights card, and mostly the state where it renders nothing.
///
/// Empty is the ordinary answer — most couples have no recurring theme and no
/// perception gap — so the test that matters most is that an empty list
/// produces no card, no heading and no placeholder. A weekly "we looked and
/// found nothing" is a worse product than silence.
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/features/home/views/insights_card.dart';
import 'package:mobile/features/relationship/relationship_insight.dart';

Future<void> pumpCard(WidgetTester tester, List<RelationshipInsight> insights) =>
    tester.pumpWidget(
      MaterialApp(home: Scaffold(body: InsightsCard(insights: insights))),
    );

RelationshipInsight insight({
  String id = 'i1',
  InsightKind kind = InsightKind.recurringTheme,
  String theme = 'how evenings get decided',
}) => RelationshipInsight(id: id, kind: kind, theme: theme, confidence: 0.9);

void main() {
  group('nothing to say', () {
    testWidgets('an empty list renders no card at all', (tester) async {
      await pumpCard(tester, const []);
      expect(find.byKey(const Key('insights_card')), findsNothing);
      expect(find.textContaining('noticed'), findsNothing);
    });

    testWidgets('an insight with a blank shape is not a card', (tester) async {
      await pumpCard(tester, [insight(theme: '   ')]);
      expect(find.byKey(const Key('insights_card')), findsNothing);
    });
  });

  group('showing one', () {
    testWidgets('a recurring theme reads as an observation', (tester) async {
      await pumpCard(tester, [insight()]);

      expect(find.byKey(const Key('insights_card')), findsOneWidget);
      expect(
        find.textContaining('how evenings get decided'),
        findsOneWidget,
      );
    });

    testWidgets('a perception gap never says who felt worse', (tester) async {
      /// The property the server detector is built around, asserted again at
      /// the surface that renders it. Each partner knows their own check-in
      /// score, so any word about direction hands them the other's private
      /// answer by subtraction.
      await pumpCard(tester, [
        insight(
          kind: InsightKind.perceptionGap,
          theme: 'how connected these last few weeks have felt',
        ),
      ]);

      final rendered = tester
          .widgetList<Text>(find.byType(Text))
          .map((t) => t.data ?? '')
          .join(' ')
          .toLowerCase();

      for (final forbidden in [
        'higher',
        'lower',
        'more than',
        'less than',
        'better',
        'worse',
        'than you',
        'than your partner',
      ]) {
        expect(
          rendered.contains(forbidden),
          isFalse,
          reason: 'the card leaked direction: "$forbidden"',
        );
      }
    });
  });

  group('showing several', () {
    testWidgets('both detectors can appear at once', (tester) async {
      await pumpCard(tester, [
        insight(id: 'a'),
        insight(
          id: 'b',
          kind: InsightKind.perceptionGap,
          theme: 'how connected these last few weeks have felt',
        ),
      ]);

      expect(find.byKey(const Key('insight_a')), findsOneWidget);
      expect(find.byKey(const Key('insight_b')), findsOneWidget);
    });

    testWidgets('the list is capped rather than growing without limit', (
      tester,
    ) async {
      await pumpCard(tester, [
        for (var i = 0; i < 6; i++) insight(id: 'i$i'),
      ]);

      expect(find.byKey(const Key('insight_i0')), findsOneWidget);
      expect(find.byKey(const Key('insight_i1')), findsOneWidget);
      expect(find.byKey(const Key('insight_i2')), findsNothing);
    });
  });

  group('parsing', () {
    test('an unknown type is rendered rather than dropped', () {
      final parsed = RelationshipInsight.fromJson({
        'id': 'x',
        'type': 'something_new',
        'theme': 'a shape',
        'confidence': 0.7,
      });
      expect(parsed.kind, InsightKind.other);
      expect(parsed.isPresentable, isTrue);
    });

    test('the private halves are not fields on the client model', () {
      /// They exist on the server model and stay behind the consent flow. If
      /// they ever arrive, nothing here should be ready to render them.
      final parsed = RelationshipInsight.fromJson({
        'id': 'x',
        'type': 'perception_gap',
        'theme': 'a shape',
        'confidence': 0.7,
        'a_narrative_summary': 'what Alex said alone',
        'synthesis': 'they remember it differently',
      });
      expect(parsed.theme, 'a shape');
      expect(
        parsed.toString().contains('Alex'),
        isFalse,
        reason: 'a private half reached the client model',
      );
    });
  });
}
