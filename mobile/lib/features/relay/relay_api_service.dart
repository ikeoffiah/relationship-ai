import 'package:mobile/core/api_services/base_api_service.dart';
import 'package:mobile/core/security/certificate_config.dart';
import 'package:mobile/features/relay/relay_models.dart';

/// Talks to the FastAPI relay endpoints. Extends [BaseApiService] for the
/// Bearer token and certificate pinning, and targets the FastAPI host (relay
/// lives there, alongside chat), replacing the earlier raw-http service that
/// carried a manually-passed token and hit paths the backend never had.
class RelayApiService extends BaseApiService {
  RelayApiService({super.injectedDio})
      : super(baseUrl: 'https://${CertConfig.fastapiHost}');

  /// Send a relay to the partner resolved from the sender's active
  /// relationship. Returns the new relay's status ('ready' | 'processing').
  ///
  /// [sessionId] is a path segment only — the backend routes by relationship —
  /// so async relays pass a sentinel.
  Future<String> send({
    required String content,
    required bool consent,
    String sessionId = 'async',
  }) async {
    try {
      final res = await dio.post(
        '/api/v1/sessions/$sessionId/relay',
        data: {'content': content, 'consent_to_relay': consent},
      );
      return res.data['status'] as String;
    } catch (e) {
      throw handleError(e);
    }
  }

  /// The relays waiting for [userId] to review.
  Future<List<RelayDetail>> fetchPending(String userId) async {
    try {
      final res = await dio.get('/api/v1/users/$userId/relay/pending');
      final list = (res.data as List).cast<Map<String, dynamic>>();
      return list.map(RelayDetail.fromJson).toList();
    } catch (e) {
      throw handleError(e);
    }
  }

  /// Recipient takes delivery, choosing the AI-translated or original version.
  Future<RelayDetail> deliver(String relayId, String version) async {
    try {
      final res = await dio.post(
        '/api/v1/relay/$relayId/deliver',
        data: {'recipient_chose_version': version},
      );
      return RelayDetail.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  /// Sender withdraws a relay before it is delivered.
  Future<void> withdraw(String relayId) async {
    try {
      await dio.delete('/api/v1/relay/$relayId');
    } catch (e) {
      throw handleError(e);
    }
  }
}
