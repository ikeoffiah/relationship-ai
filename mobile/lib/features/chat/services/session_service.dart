import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:mobile/features/chat/models/chat_models.dart';

class SessionService {
  final Dio _dio;

  SessionService(this._dio);

  Stream<ChatEvent> sendMessage(String sessionId, String content) async* {
    try {
      final request = await _dio.post(
        '/api/v1/sessions/$sessionId/messages',
        data: {'content': content},
        options: Options(
          responseType: ResponseType.stream,
          headers: {'Accept': 'text/event-stream'},
        ),
      );

      final stream = request.data.stream as Stream<Uint8List>;

      await for (final chunk in stream) {
        final text = utf8.decode(chunk);
        for (final line in text.split('\n')) {
          if (!line.startsWith('data: ')) continue;
          final jsonStr = line.substring(6).trim();
          if (jsonStr.isEmpty) continue;
          
          final json = jsonDecode(jsonStr) as Map<String, dynamic>;

          switch (json['type']) {
            case 'token':
              yield ChatTokenEvent(json['content'] as String);
              break;
            case 'strategy_change':
              yield StrategyChangeEvent(json['strategy'] as String);
              break;
            case 'safety_triggered':
              yield SafetyTriggeredEvent(
                level: json['level'] as String,
                resources: (json['resources'] as List).cast<Map>(),
              );
              break;
            case 'reframe_available':
              yield ReframeAvailableEvent(
                reframed: json['reframed'] as String,
                original: json['original'] as String,
                confidence: (json['confidence'] as num).toDouble(),
              );
              break;
            case 'turn_held':
              yield TurnHeldEvent(countdown: json['countdown_seconds'] as int);
              break;
            case 'de_escalation_triggered':
              yield DeEscalationEvent(json['breathing_prompt'] as String);
              break;
            case 'done':
              yield MessageCompleteEvent();
              break;
          }
        }
      }
    } catch (e) {
      // Handle error gracefully in real app
      yield MessageCompleteEvent(); 
    }
  }
}
