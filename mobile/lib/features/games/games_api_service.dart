import '../../core/api_services/base_api_service.dart';
import 'games_models.dart';

/// API client for the couple-games endpoints (Django host). Extends
/// [BaseApiService] for JWT injection, refresh and pinning.
class GamesApiService extends BaseApiService {
  GamesApiService({super.injectedDio});

  static const _base = '/api/v1/engagement/games';

  Future<List<GameSummary>> fetchGames() async {
    try {
      final res = await dio.get(_base);
      final list = (res.data['games'] as List).cast<Map<String, dynamic>>();
      return list.map(GameSummary.fromJson).toList();
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<GameDetail> fetchGame(String key) async {
    try {
      final res = await dio.get('$_base/$key');
      return GameDetail.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  /// Submit one answer; returns the raw payload {progress, just_completed, reveal?}.
  Future<Map<String, dynamic>> submitAnswer({
    required String key,
    required String questionId,
    required int selfAnswer,
    required int guessAnswer,
  }) async {
    try {
      final res = await dio.post('$_base/$key/answer', data: {
        'question_id': questionId,
        'self_answer': selfAnswer,
        'guess_answer': guessAnswer,
      });
      return res.data as Map<String, dynamic>;
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<SpicyConsent> fetchSpicyConsent() async {
    try {
      final res = await dio.get('$_base/spicy-consent');
      return SpicyConsent.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<SpicyConsent> setSpicyConsent(bool enabled) async {
    try {
      final res = await dio.post('$_base/spicy-consent', data: {'enabled': enabled});
      return SpicyConsent.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }
}
