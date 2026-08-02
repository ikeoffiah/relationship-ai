import 'package:flutter/foundation.dart';

import 'engagement_api_service.dart';
import '../relationship/connection_score.dart';
import '../relationship/relationship_insight.dart';
import 'engagement_models.dart';

/// Drives the daily-ritual and shared-goals screens. Follows the app's
/// ChangeNotifier + injected-service convention (see RelayViewModel).
class EngagementViewModel extends ChangeNotifier {
  final EngagementApiService _api;
  EngagementViewModel({EngagementApiService? api}) : _api = api ?? EngagementApiService();

  bool _isLoading = false;
  bool get isLoading => _isLoading;
  String? _error;
  String? get error => _error;

  DailyQuestionState _question = const DailyQuestionState();
  DailyQuestionState get question => _question;

  MicroActionState _microAction = const MicroActionState();
  MicroActionState get microAction => _microAction;

  EngagementSummary _summary = const EngagementSummary();
  EngagementSummary get summary => _summary;

  List<SharedGoal> _goals = [];
  List<SharedGoal> get goals => List.unmodifiable(_goals);

  /// How the relationship is going, and how loudly to say it. Starts hidden,
  /// which is also where it stays if the request fails — see
  /// `fetchConnectionScore`.
  ConnectionScore _connection = ConnectionScore.unknown;
  ConnectionScore get connection => _connection;

  /// What Bliss has noticed. Empty is the ordinary state and the honest one —
  /// most couples have no recurring theme and no perception gap, and the
  /// detectors are built to say so rather than to find something.
  List<RelationshipInsight> _insights = [];
  List<RelationshipInsight> get insights => List.unmodifiable(_insights);

  /// Loads everything the daily-ritual hub needs in one shot.
  Future<void> loadRitual() async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      final results = await Future.wait([
        _api.fetchSummary(),
        _api.fetchDailyQuestion(),
        _api.fetchMicroAction(),
        _api.fetchConnectionScore(),
        _api.fetchInsights(),
      ]);
      _summary = results[0] as EngagementSummary;
      _question = results[1] as DailyQuestionState;
      _microAction = results[2] as MicroActionState;
      _connection = results[3] as ConnectionScore;
      _insights = results[4] as List<RelationshipInsight>;
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> answerQuestion(String text) async {
    return _run(() async {
      await _api.answerDailyQuestion(text);
      _question = await _api.fetchDailyQuestion();
      _summary = await _api.fetchSummary();
    });
  }

  Future<bool> checkIn({required int score, String? mood, String? note}) async {
    return _run(() async {
      await _api.submitCheckIn(connectionScore: score, mood: mood, note: note);
      _summary = await _api.fetchSummary();
    });
  }

  Future<bool> completeMicroAction() async {
    return _run(() async {
      await _api.completeMicroAction();
      _microAction = await _api.fetchMicroAction();
      _summary = await _api.fetchSummary();
    });
  }

  Future<bool> logGratitude({required String kind, required String text}) async {
    return _run(() async {
      await _api.logGratitude(kind: kind, text: text);
      _summary = await _api.fetchSummary();
    });
  }

  // ── Goals ──────────────────────────────────────────────────────────
  Future<void> loadGoals() async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      _goals = await _api.fetchGoals();
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> createGoal({
    required String title,
    String? description,
    required String category,
    double? targetValue,
    String? unit,
  }) async {
    return _run(() async {
      final goal = await _api.createGoal(
        title: title,
        description: description,
        category: category,
        targetValue: targetValue,
        unit: unit,
      );
      _goals = [goal, ..._goals];
    });
  }

  Future<bool> logGoalProgress({required String goalId, required double value, String? note}) async {
    return _run(() async {
      final updated = await _api.logGoalProgress(goalId: goalId, value: value, note: note);
      _goals = [
        for (final g in _goals)
          if (g.id == updated.id) updated else g,
      ];
      _summary = await _api.fetchSummary();
    });
  }

  /// Runs a mutation, surfacing errors the same way across the viewmodel.
  /// Returns true on success.
  Future<bool> _run(Future<void> Function() body) async {
    _error = null;
    try {
      await body();
      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      notifyListeners();
      return false;
    }
  }
}
