import 'package:flutter/foundation.dart';
import 'package:mobile/core/api_services/session_history_api_service.dart';
import 'package:mobile/core/services/storage_service.dart';
import 'package:mobile/features/history/models/session_history_model.dart';

class SessionDetailViewModel extends ChangeNotifier {
  final SessionHistoryApiService _api;

  SessionDetailViewModel({SessionHistoryApiService? apiService})
      : _api = apiService ?? SessionHistoryApiService();

  // ────────────────────────────── State ──────────────────────────────
  SessionDetail? _detail;
  List<SessionMemory> _memories = [];
  bool _isLoading = false;
  bool _isDeletingAll = false;
  String? _error;

  // ───────────────────────────── Getters ─────────────────────────────
  SessionDetail? get detail => _detail;
  List<SessionMemory> get memories => List.unmodifiable(_memories);
  bool get isLoading => _isLoading;
  bool get isDeletingAll => _isDeletingAll;
  String? get error => _error;

  // ──────────────────────────── Methods ──────────────────────────────

  /// Load the session detail and its memories concurrently.
  Future<void> loadDetail(String sessionId) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    final userId = await StorageService.getUserId();

    try {
      final results = await Future.wait([
        _api.getSessionSummary(sessionId),
        if (userId != null)
          _api.getSessionMemories(userId, sessionId)
        else
          Future.value(<SessionMemory>[]),
      ]);

      _detail = results[0] as SessionDetail;
      _memories = results[1] as List<SessionMemory>;
    } catch (e) {
      debugPrint('SessionDetailViewModel.loadDetail error: $e');
      _error = 'Could not load session details. Please try again.';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Enter or exit inline-edit mode for a memory.
  void toggleEditMode(String memoryId) {
    final index = _memories.indexWhere((m) => m.id == memoryId);
    if (index == -1) return;
    _memories[index] = _memories[index].copyWith(
      isEditing: !_memories[index].isEditing,
    );
    notifyListeners();
  }

  /// Save an edited memory (optimistic update with rollback).
  Future<void> saveMemory(String memoryId, String newContent) async {
    final userId = await StorageService.getUserId();
    if (userId == null) return;

    final index = _memories.indexWhere((m) => m.id == memoryId);
    if (index == -1) return;

    final previous = _memories[index];
    _memories[index] = previous.copyWith(content: newContent, isEditing: false);
    notifyListeners();

    try {
      await _api.updateMemory(userId, memoryId, {'content': newContent});
    } catch (e) {
      debugPrint('SessionDetailViewModel.saveMemory error: $e');
      _memories[index] = previous;
      _error = 'Failed to save changes. Please try again.';
      notifyListeners();
    }
  }

  /// Delete a single memory (optimistic update with rollback).
  Future<void> deleteMemory(String memoryId) async {
    final userId = await StorageService.getUserId();
    if (userId == null) return;

    final index = _memories.indexWhere((m) => m.id == memoryId);
    if (index == -1) return;

    final previous = _memories[index];
    _memories.removeAt(index);
    notifyListeners();

    try {
      await _api.deleteMemory(userId, memoryId);
    } catch (e) {
      debugPrint('SessionDetailViewModel.deleteMemory error: $e');
      _memories.insert(index, previous);
      _error = 'Failed to delete memory. Please try again.';
      notifyListeners();
    }
  }

  /// Bulk-delete all memories from this session.
  Future<bool> deleteAllSessionMemories() async {
    final userId = await StorageService.getUserId();
    final sessionId = _detail?.id;
    if (userId == null || sessionId == null) return false;

    _isDeletingAll = true;
    notifyListeners();

    try {
      await _api.deleteSessionMemories(userId, sessionId);
      _memories = [];
      return true;
    } catch (e) {
      debugPrint('SessionDetailViewModel.deleteAllSessionMemories error: $e');
      _error = 'Failed to delete memories. Please try again.';
      return false;
    } finally {
      _isDeletingAll = false;
      notifyListeners();
    }
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }
}
