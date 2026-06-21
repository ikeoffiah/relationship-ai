import 'package:flutter/foundation.dart';
import 'package:mobile/core/api_services/session_history_api_service.dart';
import 'package:mobile/features/history/models/session_history_model.dart';

class SessionHistoryViewModel extends ChangeNotifier {
  final SessionHistoryApiService _api;

  SessionHistoryViewModel({SessionHistoryApiService? apiService})
      : _api = apiService ?? SessionHistoryApiService();

  // ────────────────────────────── State ──────────────────────────────
  List<SessionHistoryItem> _sessions = [];
  bool _isLoading = false;
  bool _isLoadingMore = false;
  bool _hasMore = false;
  int _currentPage = 1;
  String _filter = 'all'; // 'all' | 'individual' | 'joint' | 'relay'
  String? _error;

  // ───────────────────────────── Getters ─────────────────────────────
  List<SessionHistoryItem> get sessions => List.unmodifiable(_sessions);
  bool get isLoading => _isLoading;
  bool get isLoadingMore => _isLoadingMore;
  bool get hasMore => _hasMore;
  String get filter => _filter;
  String? get error => _error;
  bool get isEmpty => !_isLoading && _sessions.isEmpty;

  // ──────────────────────────── Methods ──────────────────────────────

  /// Load the first page (or reload after filter change).
  Future<void> loadSessions() async {
    _isLoading = true;
    _error = null;
    _currentPage = 1;
    notifyListeners();

    try {
      final result = await _api.listSessions(page: 1, filter: _filter);
      _sessions = result['items'] as List<SessionHistoryItem>;
      _hasMore = result['hasMore'] as bool;
      _currentPage = 1;
    } catch (e) {
      debugPrint('SessionHistoryViewModel.loadSessions error: $e');
      _error = 'Could not load sessions. Please try again.';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Load the next page (called by the infinite scroll listener).
  Future<void> loadMore() async {
    if (_isLoadingMore || !_hasMore) return;

    _isLoadingMore = true;
    notifyListeners();

    try {
      final nextPage = _currentPage + 1;
      final result =
          await _api.listSessions(page: nextPage, filter: _filter);
      _sessions.addAll(result['items'] as List<SessionHistoryItem>);
      _hasMore = result['hasMore'] as bool;
      _currentPage = nextPage;
    } catch (e) {
      debugPrint('SessionHistoryViewModel.loadMore error: $e');
    } finally {
      _isLoadingMore = false;
      notifyListeners();
    }
  }

  /// Change the active session-type filter and reload.
  Future<void> setFilter(String newFilter) async {
    if (_filter == newFilter) return;
    _filter = newFilter;
    await loadSessions();
  }

  /// Pull-to-refresh: reload from page 1.
  Future<void> refresh() => loadSessions();

  void clearError() {
    _error = null;
    notifyListeners();
  }
}
