import 'package:flutter/material.dart';
import 'package:mobile/features/chat/models/chat_models.dart';
import 'package:mobile/features/chat/widgets/nvc_reframe_card.dart';

class AnimatedTextDisplay extends StatefulWidget {
  final String text;
  final bool isStreaming;

  const AnimatedTextDisplay({super.key, required this.text, this.isStreaming = false});

  @override
  State<AnimatedTextDisplay> createState() => _AnimatedTextDisplayState();
}

class _AnimatedTextDisplayState extends State<AnimatedTextDisplay> {
  @override
  Widget build(BuildContext context) {
    // For MVP, just render the text directly since Flutter Text handles fast updates well.
    // In a production app, we might want custom animation logic for the incoming tokens.
    return Text(
      widget.text,
      style: const TextStyle(fontSize: 16),
    );
  }
}

class _StreamingCursor extends StatelessWidget {
  const _StreamingCursor();

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(left: 4, top: 4),
      width: 8,
      height: 16,
      color: Colors.blue.withValues(alpha: 0.6),
    );
  }
}

class _StrategyChip extends StatelessWidget {
  final String strategy;

  const _StrategyChip({required this.strategy});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.purple.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.purple.shade100),
      ),
      child: Text(
        strategy,
        style: TextStyle(fontSize: 10, color: Colors.purple.shade700, fontWeight: FontWeight.w600),
      ),
    );
  }
}

class AssistantMessageBubble extends StatelessWidget {
  final ChatMessage message;
  final ValueChanged<String> onRejectReframe;

  const AssistantMessageBubble({
    super.key,
    required this.message,
    required this.onRejectReframe,
  });

  @override
  Widget build(BuildContext context) {
    final showStrategy = message.strategy != null; // Feature flag could wrap this

    return Align(
      alignment: Alignment.centerLeft,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (showStrategy) _StrategyChip(strategy: message.strategy!),
            Container(
              constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: message.isSafetyMessage
                    ? Colors.amber.shade50
                    : Theme.of(context).colorScheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(16).copyWith(topLeft: const Radius.circular(4)),
                border: message.isSafetyMessage
                    ? Border.all(color: Colors.amber.shade300, width: 1.5)
                    : null,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  AnimatedTextDisplay(
                    text: message.text,
                    isStreaming: message.isStreaming,
                  ),
                  if (message.isStreaming) const _StreamingCursor(),
                ],
              ),
            ),
            if (message.reframe != null)
              NVCReframeCard(
                reframe: message.reframe!,
                onReject: onRejectReframe,
              ),
          ],
        ),
      ),
    );
  }
}
