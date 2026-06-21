import 'package:mobile/features/chat/models/chat_models.dart';

class ChatState {
  final List<ChatMessage> messages;
  final SessionState? sessionInfo;
  final String? safetyOverlayLevel;
  final List<Map>? safetyOverlayResources;
  final int turnHoldCountdown;
  final String? deEscalationPrompt;

  const ChatState({
    required this.messages,
    this.sessionInfo,
    this.safetyOverlayLevel,
    this.safetyOverlayResources,
    this.turnHoldCountdown = 0,
    this.deEscalationPrompt,
  });

  factory ChatState.initial() => const ChatState(messages: []);

  ChatState copyWith({
    List<ChatMessage>? messages,
    SessionState? sessionInfo,
    String? safetyOverlayLevel,
    List<Map>? safetyOverlayResources,
    int? turnHoldCountdown,
    String? deEscalationPrompt,
  }) {
    return ChatState(
      messages: messages ?? this.messages,
      sessionInfo: sessionInfo ?? this.sessionInfo,
      safetyOverlayLevel: safetyOverlayLevel ?? this.safetyOverlayLevel,
      safetyOverlayResources: safetyOverlayResources ?? this.safetyOverlayResources,
      turnHoldCountdown: turnHoldCountdown ?? this.turnHoldCountdown,
      deEscalationPrompt: deEscalationPrompt ?? this.deEscalationPrompt,
    );
  }

  ChatState addUserMessage(String content) {
    return copyWith(
      messages: [...messages, ChatMessage(id: DateTime.now().millisecondsSinceEpoch.toString(), text: content, isUser: true)],
    );
  }

  ChatState addStreamingMessage(String id) {
    return copyWith(
      messages: [...messages, ChatMessage(id: id, text: '', isUser: false, isStreaming: true)],
    );
  }

  ChatState appendToken(String id, String content) {
    return copyWith(
      messages: messages.map((m) {
        if (m.id == id) {
          return m.copyWith(text: m.text + content);
        }
        return m;
      }).toList(),
    );
  }

  ChatState updateStrategy(String strategy) {
    if (messages.isEmpty) return this;
    final lastMsg = messages.last;
    if (lastMsg.isUser) return this;

    return copyWith(
      messages: messages.map((m) {
        if (m.id == lastMsg.id) {
          return m.copyWith(strategy: strategy);
        }
        return m;
      }).toList(),
    );
  }

  ChatState showSafetyOverlay(String level, List<Map> resources) {
    return copyWith(safetyOverlayLevel: level, safetyOverlayResources: resources);
  }

  ChatState addReframe(String id, String reframed, String original, double confidence) {
    return copyWith(
      messages: messages.map((m) {
        if (m.id == id) {
          return m.copyWith(reframe: NVCReframe(reframed: reframed, original: original, confidence: confidence));
        }
        return m;
      }).toList(),
    );
  }

  ChatState startTurnHold(int countdown) {
    return copyWith(turnHoldCountdown: countdown);
  }
  
  ChatState updateTurnHold(int countdown) {
    return copyWith(turnHoldCountdown: countdown);
  }

  ChatState showDeEscalation(String prompt) {
    return copyWith(deEscalationPrompt: prompt);
  }

  ChatState finalizeMessage(String id) {
    return copyWith(
      messages: messages.map((m) {
        if (m.id == id) {
          return m.copyWith(isStreaming: false);
        }
        return m;
      }).toList(),
    );
  }

  ChatState applyUserReframeCorrection(String id, String correction) {
    return copyWith(
      messages: messages.map((m) {
        if (m.id == id && m.reframe != null) {
          // In a real app we might update the reframe object or add a new correction field.
          // For now, we clear the reframe so the user can see it was rejected.
          return ChatMessage(
            id: m.id,
            text: m.text,
            isUser: m.isUser,
            isStreaming: m.isStreaming,
            strategy: m.strategy,
            isSafetyMessage: m.isSafetyMessage,
            reframe: null,
          );
        }
        return m;
      }).toList(),
    );
  }
}
