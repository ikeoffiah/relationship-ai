import 'package:flutter/foundation.dart';

import 'tone_api_service.dart';
import 'tone_models.dart';

/// Screen-scoped state for the in-chat tone coach: the current auto-suggestions
/// and in-flight flags. The coach sheet and mood popover call through here too
/// so all tone network access sits behind one injectable service.
class ToneViewModel extends ChangeNotifier {
  final ToneApiService _api;
  ToneViewModel({ToneApiService? api}) : _api = api ?? ToneApiService();

  List<String> _suggestions = const [];
  List<String> get suggestions => List.unmodifiable(_suggestions);

  bool _loadingSuggestions = false;
  bool get loadingSuggestions => _loadingSuggestions;

  String? _error;
  String? get error => _error;

  /// Refresh auto-suggestions from recent messages. Silently clears on failure
  /// (suggestions are a nicety — never block the chat on them).
  Future<void> refreshSuggestions(List<Map<String, String>> messages) async {
    if (messages.isEmpty) {
      _suggestions = const [];
      notifyListeners();
      return;
    }
    _loadingSuggestions = true;
    notifyListeners();
    try {
      _suggestions = await _api.suggest(messages);
    } catch (_) {
      _suggestions = const [];
    } finally {
      _loadingSuggestions = false;
      notifyListeners();
    }
  }

  void clearSuggestions() {
    if (_suggestions.isEmpty) return;
    _suggestions = const [];
    notifyListeners();
  }

  /// Read the mood of a single message. Returns null on failure.
  Future<MoodRead?> readMood(String text) async {
    try {
      return await _api.analyze(text);
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      notifyListeners();
      return null;
    }
  }

  /// Coach a draft. Returns null on failure (caller keeps the original draft).
  Future<CoachResult?> coach(String draft, {String? partnerMood}) async {
    try {
      return await _api.coach(draft, partnerMood: partnerMood);
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      notifyListeners();
      return null;
    }
  }
}
