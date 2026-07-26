import 'package:flutter/foundation.dart';

import 'games_api_service.dart';
import 'games_models.dart';

/// Drives the games list and a Know Your Partner play/reveal flow. Follows the
/// app's ChangeNotifier + injected-service convention.
class GamesViewModel extends ChangeNotifier {
  final GamesApiService _api;
  GamesViewModel({GamesApiService? api}) : _api = api ?? GamesApiService();

  bool _isLoading = false;
  bool get isLoading => _isLoading;
  String? _error;
  String? get error => _error;

  List<GameSummary> _games = [];
  List<GameSummary> get games => List.unmodifiable(_games);

  GameDetail? _detail;
  GameDetail? get detail => _detail;

  SpicyConsent? _spicyConsent;
  SpicyConsent? get spicyConsent => _spicyConsent;

  Future<void> loadSpicyConsent() async {
    try {
      _spicyConsent = await _api.fetchSpicyConsent();
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
    }
    notifyListeners();
  }

  /// Toggle the caller's spicy opt-in, then refresh the games list (spicy packs
  /// appear/disappear based on the couple's combined consent).
  Future<bool> toggleSpicy(bool enabled) async {
    try {
      _spicyConsent = await _api.setSpicyConsent(enabled);
      await loadGames();
      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      notifyListeners();
      return false;
    }
  }

  Future<void> loadGames() async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      _games = await _api.fetchGames();
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> loadGame(String key) async {
    _isLoading = true;
    _error = null;
    _detail = null;
    notifyListeners();
    try {
      _detail = await _api.fetchGame(key);
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Submit every answered question in a play session. Returns the refreshed
  /// detail (with reveal when both partners are now done), or null on error.
  Future<GameDetail?> submitAnswers(
    String key,
    Map<String, ({int self, int? guess})> answers,
  ) async {
    _error = null;
    try {
      for (final entry in answers.entries) {
        await _api.submitAnswer(
          key: key,
          questionId: entry.key,
          selfAnswer: entry.value.self,
          guessAnswer: entry.value.guess,
        );
      }
      _detail = await _api.fetchGame(key);
      notifyListeners();
      return _detail;
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      notifyListeners();
      return null;
    }
  }
}
