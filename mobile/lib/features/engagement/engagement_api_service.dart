import '../../core/api_services/base_api_service.dart';
import 'engagement_models.dart';

/// API client for the daily-engagement endpoints (Django host).
///
/// Extends [BaseApiService], so JWT injection, token refresh, TLS pinning and
/// error normalisation are all inherited — each method only builds its path and
/// decodes the response.
class EngagementApiService extends BaseApiService {
  EngagementApiService({super.injectedDio});

  static const _base = '/api/v1/engagement';

  // ── Daily question ────────────────────────────────────────────────
  Future<DailyQuestionState> fetchDailyQuestion() async {
    try {
      final res = await dio.get('$_base/daily-question');
      return DailyQuestionState.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<ActionReward> answerDailyQuestion(String responseText) async {
    try {
      final res = await dio.post(
        '$_base/daily-question/answer',
        data: {'response_text': responseText},
      );
      return ActionReward.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  // ── Daily check-in ────────────────────────────────────────────────
  Future<ActionReward> submitCheckIn({
    required int connectionScore,
    String? mood,
    String? note,
  }) async {
    try {
      final res = await dio.post('$_base/check-in', data: {
        'connection_score': connectionScore,
        if (mood != null && mood.isNotEmpty) 'mood': mood,
        if (note != null && note.isNotEmpty) 'note': note,
      });
      return ActionReward.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  // ── Micro-action ──────────────────────────────────────────────────
  Future<MicroActionState> fetchMicroAction() async {
    try {
      final res = await dio.get('$_base/micro-action');
      return MicroActionState.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<int> completeMicroAction() async {
    try {
      final res = await dio.post('$_base/micro-action/complete');
      return res.data['points_awarded'] as int? ?? 0;
    } catch (e) {
      throw handleError(e);
    }
  }

  // ── Gratitude / repair ────────────────────────────────────────────
  Future<ActionReward> logGratitude({required String kind, required String text}) async {
    try {
      final res = await dio.post('$_base/gratitude', data: {'kind': kind, 'text': text});
      return ActionReward.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  // ── Shared goals ──────────────────────────────────────────────────
  Future<List<SharedGoal>> fetchGoals() async {
    try {
      final res = await dio.get('$_base/goals');
      final list = (res.data['goals'] as List).cast<Map<String, dynamic>>();
      return list.map(SharedGoal.fromJson).toList();
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<SharedGoal> createGoal({
    required String title,
    String? description,
    required String category,
    String cadence = 'daily',
    double? targetValue,
    String? unit,
  }) async {
    try {
      final res = await dio.post('$_base/goals', data: {
        'title': title,
        'description': ?description,
        'category': category,
        'cadence': cadence,
        'target_value': ?targetValue,
        'unit': ?unit,
      });
      return SharedGoal.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<SharedGoal> logGoalProgress({required String goalId, required double value, String? note}) async {
    try {
      final res = await dio.post('$_base/goals/$goalId/progress', data: {
        'value': value,
        if (note != null && note.isNotEmpty) 'note': note,
      });
      return SharedGoal.fromJson(res.data['goal'] as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  // ── Summary ───────────────────────────────────────────────────────
  Future<EngagementSummary> fetchSummary() async {
    try {
      final res = await dio.get('$_base/summary');
      return EngagementSummary.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }
}
