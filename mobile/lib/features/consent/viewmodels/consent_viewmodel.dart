import 'package:flutter/foundation.dart';
import 'package:mobile/core/api_services/consent_api_service.dart';
import 'package:mobile/features/consent/models/consent_model.dart';
import 'package:mobile/features/consent/models/memory_model.dart';
import 'package:mobile/core/services/storage_service.dart';

class ConsentViewModel extends ChangeNotifier {
  final ConsentApiService _apiService;

  ConsentViewModel({ConsentApiService? apiService})
      : _apiService = apiService ?? ConsentApiService();

  ConsentModel? _consent;
  List<MemoryModel> _memories = [];
  bool _isLoading = false;
  String? _errorMessage;

  ConsentModel? get consent => _consent;
  List<MemoryModel> get memories => _memories;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  int get privateMemoryCount => _memories.where((m) => m.zone == MemoryZone.private).length;
  int get sharedMemoryCount => _memories.where((m) => m.zone == MemoryZone.shared).length;
  int get therapistMemoryCount => _memories.where((m) => m.zone == MemoryZone.therapist).length;

  void _setLoading(bool value) {
    _isLoading = value;
    notifyListeners();
  }

  void _setError(String? message) {
    _errorMessage = message;
    notifyListeners();
  }

  Future<void> fetchConsent() async {
    final userId = await StorageService.getUserId();
    if (userId == null) return;

    _setLoading(true);
    _errorMessage = null;
    try {
      _consent = await _apiService.fetchConsent(userId);
    } catch (e) {
      debugPrint('ConsentViewModel.fetchConsent error: $e');
      _setError('We couldn\'t load your privacy settings. Check your connection.');
      _consent ??= ConsentModel.defaultRestrictive(userId);
    } finally {
      _setLoading(false);
    }
  }

  Future<void> logSummaryShown() async {
    final userId = await StorageService.getUserId();
    if (userId == null) return;
    try {
      await _apiService.logConsentSummaryShown(userId);
    } catch (e) {
      debugPrint('ConsentViewModel.logSummaryShown error: $e');
    }
  }

  Future<void> updateField(String field, dynamic value) async {
    final userId = await StorageService.getUserId();
    if (userId == null || _consent == null) return;

    final previous = _consent!;
    _consent = _applyField(previous, field, value);
    notifyListeners();

    try {
      final updated = await _apiService.updateConsent(userId, {field: value});
      _consent = updated;
      notifyListeners();
    } catch (e) {
      debugPrint('ConsentViewModel.updateField error: $e');
      _consent = previous;
      _setError('Failed to update consent: ${e.toString().replaceAll('Exception: ', '')}');
    }
  }

  ConsentModel _applyField(ConsentModel model, String field, dynamic value) {
    switch (field) {
      case 'session_transcript_retention':
        return model.copyWith(sessionTranscriptRetention: value as String);
      case 'cross_partner_insight_sharing':
        return model.copyWith(crossPartnerInsightSharing: value as String);
      case 'joint_session_participation':
        return model.copyWith(jointSessionParticipation: value as String);
      case 'shared_relationship_context':
        return model.copyWith(sharedRelationshipContext: value as String);
      case 'therapist_summary_access':
        return model.copyWith(therapistSummaryAccess: value as bool);
      case 'model_improvement_data':
        return model.copyWith(modelImprovementData: value as bool);
      default:
        return model;
    }
  }

  Future<void> fetchMemories() async {
    final userId = await StorageService.getUserId();
    if (userId == null) return;

    _setLoading(true);
    try {
      final data = await _apiService.fetchMemories(userId);
      _memories = data.map((m) => MemoryModel.fromJson(m)).toList();
      notifyListeners();
    } catch (e) {
      debugPrint('ConsentViewModel.fetchMemories error: $e');
      _setError('Failed to fetch memories');
    } finally {
      _setLoading(false);
    }
  }

  Future<void> updateMemory(
    String memoryId,
    String title,
  ) async {
    final userId = await StorageService.getUserId();
    if (userId == null) return;

    final index = _memories.indexWhere((m) => m.id == memoryId);
    if (index == -1) return;

    final previous = _memories[index];
    _memories[index] = previous.copyWith(title: title);
    notifyListeners();

    try {
      await _apiService.updateMemory(userId, memoryId, {'title': title});
    } catch (e) {
      debugPrint('ConsentViewModel.updateMemory error: $e');
      _memories[index] = previous;
      _setError('Failed to update memory');
      notifyListeners();
    }
  }

  Future<void> deleteMemory(String memoryId) async {
    final userId = await StorageService.getUserId();
    if (userId == null) return;

    final index = _memories.indexWhere((m) => m.id == memoryId);
    if (index == -1) return;

    final previous = _memories[index];
    _memories.removeAt(index);
    notifyListeners();

    try {
      await _apiService.deleteMemory(userId, memoryId);
    } catch (e) {
      debugPrint('ConsentViewModel.deleteMemory error: $e');
      _memories.insert(index, previous);
      _setError('Failed to delete memory');
      notifyListeners();
    }
  }

  void clearError() {
    _setError(null);
  }
}
