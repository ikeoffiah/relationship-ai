import 'package:mobile/core/api_services/base_api_service.dart';
import 'package:mobile/features/couple_chat/models/couple_message.dart';

/// HTTP client for the couple's thread.
///
/// Inherits the Bearer token and release-build certificate pinning from
/// [BaseApiService]. Every path is scoped by relationship id; the server
/// resolves membership and 404s a thread the caller is not part of.
class CoupleChatApiService extends BaseApiService {
  CoupleChatApiService({super.injectedDio});

  String _base(String relationshipId) => '/api/v1/chat/$relationshipId';

  /// One page of history, newest first.
  ///
  /// [before] is a cursor, not an offset — the thread grows from the bottom
  /// while you are reading it, and an offset would skip or repeat messages.
  Future<({List<CoupleMessage> messages, bool hasMore, String? nextBefore})>
  history(String relationshipId, {String? before, int limit = 50}) async {
    try {
      final response = await dio.get(
        '${_base(relationshipId)}/messages',
        queryParameters: <String, dynamic>{
          'limit': limit,
          // ignore: use_null_aware_elements — a keyed entry, not a spread
          if (before != null) 'before': before,
        },
      );
      final data = response.data as Map<String, dynamic>;
      return (
        messages: (data['results'] as List)
            .map((m) => CoupleMessage.fromJson(m as Map<String, dynamic>))
            .toList(),
        hasMore: data['has_more'] as bool? ?? false,
        nextBefore: data['next_before'] as String?,
      );
    } catch (e) {
      throw handleError(e);
    }
  }

  /// Send a message. [clientId] makes a retry idempotent — the server returns
  /// the original rather than posting twice.
  Future<CoupleMessage> send(
    String relationshipId, {
    required String clientId,
    String? body,
    String? sticker,
    String? replyTo,
  }) async {
    try {
      final response = await dio.post(
        '${_base(relationshipId)}/messages/send',
        data: {
          'client_id': clientId,
          if (sticker != null) ...{'kind': 'sticker', 'sticker': sticker},
          // ignore: use_null_aware_elements — keyed entries, not spreads
          if (body != null) 'body': body,
          // ignore: use_null_aware_elements
          if (replyTo != null) 'reply_to': replyTo,
        },
      );
      return CoupleMessage.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<CoupleMessage> toggleReaction(String messageId, String emoji) async {
    try {
      final response = await dio.post(
        '/api/v1/chat/messages/$messageId/reactions',
        data: {'emoji': emoji},
      );
      return CoupleMessage.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<void> deleteMessage(String messageId) async {
    try {
      await dio.delete('/api/v1/chat/messages/$messageId');
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<void> markRead(String relationshipId) async {
    try {
      await dio.post('${_base(relationshipId)}/read');
    } catch (e) {
      throw handleError(e);
    }
  }

  /// Ask Bliss whether a draft is likely to land badly.
  ///
  /// Fails open by returning [DraftVerdict.ok]: a check that cannot complete
  /// must never stop someone sending their own message.
  Future<DraftVerdict> checkDraft(String relationshipId, String draft) async {
    try {
      final response = await dio.post(
        '${_base(relationshipId)}/assist/check',
        data: {'draft': draft},
      );
      return DraftVerdict.fromJson(response.data as Map<String, dynamic>);
    } catch (_) {
      return DraftVerdict.ok;
    }
  }

  /// "Help me say this." Returns null if Bliss has nothing to offer.
  Future<String?> rephrase(String relationshipId, String draft) async {
    try {
      final response = await dio.post(
        '${_base(relationshipId)}/assist/rephrase',
        data: {'draft': draft},
      );
      return (response.data as Map<String, dynamic>)['suggestion'] as String?;
    } catch (_) {
      return null;
    }
  }

  /// Private guidance for the partner who just received something hard.
  /// Never shown to the sender.
  Future<({String? guidance, bool deferToSupport})> readCoach(
    String relationshipId,
    String message,
  ) async {
    try {
      final response = await dio.post(
        '${_base(relationshipId)}/assist/read-coach',
        data: {'message': message},
      );
      final data = response.data as Map<String, dynamic>;
      return (
        guidance: data['guidance'] as String?,
        deferToSupport: data['defer_to_support'] as bool? ?? false,
      );
    } catch (_) {
      return (guidance: null, deferToSupport: false);
    }
  }
}
