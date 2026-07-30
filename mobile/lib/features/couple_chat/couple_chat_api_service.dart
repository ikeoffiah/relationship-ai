import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:mobile/core/api_services/base_api_service.dart';
import 'package:mobile/features/couple_chat/models/couple_message.dart';
import 'package:mobile/features/couple_chat/models/message_media.dart';

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
  ///
  /// [mediaId] attaches an already-uploaded photo or voice note. On a photo a
  /// non-empty [body] is its caption.
  Future<CoupleMessage> send(
    String relationshipId, {
    required String clientId,
    String? body,
    String? sticker,
    String? replyTo,
    String? mediaId,
    String? mediaKind,
  }) async {
    try {
      final response = await dio.post(
        '${_base(relationshipId)}/messages/send',
        data: {
          'client_id': clientId,
          if (sticker != null) ...{'kind': 'sticker', 'sticker': sticker},
          if (mediaId != null) ...{'kind': mediaKind, 'media': mediaId},
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

  /// Upload a photo or voice note, ahead of the message that will carry it.
  ///
  /// Two steps rather than one multipart send, so the bubble can render from
  /// the local file with a progress ring the moment the user picks or releases.
  /// [onProgress] drives that ring.
  ///
  /// An upload that is never followed by a send is collected server-side after
  /// a day, so abandoning here costs nothing.
  Future<MessageMedia> uploadMedia(
    String relationshipId, {
    required String path,
    required String kind,
    int? durationMs,
    List<int>? waveform,
    void Function(double progress)? onProgress,
    CancelToken? cancelToken,
  }) async {
    try {
      final form = FormData.fromMap({
        'kind': kind,
        'file': await MultipartFile.fromFile(path),
        // ignore: use_null_aware_elements — keyed entries, not spreads
        if (durationMs != null) 'duration_ms': durationMs,
        if (waveform != null) 'waveform': jsonEncode(waveform),
      });
      final response = await dio.post(
        '${_base(relationshipId)}/media',
        data: form,
        cancelToken: cancelToken,
        options: Options(
          // The default 10s receive timeout is for JSON. A photo on a poor
          // connection legitimately takes longer, and killing it mid-upload
          // reads as "the app is broken" rather than "the network is slow".
          sendTimeout: const Duration(minutes: 2),
          receiveTimeout: const Duration(minutes: 2),
        ),
        onSendProgress: (sent, total) {
          if (total > 0) onProgress?.call(sent / total);
        },
      );
      return MessageMedia.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  /// Re-read a media row.
  ///
  /// Transcription finishes after the upload has responded, so this is how a
  /// voice note's transcript arrives — for the sender before they send, and
  /// for the reader when they tap to expand.
  Future<MessageMedia> mediaMeta(String mediaId) async {
    try {
      final response = await dio.get('/api/v1/chat/media/$mediaId/meta');
      return MessageMedia.fromJson(response.data as Map<String, dynamic>);
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

  /// Whether the couple's mutual intimate-content consent is in place.
  ///
  /// Deliberately the games endpoint rather than a second consent of our own.
  /// The gate — both partners age-verified, both opted in — is about the couple,
  /// not about games, and two switches for one decision is how you end up with
  /// a couple who thinks they turned something off and did not.
  Future<bool> intimateUnlocked(String relationshipId) async {
    try {
      final res = await dio.get('/api/v1/engagement/games/spicy-consent');
      final data = res.data as Map<String, dynamic>;
      return data['unlocked'] as bool? ?? false;
    } catch (_) {
      // Fails closed. Not knowing must not be the same as being unlocked.
      //
      // This catch used to be doing two jobs: swallowing real failures, and
      // absorbing the 409 the endpoint returned for anyone without a partner.
      // The second was the common case, so every solo user opening the thread
      // logged a DioException on a path where nothing had gone wrong. The
      // server answers that question properly now, and this is back to meaning
      // only what it says.
      return false;
    }
  }

  /// Acknowledge that this device now holds the thread — which is a different
  /// claim from having opened it, and is why it is a different endpoint.
  Future<void> markDelivered(String relationshipId) async {
    try {
      await dio.post('${_base(relationshipId)}/delivered');
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
