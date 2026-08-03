/// The RSQ scale has to say which end is which.
///
/// Without anchors the 30 items render as bare chips reading 1 2 3 4 5, and a
/// user who reads the scale backwards produces an inverted attachment score.
/// Those scores feed prompt modifiers, micro-action selection and the portrait,
/// so this is not a cosmetic defect — it is silent corruption of the one
/// instrument the personalisation rests on.
///
/// The legend must also survive scrolling: it is pinned outside the ListView
/// precisely so items 4-30 are not left as ambiguous as they were before.
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:mobile/features/onboarding/onboarding_viewmodel.dart';
import 'package:mobile/features/onboarding/screens/rsq_screen.dart';

Future<void> pumpRsq(WidgetTester tester) => tester.pumpWidget(
  MaterialApp(
    home: ChangeNotifierProvider(
      create: (_) => OnboardingViewModel(),
      child: RsqScreen(onNext: () {}),
    ),
  ),
);

void main() {
  testWidgets('both ends of the scale are labelled', (tester) async {
    await pumpRsq(tester);
    await tester.pump();

    expect(find.byKey(const Key('rsq_anchor_low')), findsOneWidget);
    expect(find.byKey(const Key('rsq_anchor_high')), findsOneWidget);
    expect(find.textContaining('Not like me'), findsWidgets);
    expect(find.textContaining('Very like me'), findsWidgets);
  });

  testWidgets('the legend is outside the scroll area, not a list header', (
    tester,
  ) async {
    /// A header inside the ListView would scroll away by item three. If this
    /// ever regresses to an item, the legend will be a descendant of the
    /// Scrollable and this fails.
    await pumpRsq(tester);
    await tester.pump();

    final legend = find.byKey(const Key('rsq_anchor_low'));
    expect(legend, findsOneWidget);
    expect(
      find.ancestor(of: legend, matching: find.byType(Scrollable)),
      findsNothing,
      reason: 'the legend scrolls away with the list',
    );
  });
}
