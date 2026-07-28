import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/safety/safety_resources_screen.dart';
import 'package:mobile/features/safety/safety_resources_data.dart';
import 'package:mobile/shared/widgets/support_action.dart';

void main() {
  group('SafetyResourcesScreen Tests', () {
    testWidgets('Screen loads fully offline and displays resources', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: SafetyResourcesScreen(),
        ),
      );

      // Verify the app bar title
      expect(find.text('Support'), findsOneWidget);

      // Verify all resources are present
      for (final resource in safetyResources) {
        expect(find.textContaining(resource.name), findsOneWidget);
      }

      // Verify no network calls are needed (implicit by running purely offline UI test)
    });

    testWidgets('Optional pre-pended message is rendered if passed', (WidgetTester tester) async {
      const String testMessage = 'The AI detected something in our conversation...';

      await tester.pumpWidget(
        MaterialApp(
          onGenerateRoute: (settings) {
            return MaterialPageRoute(
              settings: const RouteSettings(arguments: testMessage),
              builder: (context) => const SafetyResourcesScreen(),
            );
          },
          initialRoute: '/',
        ),
      );

      // Verify the pre-pended message is displayed
      expect(find.text(testMessage), findsOneWidget);
    });

    // The safety-critical property is reachability, not loudness: support must
    // still be exactly one tap away from anywhere it is offered. The previous
    // version of this test asserted the button was #B71C1C — it locked in the
    // alarm styling rather than the behaviour that actually matters.
    testWidgets('SupportAction is one tap from the support resources', (
      WidgetTester tester,
    ) async {
      bool navigated = false;

      await tester.pumpWidget(
        MaterialApp(
          routes: {
            '/': (context) => const Scaffold(
              body: Center(child: SupportAction()),
            ),
            '/safety': (context) {
              navigated = true;
              return const Scaffold(body: Text('Safety Screen'));
            },
          },
        ),
      );

      // Discoverable by assistive tech even though it is icon-only.
      expect(
        find.byTooltip('Support'),
        findsOneWidget,
        reason: 'support must remain findable',
      );

      await tester.tap(find.byType(SupportAction));
      await tester.pumpAndSettle();

      expect(navigated, isTrue);
    });
  });
}
