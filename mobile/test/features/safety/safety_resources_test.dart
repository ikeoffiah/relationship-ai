import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/safety/safety_resources_screen.dart';
import 'package:mobile/features/safety/safety_resources_data.dart';
import 'package:mobile/shared/widgets/get_help_now_button.dart';

void main() {
  group('SafetyResourcesScreen Tests', () {
    testWidgets('Screen loads fully offline and displays resources', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: SafetyResourcesScreen(),
        ),
      );

      // Verify the app bar title
      expect(find.text('Get Help Now'), findsOneWidget);

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

    testWidgets('GetHelpNowButton uses deep red color and triggers navigation', (WidgetTester tester) async {
      bool navigated = false;

      await tester.pumpWidget(
        MaterialApp(
          routes: {
            '/': (context) => Scaffold(body: const GetHelpNowButton()),
            '/safety': (context) {
              navigated = true;
              return const Scaffold(body: Text('Safety Screen'));
            },
          },
        ),
      );

      final containerFinder = find.byType(Container);
      expect(containerFinder, findsOneWidget);
      
      final container = tester.widget<Container>(containerFinder);
      expect(container.color, const Color(0xFFB71C1C));

      await tester.tap(find.text('Get Help Now'));
      await tester.pumpAndSettle();

      expect(navigated, isTrue);
    });
  });
}
