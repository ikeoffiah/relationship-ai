import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/chat/models/chat_models.dart';
import 'package:mobile/features/chat/widgets/assistant_message_bubble.dart';
import 'package:mobile/features/chat/widgets/message_list.dart';

void main() {
  testWidgets('MessageList threads the message id into onRejectReframe',
      (WidgetTester tester) async {
    const assistant = ChatMessage(
      id: 'assistant-42',
      text: 'Original message',
      isUser: false,
      reframe: NVCReframe(
        reframed: 'Reframed message',
        original: 'Original message',
        confidence: 0.9,
      ),
    );

    String? gotId;
    String? gotCorrection;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: MessageList(
            controller: ScrollController(),
            messages: const [
              ChatMessage(id: 'u1', text: 'hi', isUser: true),
              assistant,
            ],
            onRejectReframe: (messageId, correction) {
              gotId = messageId;
              gotCorrection = correction;
            },
          ),
        ),
      ),
    );

    // The bubble only carries the correction text; simulate its reject callback
    // and confirm MessageList supplied THIS message's id to the parent.
    final bubble = tester.widget<AssistantMessageBubble>(
      find.byType(AssistantMessageBubble),
    );
    bubble.onRejectReframe('I meant it more gently');

    expect(gotId, 'assistant-42');
    expect(gotCorrection, 'I meant it more gently');
  });
}
