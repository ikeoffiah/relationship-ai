import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/features/engagement/engagement_models.dart';
import 'package:mobile/features/engagement/engagement_viewmodel.dart';
import 'package:mobile/features/home/views/today_hero.dart';

/// Every Today state should occupy the same width.
///
/// Two of the four wrap their card in a Column, and Column defaults to
/// CrossAxisAlignment.center — which sizes children to their intrinsic width
/// and centres them. So "Done for today" and "You're in" rendered as a narrow
/// card floating in the middle of a screen where every other card ran edge to
/// edge, while the reveal and unanswered states — which return an AppCard
/// directly — looked correct.
///
/// The old test asserted the card was *present*, which it always was. Presence
/// is the easy half; a layout bug is invisible to a finder and obvious to
/// anyone holding the phone.
class _StubEngagementViewModel extends EngagementViewModel {
  _StubEngagementViewModel(this._question);

  final DailyQuestionState _question;

  @override
  DailyQuestionState get question => _question;

  // Never completes against no API, which would hang pumpAndSettle.
  @override
  Future<void> loadRitual() async {}
}

void main() {
  // Deliberately wider than the content. At phone width the longest line in
  // these cards very nearly fills the row, so a shrink-wrapped card measures
  // the same as a stretched one and the bug is invisible to a test — which is
  // how it survived review and got noticed on a real device instead. At 1000
  // the difference is 474px against 968px.
  //
  // Stretch is a layout rule, not a width, so proving it holds here proves it
  // holds everywhere.
  const screenWidth = 1000.0;
  const horizontalPadding = 16.0;

  Future<double> widthOfHero(
    WidgetTester tester,
    DailyQuestionState question,
    Key cardKey,
  ) async {
    tester.view.physicalSize = const Size(screenWidth, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Padding(
            padding: const EdgeInsets.symmetric(horizontal: horizontalPadding),
            child: TodayHero(
              vm: _StubEngagementViewModel(question),
              onElsewhere: () {},
            ),
          ),
        ),
      ),
    );
    await tester.pump();
    return tester.getSize(find.byKey(cardKey)).width;
  }

  const available = screenWidth - (horizontalPadding * 2);

  testWidgets('the done card fills the width it is given', (tester) async {
    final width = await widthOfHero(
      tester,
      const DailyQuestionState(),
      const Key('today_done'),
    );
    expect(width, available);
  });

  testWidgets('the waiting card fills the width it is given', (tester) async {
    final width = await widthOfHero(
      tester,
      const DailyQuestionState(
        promptText: 'What made you laugh today?',
        iAnswered: true,
        partnerAnswered: false,
        hasPartner: true,
        partnerName: 'Sam',
      ),
      const Key('today_waiting'),
    );
    expect(width, available);
  });

  testWidgets('the unanswered card fills the width it is given', (tester) async {
    // The state that was already correct — pinned so a later refactor cannot
    // regress it in the same way the other two were wrong.
    final width = await widthOfHero(
      tester,
      const DailyQuestionState(promptText: 'What made you laugh today?'),
      const Key('today_question'),
    );
    expect(width, available);
  });

  testWidgets('every state agrees on width', (tester) async {
    // The property that actually matters. A card being narrower than its
    // neighbours is only noticeable next to them.
    final done = await widthOfHero(
      tester,
      const DailyQuestionState(),
      const Key('today_done'),
    );
    final unanswered = await widthOfHero(
      tester,
      const DailyQuestionState(promptText: 'anything'),
      const Key('today_question'),
    );
    expect(done, unanswered);
  });
}
