import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:mobile/core/api_services/base_api_service.dart';
import 'package:mobile/core/security/certificate_config.dart';
import 'package:mobile/features/chat/models/chat_models.dart';

/// Streams a counseling turn from the FastAPI service.
///
/// Extends [BaseApiService] so the request carries the Bearer token and the
/// release-build certificate pinning, and targets the FastAPI host rather than
/// the Django REST host. `receiveTimeout` is disabled because a counseling
/// turn is a long-lived response that a fixed timeout would abort mid-stream.
class SessionService extends BaseApiService {
  SessionService({super.injectedDio})
    : super(
        baseUrl: 'https://${CertConfig.fastapiHost}',
        receiveTimeout: null,
      );

  Stream<ChatEvent> sendMessage(String sessionId, String content) async* {
    try {
      final request = await dio.post(
        '/api/v1/sessions/$sessionId/messages',
        data: {'content': content},
        options: Options(
          responseType: ResponseType.stream,
          headers: {'Accept': 'text/event-stream'},
        ),
      );

      final stream = request.data.stream as Stream<Uint8List>;

      // A chunk boundary can fall mid-line, so hold the trailing partial line
      // back until the next chunk completes it.
      var buffer = '';

      await for (final chunk in stream) {
        buffer += utf8.decode(chunk, allowMalformed: true);
        final lines = buffer.split('\n');
        buffer = lines.removeLast();

        for (final line in lines) {
          final event = _parseLine(line);
          if (event != null) yield event;
        }
      }

      final trailing = _parseLine(buffer);
      if (trailing != null) yield trailing;
    } catch (e) {
      // Surface completion so the UI does not sit on a spinner forever.
      yield MessageCompleteEvent();
    }
  }

  ChatEvent? _parseLine(String line) {
    if (!line.startsWith('data: ')) return null;
    final jsonStr = line.substring(6).trim();
    if (jsonStr.isEmpty) return null;

    final Map<String, dynamic> json;
    try {
      json = jsonDecode(jsonStr) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }

    switch (json['type']) {
      case 'token':
        return ChatTokenEvent(json['content'] as String);
      case 'strategy_change':
        return StrategyChangeEvent(json['strategy'] as String);
      case 'safety_triggered':
        return SafetyTriggeredEvent(
          level: json['level'] as String,
          resources: (json['resources'] as List).cast<Map>(),
        );
      case 'reframe_available':
        return ReframeAvailableEvent(
          reframed: json['reframed'] as String,
          original: json['original'] as String,
          confidence: (json['confidence'] as num).toDouble(),
        );
      case 'turn_held':
        return TurnHeldEvent(countdown: json['countdown_seconds'] as int);
      case 'de_escalation_triggered':
        return DeEscalationEvent(json['breathing_prompt'] as String);
      case 'done':
        return MessageCompleteEvent();
      default:
        return null;
    }
  }
}
