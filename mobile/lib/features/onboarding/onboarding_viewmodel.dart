import 'package:flutter/foundation.dart';
import 'package:mobile/core/api_services/personalization_api_service.dart';

/// Manages the multi-step onboarding flow state.
///
/// Screens: RSQ → Relationship Context → Cultural Context → Communication Quiz
class OnboardingViewModel extends ChangeNotifier {
  final PersonalizationApiService _api;

  OnboardingViewModel({PersonalizationApiService? api})
      : _api = api ?? PersonalizationApiService();

  // ── Loading / error state ──────────────────────────────────────────────────
  bool _isLoading = false;
  bool get isLoading => _isLoading;

  String? _error;
  String? get error => _error;

  // ── Questionnaire definitions (fetched from API) ───────────────────────────
  List<Map<String, dynamic>> _rsqQuestions = [];
  List<Map<String, dynamic>> get rsqQuestions => _rsqQuestions;

  List<Map<String, dynamic>> _stages = [];
  List<Map<String, dynamic>> get stages => _stages;

  List<Map<String, dynamic>> _communicationQuiz = [];
  List<Map<String, dynamic>> get communicationQuiz => _communicationQuiz;

  // ── User responses (collected across screens) ──────────────────────────────
  final Map<String, int> _rsqResponses = {};
  Map<String, int> get rsqResponses => _rsqResponses;

  String _relationshipStage = '';
  String get relationshipStage => _relationshipStage;

  int? _relationshipDurationMonths;
  int? get relationshipDurationMonths => _relationshipDurationMonths;

  bool? _cohabiting;
  bool? get cohabiting => _cohabiting;

  int _childrenCount = 0;
  int get childrenCount => _childrenCount;

  String _reasonForUsing = '';
  String get reasonForUsing => _reasonForUsing;

  String _culturalBackground = '';
  String get culturalBackground => _culturalBackground;

  String _religiousValues = '';
  String get religiousValues => _religiousValues;

  String _communicationStylePreference = 'direct';
  String get communicationStylePreference => _communicationStylePreference;

  String _familyCommunityOrientation = 'individual';
  String get familyCommunityOrientation => _familyCommunityOrientation;

  final Map<String, String> _communicationQuizResponses = {};
  Map<String, String> get communicationQuizResponses =>
      _communicationQuizResponses;

  // ── Computed results (returned from API after submission) ──────────────────
  String _attachmentStyle = '';
  String get attachmentStyle => _attachmentStyle;

  String _communicationStyle = '';
  String get communicationStyle => _communicationStyle;

  bool _onboardingCompleted = false;
  bool get onboardingCompleted => _onboardingCompleted;

  // ── Current step tracking ──────────────────────────────────────────────────
  int _currentStep = 0;
  int get currentStep => _currentStep;
  static const int totalSteps = 4;

  void setCurrentStep(int step) {
    _currentStep = step;
    notifyListeners();
  }

  // ── API methods ────────────────────────────────────────────────────────────

  /// Loads the questionnaire definitions from the server.
  Future<void> loadQuestionnaire() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final data = await _api.fetchQuestionnaire();
      _rsqQuestions = List<Map<String, dynamic>>.from(data['rsq_questions'] ?? []);
      _stages = List<Map<String, dynamic>>.from(data['stages'] ?? []);
      _communicationQuiz = List<Map<String, dynamic>>.from(data['communication_quiz'] ?? []);
    } catch (e) {
      _error = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Loads the user's existing profile (for resuming onboarding).
  Future<void> loadProfile() async {
    try {
      final data = await _api.fetchProfile();
      _onboardingCompleted = data['onboarding_completed'] ?? false;
      _attachmentStyle = data['attachment_style'] ?? '';
      _communicationStyle = data['communication_style_self_report'] ?? '';

      if (data['rsq_responses'] is Map && (data['rsq_responses'] as Map).isNotEmpty) {
        _rsqResponses.clear();
        (data['rsq_responses'] as Map).forEach((k, v) {
          _rsqResponses[k.toString()] = int.tryParse(v.toString()) ?? 3;
        });
      }

      _relationshipStage = data['relationship_stage'] ?? '';
      _culturalBackground = data['cultural_background'] ?? '';
      _religiousValues = data['religious_values'] ?? '';
      _communicationStylePreference = data['communication_style_preference'] ?? 'direct';
      _familyCommunityOrientation = data['family_community_orientation'] ?? 'individual';

      notifyListeners();
    } catch (_) {
      // Profile doesn't exist yet — that's fine for new users.
    }
  }

  // ── Setters (called from UI) ───────────────────────────────────────────────

  void setRsqResponse(int questionId, int value) {
    _rsqResponses[questionId.toString()] = value;
    notifyListeners();
  }

  void setRelationshipStage(String stage) {
    _relationshipStage = stage;
    notifyListeners();
  }

  void setRelationshipDuration(int? months) {
    _relationshipDurationMonths = months;
    notifyListeners();
  }

  void setCohabiting(bool? val) {
    _cohabiting = val;
    notifyListeners();
  }

  void setChildrenCount(int count) {
    _childrenCount = count;
    notifyListeners();
  }

  void setReasonForUsing(String reason) {
    _reasonForUsing = reason;
    notifyListeners();
  }

  void setCulturalBackground(String val) {
    _culturalBackground = val;
    notifyListeners();
  }

  void setReligiousValues(String val) {
    _religiousValues = val;
    notifyListeners();
  }

  void setCommunicationStylePreference(String val) {
    _communicationStylePreference = val;
    notifyListeners();
  }

  void setFamilyCommunityOrientation(String val) {
    _familyCommunityOrientation = val;
    notifyListeners();
  }

  void setCommunicationQuizAnswer(int questionId, String value) {
    _communicationQuizResponses[questionId.toString()] = value;
    notifyListeners();
  }

  // ── Submission ─────────────────────────────────────────────────────────────

  /// Submits all collected data to the backend.
  Future<bool> submitOnboarding() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final payload = <String, dynamic>{
        'rsq_responses': _rsqResponses,
        'relationship_stage': _relationshipStage,
        'relationship_duration_months': _relationshipDurationMonths,
        'cohabiting': _cohabiting,
        'children_count': _childrenCount,
        'reason_for_using': _reasonForUsing,
        'cultural_background': _culturalBackground,
        'religious_values': _religiousValues,
        'communication_style_preference': _communicationStylePreference,
        'family_community_orientation': _familyCommunityOrientation,
        'communication_style_quiz_responses': _communicationQuizResponses,
      };

      final result = await _api.submitProfile(payload);

      _attachmentStyle = result['attachment_style'] ?? '';
      _communicationStyle = result['communication_style_self_report'] ?? '';
      _onboardingCompleted = result['onboarding_completed'] ?? false;

      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString();
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  /// Checks whether the RSQ section is fully answered.
  bool get isRsqComplete => _rsqResponses.length >= 30;

  /// Checks whether the relationship context section has a stage selected.
  bool get isRelationshipContextComplete => _relationshipStage.isNotEmpty;

  /// Checks whether the cultural context section is filled.
  bool get isCulturalContextComplete => _culturalBackground.isNotEmpty;

  /// Checks whether all comm-quiz questions are answered.
  bool get isCommunicationQuizComplete =>
      _communicationQuizResponses.length >= _communicationQuiz.length &&
      _communicationQuiz.isNotEmpty;
}
