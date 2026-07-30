import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/features/onboarding/screens/relationship_portrait_screen.dart';

/// One screen, two callers.
///
/// Onboarding reaches the portrait with pushNamedAndRemoveUntil, clearing the
/// stack — nothing to go back to, so no back button belongs. The You hub pushes
/// it normally and inherited the same chrome, which left someone reading their
/// own portrait with no way out of it.
///
/// The forward button was worse than the missing back one: it pushed the
/// onboarding *completion* screen and wiped the stack, so opening your portrait
/// from You dropped you into a flow you finished weeks ago.
/// Let the screen's portrait request time out.
///
/// It fetches on init against no server, which leaves Dio's connect timeout
/// pending — and a pending timer fails the test-teardown invariant rather than
/// the assertion, so it reads as an unrelated framework error. Advancing past
/// the timeout is more honest than injecting a stub client here, because these
/// tests are about which chrome the screen wears, and that is decided before
/// the future resolves either way.
Future<void> _drainPortraitFetch(WidgetTester tester) async {
  await tester.pump(const Duration(seconds: 11));
}

void main() {
  /// Pushes the portrait onto a stack, the way the You hub does.
  Future<void> pumpRevisited(WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder: (context) => Scaffold(
            body: ElevatedButton(
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => const RelationshipPortraitScreen(),
                ),
              ),
              child: const Text('open'),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('open'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    await _drainPortraitFetch(tester);
  }

  /// Replaces the stack, the way onboarding does.
  Future<void> pumpAsOnboarding(WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: RelationshipPortraitScreen()),
    );
    await tester.pump();
    await _drainPortraitFetch(tester);
  }

  testWidgets('revisiting from inside the app offers a way back', (
    tester,
  ) async {
    await pumpRevisited(tester);
    expect(find.byType(BackButton), findsOneWidget);
  });

  testWidgets('revisiting is titled so you know where you are', (tester) async {
    await pumpRevisited(tester);
    expect(find.text('Your portrait'), findsOneWidget);
  });

  testWidgets('onboarding gets no back button, because there is no back', (
    tester,
  ) async {
    // Not cosmetic: onboarding cleared the stack to get here, so a back button
    // would be an affordance that cannot work.
    await pumpAsOnboarding(tester);
    expect(find.byType(BackButton), findsNothing);
    expect(find.text('Your portrait'), findsNothing);
  });

  testWidgets('the back button actually pops', (tester) async {
    await pumpRevisited(tester);
    await tester.tap(find.byType(BackButton));
    await tester.pumpAndSettle();
    // Back on the screen that opened it.
    expect(find.text('open'), findsOneWidget);
  });
}
