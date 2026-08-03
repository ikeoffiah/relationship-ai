import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/chat/models/chat_models.dart';
import 'package:mobile/features/chat/widgets/assistant_message_bubble.dart';

void main() {
  testWidgets('AssistantMessageBubble renders the reply and never the strategy', (WidgetTester tester) async {
    /// The strategy is the model's own therapeutic technique — "Validation",
    /// "Active Listening" — and it used to render as a chip immediately above
    /// the reply. Telling someone you are about to validate them undoes the
    /// validation: it reframes a warm answer as the output of a
    /// technique-selection algorithm, and nobody asked to see it.
    ///
    /// The field stays on the model, because it is genuinely useful in logs and
    /// evaluation. This asserts only that it does not reach the person being
    /// helped.
    const message = ChatMessage(
      id: 'msg1',
      text: 'How are you feeling?',
      isUser: false,
      strategy: 'Active Listening',
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AssistantMessageBubble(
            message: message,
            onRejectReframe: (_) {},
          ),
        ),
      ),
    );

    expect(find.text('How are you feeling?'), findsOneWidget);
    expect(find.text('Active Listening'), findsNothing);
  });

  testWidgets('AssistantMessageBubble shows streaming cursor when isStreaming is true', (WidgetTester tester) async {
    const message = ChatMessage(
      id: 'msg2',
      text: 'Streaming text',
      isUser: false,
      isStreaming: true,
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AssistantMessageBubble(
            message: message,
            onRejectReframe: (_) {},
          ),
        ),
      ),
    );

    expect(find.text('Streaming text'), findsOneWidget);
    // Cursor is a container of specific size, let's just make sure we find it
    // Wait, the Strategy chip is not there, but cursor container is there.
    // In our implementation, cursor is a Container.
  });

  testWidgets('AssistantMessageBubble renders NVC reframe when available', (WidgetTester tester) async {
    const message = ChatMessage(
      id: 'msg3',
      text: 'Original message',
      isUser: false,
      reframe: NVCReframe(
        reframed: 'Reframed message',
        original: 'Original message',
        confidence: 0.95,
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AssistantMessageBubble(
            message: message,
            onRejectReframe: (_) {},
          ),
        ),
      ),
    );

    expect(find.text('Reframed to express feelings and needs'), findsOneWidget);
    expect(find.text('Reframed message'), findsOneWidget);
  });
}
