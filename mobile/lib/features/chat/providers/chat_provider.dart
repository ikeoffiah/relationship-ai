import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:uuid/uuid.dart';
import 'package:mobile/features/chat/models/chat_models.dart';
import 'package:mobile/features/chat/models/chat_state.dart';
import 'package:mobile/features/chat/services/session_service.dart';

part 'chat_provider.g.dart';

final sessionServiceProvider = Provider((ref) => SessionService(Dio()));

@riverpod
class ChatNotifier extends _$ChatNotifier {
  @override
  ChatState build(String sessionId) => ChatState.initial();

  Future<void> sendMessage(String content) async {
    state = state.addUserMessage(content);
    
    const uuid = Uuid();
    final assistantMsgId = uuid.v4();
    state = state.addStreamingMessage(assistantMsgId);

    final service = ref.read(sessionServiceProvider);
    
    await for (final event in service.sendMessage(sessionId, content)) {
      state = switch (event) {
        ChatTokenEvent(:final content) =>
          state.appendToken(assistantMsgId, content),
        StrategyChangeEvent(:final strategy) =>
          state.updateStrategy(strategy),
        SafetyTriggeredEvent(:final level, :final resources) =>
          state.showSafetyOverlay(level, resources),
        ReframeAvailableEvent(:final reframed, :final original, :final confidence) =>
          state.addReframe(assistantMsgId, reframed, original, confidence),
        TurnHeldEvent(:final countdown) =>
          state.startTurnHold(countdown),
        DeEscalationEvent(:final breathingPrompt) =>
          state.showDeEscalation(breathingPrompt),
        MessageCompleteEvent() =>
          state.finalizeMessage(assistantMsgId),
        _ => state,
      };
    }
  }

  void rejectReframe(String messageId, String correction) {
    state = state.applyUserReframeCorrection(messageId, correction);
  }
  
  void updateTurnHold(int countdown) {
    state = state.updateTurnHold(countdown);
  }
}
