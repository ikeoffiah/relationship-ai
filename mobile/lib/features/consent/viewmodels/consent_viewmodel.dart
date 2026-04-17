import 'package:flutter/foundation.dart';
import 'package:mobile/core/api_services/consent_api_service.dart';
import 'package:mobile/features/consent/models/consent_model.dart';

/// ViewModel for managing consent state throughout the session lifecycle.
///
/// Responsibilities:
/// - Fetch fresh consent from the API on every session start (no cache).
/// - Provide single-method revocation for in-session permission changes.
/// - Notify listeners immediately for responsive UI feedback.
class ConsentViewModel extends ChangeNotifier {
  final ConsentApiService _apiService;

  ConsentViewModel({ConsentApiService? apiService})
      : _apiService = apiService ?? ConsentApiService();

  ConsentModel? _consent;
  bool _isLoading = false;
  String? _errorMessage;

  ConsentModel? get consent => _consent;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  void _setLoading(bool value) {
    _isLoading = value;
    notifyListeners();
  }

  void _setError(String? message) {
    _errorMessage = message;
    notifyListeners();
  }

  /// Fetches the latest consent state from the API.
  ///
  /// Called every time the [ConsentSummarySheet] opens — never uses a cache.
  /// On failure, falls back to most-restrictive defaults so the session can
  /// still proceed safely.
  Future<void> fetchConsent(String userId) async {
    _setLoading(true);
    _errorMessage = null;
    try {
      _consent = await _apiService.fetchConsent(userId);
    } catch (e) {
      debugPrint('ConsentViewModel.fetchConsent error: $e');
      _setError(e.toString().replaceAll('Exception: ', ''));
      // Safe fallback — most restrictive defaults
      _consent ??= ConsentModel.defaultRestrictive(userId);
    } finally {
      _setLoading(false);
    }
  }

  /// Updates a single consent field in-session.
  ///
  /// Applies an optimistic local update immediately (for responsive UI),
  /// then syncs with the API. If the API call fails, reverts to the
  /// previous state.
  ///
  /// [field] is the snake_case API field name (e.g. 'therapist_summary_access').
  /// [value] is the new value (String or bool).
  Future<void> updateField(
    String userId,
    String field,
    dynamic value,
  ) async {
    if (_consent == null) return;

    final previous = _consent!;

    // Optimistic update — apply immediately for responsive UI
    _consent = _applyField(previous, field, value);
    notifyListeners();

    try {
      final updated = await _apiService.updateConsent(userId, {field: value});
      _consent = updated;
      notifyListeners();
    } catch (e) {
      debugPrint('ConsentViewModel.updateField error: $e');
      // Revert on failure
      _consent = previous;
      _setError('Failed to update consent: ${e.toString().replaceAll('Exception: ', '')}');
    }
  }

  /// Applies a field update to a [ConsentModel] via copyWith.
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

  void clearError() {
    _setError(null);
  }
}
