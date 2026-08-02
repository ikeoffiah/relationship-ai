import '../../core/api_services/base_api_service.dart';
import 'engagement_models.dart';
import '../relationship/connection_score.dart';
import '../relationship/relationship_insight.dart';

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

  // ── The connection score ──────────────────────────────────────────
  /// How the relationship is going, and how prominently to say it.
  ///
  /// Fails to [ConnectionScore.unknown] rather than throwing. A home screen
  /// that cannot load because one card's request failed is a worse outcome
  /// than a home screen with one card missing, and `hidden` is a true
  /// statement when we could not find out.
  Future<ConnectionScore> fetchConnectionScore() async {
    try {
      final res = await dio.get('/api/v1/personalization/connection');
      return ConnectionScore.fromJson(res.data as Map<String, dynamic>);
    } catch (_) {
      return ConnectionScore.unknown;
    }
  }

  // ── What Bliss has noticed ────────────────────────────────────────
  /// Shape-only insights the server has decided this user may see.
  ///
  /// Fails to an empty list for the same reason the score fails to `hidden`:
  /// a card that cannot load should look like "nothing to say today", which is
  /// true, rather than take the home screen down with it.
  ///
  /// No filtering happens here beyond dropping empty shapes. Consent, expiry,
  /// the abuse hold and the confidence floor are all decided server-side by
  /// `RelationshipInsight.objects.public(user)` — re-deciding any of it in the
  /// client would mean two implementations of a safety rule, and the wrong one
  /// would be the one on the phone.
  Future<List<RelationshipInsight>> fetchInsights() async {
    try {
      final res = await dio.get('/api/v1/insights/');
      final rows = (res.data as Map<String, dynamic>)['insights'] as List?;
      return (rows ?? [])
          .map(
            (row) =>
                RelationshipInsight.fromJson(row as Map<String, dynamic>),
          )
          .where((insight) => insight.isPresentable)
          .toList();
    } catch (_) {
      return const [];
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
