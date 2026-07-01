import 'package:flutter/material.dart';
import 'package:mobile/core/api_services/settings_api_service.dart';
import 'package:mobile/core/services/storage_service.dart';

/// Notification preference flags, matching the backend schema.
class NotificationPreferences {
  final bool sessionReminders;
  final bool partnerJoinedSession;
  final bool relayMessageReceived;
  final bool insightDetected;

  const NotificationPreferences({
    this.sessionReminders = true,
    this.partnerJoinedSession = true,
    this.relayMessageReceived = true,
    this.insightDetected = false,
  });

  factory NotificationPreferences.fromJson(Map<String, dynamic> json) {
    return NotificationPreferences(
      sessionReminders: json['session_reminders'] ?? true,
      partnerJoinedSession: json['partner_joined_session'] ?? true,
      relayMessageReceived: json['relay_message_received'] ?? true,
      insightDetected: json['insight_detected'] ?? false,
    );
  }

  Map<String, dynamic> toJson() => {
        'session_reminders': sessionReminders,
        'partner_joined_session': partnerJoinedSession,
        'relay_message_received': relayMessageReceived,
        'insight_detected': insightDetected,
      };

  NotificationPreferences copyWith({
    bool? sessionReminders,
    bool? partnerJoinedSession,
    bool? relayMessageReceived,
    bool? insightDetected,
  }) {
    return NotificationPreferences(
      sessionReminders: sessionReminders ?? this.sessionReminders,
      partnerJoinedSession: partnerJoinedSession ?? this.partnerJoinedSession,
      relayMessageReceived: relayMessageReceived ?? this.relayMessageReceived,
      insightDetected: insightDetected ?? this.insightDetected,
    );
  }
}

/// ViewModel for the Settings feature — manages profile, notification
/// preferences, and account-level actions.
class SettingsViewModel extends ChangeNotifier {
  final SettingsApiService _apiService;

  SettingsViewModel({SettingsApiService? apiService})
      : _apiService = apiService ?? SettingsApiService();

  // ── State ─────────────────────────────────────────────────────────────

  bool _isLoading = false;
  String? _errorMessage;
  String? _successMessage;

  String _displayName = '';
  String _email = '';

  NotificationPreferences _notificationPrefs = const NotificationPreferences();

  // App-lock timeout stored locally (not sent to server).
  int _appLockTimeoutMinutes = 5;

  // ── Getters ───────────────────────────────────────────────────────────

  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  String? get successMessage => _successMessage;
  String get displayName => _displayName;
  String get email => _email;
  NotificationPreferences get notificationPrefs => _notificationPrefs;
  int get appLockTimeoutMinutes => _appLockTimeoutMinutes;

  // ── Private helpers ───────────────────────────────────────────────────

  void _setLoading(bool v) {
    _isLoading = v;
    notifyListeners();
  }

  void _setError(String msg) {
    _errorMessage = msg;
    _successMessage = null;
    notifyListeners();
  }

  void _setSuccess(String msg) {
    _successMessage = msg;
    _errorMessage = null;
    notifyListeners();
  }

  void clearMessages() {
    _errorMessage = null;
    _successMessage = null;
    notifyListeners();
  }

  // ── Profile ───────────────────────────────────────────────────────────

  /// Load the authenticated user's profile from the API.
  Future<void> loadProfile(String userId) async {
    _setLoading(true);
    try {
      final data = await _apiService.getProfile(userId);
      _displayName = data['display_name'] ?? data['name'] ?? '';
      _email = data['email'] ?? '';
      _setLoading(false);
    } catch (e) {
      _setError(e.toString().replaceAll('Exception: ', ''));
      _setLoading(false);
    }
  }

  /// Persist a display name change.
  Future<bool> updateDisplayName(String userId, String newName) async {
    if (newName.trim().isEmpty) {
      _setError('Display name cannot be empty');
      return false;
    }
    _setLoading(true);
    try {
      await _apiService.updateProfile(userId, displayName: newName.trim());
      _displayName = newName.trim();
      _setSuccess('Display name updated');
      _setLoading(false);
      return true;
    } catch (e) {
      _setError(e.toString().replaceAll('Exception: ', ''));
      _setLoading(false);
      return false;
    }
  }

  // ── Email Change ──────────────────────────────────────────────────────

  /// Request an email change (verification link sent to [newEmail]).
  Future<bool> requestEmailChange({
    required String newEmail,
    required String password,
  }) async {
    if (newEmail.trim().isEmpty) {
      _setError('Please enter a new email address');
      return false;
    }
    if (password.isEmpty) {
      _setError('Please enter your current password');
      return false;
    }
    _setLoading(true);
    try {
      await _apiService.changeEmail(
        newEmail: newEmail.trim(),
        password: password,
      );
      _setSuccess(
        'Verification sent to $newEmail. Your email won\'t change until you click the link.',
      );
      _setLoading(false);
      return true;
    } catch (e) {
      _setError(e.toString().replaceAll('Exception: ', ''));
      _setLoading(false);
      return false;
    }
  }

  // ── Notification Preferences ──────────────────────────────────────────

  /// Fetch notification preferences from the server.
  Future<void> loadNotificationPreferences(String userId) async {
    try {
      final data = await _apiService.getNotificationPreferences(userId);
      _notificationPrefs = NotificationPreferences.fromJson(data);
      notifyListeners();
    } catch (e) {
      debugPrint('Failed to load notification prefs: $e');
    }
  }

  /// Toggle a single notification preference and persist.
  Future<void> toggleNotificationPref(
    String userId,
    String field,
    bool value,
  ) async {
    // Optimistic update
    final previous = _notificationPrefs;
    switch (field) {
      case 'session_reminders':
        _notificationPrefs = _notificationPrefs.copyWith(sessionReminders: value);
        break;
      case 'partner_joined_session':
        _notificationPrefs = _notificationPrefs.copyWith(partnerJoinedSession: value);
        break;
      case 'relay_message_received':
        _notificationPrefs = _notificationPrefs.copyWith(relayMessageReceived: value);
        break;
      case 'insight_detected':
        _notificationPrefs = _notificationPrefs.copyWith(insightDetected: value);
        break;
    }
    notifyListeners();

    try {
      await _apiService.updateNotificationPreferences(
        userId,
        preferences: {field: value},
      );
    } catch (e) {
      // Rollback on failure
      _notificationPrefs = previous;
      notifyListeners();
      debugPrint('Failed to update notification pref: $e');
    }
  }

  // ── App Lock Timeout (local only) ─────────────────────────────────────

  void setAppLockTimeout(int minutes) {
    _appLockTimeoutMinutes = minutes;
    notifyListeners();
  }

  // ── Account Deletion ──────────────────────────────────────────────────

  /// Delete the user's account (requires password confirmation).
  Future<bool> deleteAccount(String userId, String password) async {
    if (password.isEmpty) {
      _setError('Password is required to delete your account');
      return false;
    }
    _setLoading(true);
    try {
      await _apiService.deleteAccount(userId, password: password);
      await StorageService.clearAll();
      _setLoading(false);
      return true;
    } catch (e) {
      _setError(e.toString().replaceAll('Exception: ', ''));
      _setLoading(false);
      return false;
    }
  }
}
