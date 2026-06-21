import 'package:flutter/material.dart';
import 'package:mobile/features/chat/models/chat_models.dart';
import 'package:mobile/features/chat/widgets/assistant_message_bubble.dart';

class UserMessageBubble extends StatelessWidget {
  final ChatMessage message;

  const UserMessageBubble({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerRight,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 16.0),
        child: Container(
          constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Theme.of(context).primaryColor,
            borderRadius: BorderRadius.circular(16).copyWith(topRight: const Radius.circular(4)),
          ),
          child: Text(
            message.text,
            style: const TextStyle(color: Colors.white, fontSize: 16),
          ),
        ),
      ),
    );
  }
}

class MessageList extends StatelessWidget {
  final List<ChatMessage> messages;
  final ValueChanged<String>? onRejectReframe;
  final ScrollController controller;

  const MessageList({
    super.key,
    required this.messages,
    required this.controller,
    this.onRejectReframe,
  });

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      controller: controller,
      padding: const EdgeInsets.symmetric(vertical: 16),
      itemCount: messages.length,
      itemBuilder: (context, index) {
        final message = messages[index];
        if (message.isUser) {
          return UserMessageBubble(message: message);
        } else {
          return AssistantMessageBubble(
            message: message,
            onRejectReframe: onRejectReframe ?? (_) {},
          );
        }
      },
    );
  }
}
