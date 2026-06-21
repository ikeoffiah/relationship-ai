import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/chat/models/chat_models.dart';
import 'package:mobile/features/chat/widgets/nvc_reframe_card.dart';

void main() {
  testWidgets('NVCReframeCard toggles showing original message and sends correction', (WidgetTester tester) async {
    String? rejectedCorrection;
    const reframe = NVCReframe(
      reframed: 'I feel hurt because I need connection.',
      original: 'You never listen to me!',
      confidence: 0.9,
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: NVCReframeCard(
            reframe: reframe,
            onReject: (val) {
              rejectedCorrection = val;
            },
          ),
        ),
      ),
    );

    // Initial state: reframed text is shown, original is hidden
    expect(find.text('I feel hurt because I need connection.'), findsOneWidget);
    expect(find.text('Original: You never listen to me!'), findsNothing);

    // Tap 'Show original'
    await tester.tap(find.text('Show original'));
    await tester.pumpAndSettle();

    // Original text should be shown now
    expect(find.text('Original: You never listen to me!'), findsOneWidget);

    // Tap 'Hide original'
    await tester.tap(find.text('Hide original'));
    await tester.pumpAndSettle();

    // Original text should be hidden again
    expect(find.text('Original: You never listen to me!'), findsNothing);

    // Tap "This doesn't capture what I meant" to open correction textfield
    await tester.tap(find.text("This doesn't capture what I meant"));
    await tester.pumpAndSettle();

    // Check if TextField is visible
    expect(find.byType(TextField), findsOneWidget);

    // Enter correction
    await tester.enterText(find.byType(TextField), 'I just want us to spend some time together.');
    await tester.pumpAndSettle();

    // Tap send button
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    // Verify callback was called with correct content
    expect(rejectedCorrection, equals('I just want us to spend some time together.'));
  });
}
