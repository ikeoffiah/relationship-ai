
class ChatMessage {
  final String id;
  final String text;
  final bool isUser;
  final bool isStreaming;
  final String? strategy;
  final bool isSafetyMessage;
  final NVCReframe? reframe;

  const ChatMessage({
    required this.id,
    required this.text,
    required this.isUser,
    this.isStreaming = false,
    this.strategy,
    this.isSafetyMessage = false,
    this.reframe,
  });

  ChatMessage copyWith({
    String? text,
    bool? isStreaming,
    String? strategy,
    bool? isSafetyMessage,
    NVCReframe? reframe,
  }) {
    return ChatMessage(
      id: id,
      text: text ?? this.text,
      isUser: isUser,
      isStreaming: isStreaming ?? this.isStreaming,
      strategy: strategy ?? this.strategy,
      isSafetyMessage: isSafetyMessage ?? this.isSafetyMessage,
      reframe: reframe ?? this.reframe,
    );
  }
}

class NVCReframe {
  final String reframed;
  final String original;
  final double confidence;

  const NVCReframe({
    required this.reframed,
    required this.original,
    required this.confidence,
  });
}

class SessionState {
  final bool isIndividual;
  final bool isJoint;
  final String partnerInitial;
  final String partnerFirstName;

  const SessionState({
    required this.isIndividual,
    required this.isJoint,
    required this.partnerInitial,
    required this.partnerFirstName,
  });
}

// Events
abstract class ChatEvent {}

class ChatTokenEvent extends ChatEvent {
  final String content;
  ChatTokenEvent(this.content);
}

class StrategyChangeEvent extends ChatEvent {
  final String strategy;
  StrategyChangeEvent(this.strategy);
}

class SafetyTriggeredEvent extends ChatEvent {
  final String level;
  final List<Map> resources;
  SafetyTriggeredEvent({required this.level, required this.resources});
}

class ReframeAvailableEvent extends ChatEvent {
  final String reframed;
  final String original;
  final double confidence;
  ReframeAvailableEvent({required this.reframed, required this.original, required this.confidence});
}

class TurnHeldEvent extends ChatEvent {
  final int countdown;
  TurnHeldEvent({required this.countdown});
}

class DeEscalationEvent extends ChatEvent {
  final String breathingPrompt;
  DeEscalationEvent(this.breathingPrompt);
}

class MessageCompleteEvent extends ChatEvent {}
