import 'package:flutter/foundation.dart';

import 'faith_api_service.dart';
import 'faith_models.dart';

/// Drives the faith tab: today's reading, the practice checklist, and a private
/// reflection. Follows the app's ChangeNotifier + injected-service convention.
class FaithViewModel extends ChangeNotifier {
  final FaithApiService _api;
  FaithViewModel({FaithApiService? api}) : _api = api ?? FaithApiService();

  bool _isLoading = false;
  bool get isLoading => _isLoading;

  String? _error;
  String? get error => _error;

  FaithToday? _today;
  FaithToday? get today => _today;

  int _points = 0;
  int get sessionPoints => _points; // points earned in this screen session

  Future<void> loadToday() async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      _today = await _api.fetchToday();
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Optimistically check off a practice, rolling back if the call fails.
  Future<bool> completePractice(String key) async {
    final current = _today;
    if (current == null) return false;

    final updated = current.practices
        .map((p) => p.key == key ? p.copyWith(completed: true) : p)
        .toList();
    _today = current.copyWith(practices: updated);
    notifyListeners();

    try {
      _points += await _api.completePractice(key);
      notifyListeners();
      return true;
    } catch (e) {
      _today = current; // roll back the optimistic tick
      _error = e.toString().replaceAll('Exception: ', '');
      notifyListeners();
      return false;
    }
  }

  Future<bool> reflect(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty) return false;
    try {
      _points += await _api.reflect(trimmed);
      if (_today != null) _today = _today!.copyWith(reflected: true);
      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      notifyListeners();
      return false;
    }
  }
}
