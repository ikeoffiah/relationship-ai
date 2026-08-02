/// The three shapes of the connection score.
///
/// The card is built around `emphasis` rather than around `score`, and these
/// tests are mostly about the state where it renders *nothing* — the one that
/// is easiest to lose in a refactor and the one the design most depends on. A
/// couple who joined on Tuesday, or who have gone quiet, must not be shown a
/// number, because any number reads as a verdict to somebody already anxious.
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/features/home/views/connection_score_card.dart';
import 'package:mobile/features/relationship/connection_score.dart';

Future<void> pumpCard(
  WidgetTester tester,
  ConnectionScore score, {
  VoidCallback? onOpenChat,
}) => tester.pumpWidget(
  MaterialApp(
    home: Scaffold(
      body: ConnectionScoreCard(score: score, onOpenChat: onOpenChat),
    ),
  ),
);

void main() {
  group('hidden', () {
    testWidgets('a new couple is shown nothing at all', (tester) async {
      await pumpCard(tester, const ConnectionScore());

      expect(find.byKey(const Key('connection_score_value')), findsNothing);
      expect(find.textContaining('/100'), findsNothing);
    });

    testWidgets('and no placeholder either', (tester) async {
      // "—/100" reads as a zero to anyone already anxious about it.
      await pumpCard(tester, const ConnectionScore());
      expect(find.textContaining('—'), findsNothing);
    });

    testWidgets('a failed request looks like hidden, not like a collapse', (
      tester,
    ) async {
      await pumpCard(tester, ConnectionScore.unknown);
      expect(find.byKey(const Key('connection_score_value')), findsNothing);
    });

    testWidgets('an emphasis of quiet with no number still shows nothing', (
      tester,
    ) async {
      await pumpCard(
        tester,
        const ConnectionScore(emphasis: ScoreEmphasis.quiet),
      );
      expect(find.byKey(const Key('connection_score_quiet')), findsNothing);
    });
  });

  group('quiet', () {
    const low = ConnectionScore(score: 38, emphasis: ScoreEmphasis.quiet);

    testWidgets('leads with the offer, not the mark', (tester) async {
      await pumpCard(tester, low, onOpenChat: () {});

      expect(find.byKey(const Key('connection_score_quiet')), findsOneWidget);
      expect(find.textContaining('quieter stretch'), findsOneWidget);
      expect(find.text('38/100'), findsOneWidget);
    });

    testWidgets('offers somewhere to go', (tester) async {
      var opened = false;
      await pumpCard(tester, low, onOpenChat: () => opened = true);

      await tester.tap(find.byKey(const Key('connection_score_open_chat')));
      expect(opened, isTrue);
    });

    testWidgets('and copes without one', (tester) async {
      await pumpCard(tester, low);
      expect(find.byKey(const Key('connection_score_open_chat')), findsNothing);
      expect(find.text('38/100'), findsOneWidget);
    });

    testWidgets('does not use the feature layout', (tester) async {
      await pumpCard(tester, low);
      expect(find.byKey(const Key('connection_score_feature')), findsNothing);
    });
  });

  group('feature', () {
    testWidgets('the number leads', (tester) async {
      await pumpCard(
        tester,
        const ConnectionScore(score: 72, emphasis: ScoreEmphasis.feature),
      );

      expect(find.byKey(const Key('connection_score_feature')), findsOneWidget);
      expect(find.text('72'), findsOneWidget);
      expect(find.text('/100'), findsOneWidget);
    });

    testWidgets('a fall is said plainly', (tester) async {
      await pumpCard(
        tester,
        const ConnectionScore(
          score: 61,
          emphasis: ScoreEmphasis.feature,
          direction: ScoreDirection.down,
        ),
      );
      expect(find.text('down on last week'), findsOneWidget);
    });

    testWidgets('no trend is shown before there is a second week', (
      tester,
    ) async {
      // Weekly, never daily — so a couple's first week has nothing to compare
      // against, and inventing "steady" would be inventing a reading.
      await pumpCard(
        tester,
        const ConnectionScore(score: 61, emphasis: ScoreEmphasis.feature),
      );
      expect(find.byKey(const Key('connection_score_trend')), findsNothing);
    });
  });

  group('parsing', () {
    test('the server decides the emphasis, not the number', () {
      final parsed = ConnectionScore.fromJson({
        'score': 30,
        'emphasis': 'feature',
        'direction': 'up',
        'series': [
          {'week': '2026-W29', 'value': 20},
          {'week': '2026-W30', 'value': 30},
        ],
      });

      expect(parsed.emphasis, ScoreEmphasis.feature);
      expect(parsed.direction, ScoreDirection.up);
      expect(parsed.series, [20, 30]);
    });

    test('a null score is hidden however the rest reads', () {
      final parsed = ConnectionScore.fromJson({
        'score': null,
        'emphasis': 'hidden',
        'direction': null,
        'series': [],
      });

      expect(parsed.isVisible, isFalse);
    });

    test('an unrecognised emphasis falls back to hidden', () {
      final parsed = ConnectionScore.fromJson({'score': 50, 'emphasis': 'loud'});
      expect(parsed.emphasis, ScoreEmphasis.hidden);
      expect(parsed.isVisible, isFalse);
    });
  });
}
