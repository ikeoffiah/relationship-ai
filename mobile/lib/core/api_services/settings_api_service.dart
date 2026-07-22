import 'package:mobile/core/api_services/base_api_service.dart';

/// API service for user settings: profile, email, notifications, and account.
class SettingsApiService extends BaseApiService {
  SettingsApiService({super.injectedDio});

  // ── Profile ──────────────────────────────────────────────────────────────

  /// Fetch the authenticated user's profile.
  Future<Map<String, dynamic>> getProfile(String userId) async {
    try {
      final response = await dio.get('/api/v1/users/profile/');
      return response.data;
    } catch (e) {
      throw handleError(e);
    }
  }

  /// Update the authenticated user's display name.
  Future<Map<String, dynamic>> updateProfile(
    String userId, {
    required String displayName,
  }) async {
    try {
      final response = await dio.put(
        '/api/v1/users/profile/',
        data: {'full_name': displayName},
      );
      return response.data;
    } catch (e) {
      throw handleError(e);
    }
  }

  // ── Email ────────────────────────────────────────────────────────────────

  /// Initiate email change — sends a verification link to [newEmail].
  Future<void> changeEmail({
    required String newEmail,
    required String password,
  }) async {
    try {
      // Backend route is /api/v1/users/change-email/ and its serializer takes
      // `email` only (accounts/profile/serializers.py:ChangeEmailSerializer).
      await dio.post(
        '/api/v1/users/change-email/',
        data: {'email': newEmail},
      );
    } catch (e) {
      throw handleError(e);
    }
  }

  // ── Notification Preferences ─────────────────────────────────────────────

  /// Fetch current notification preferences.
  Future<Map<String, dynamic>> getNotificationPreferences(
    String userId,
  ) async {
    try {
      final response = await dio.get(
        '/api/v1/users/notification-preferences/',
      );
      return response.data;
    } catch (e) {
      throw handleError(e);
    }
  }

  /// Update a single notification preference field.
  Future<void> updateNotificationPreferences(
    String userId, {
    required Map<String, dynamic> preferences,
  }) async {
    try {
      await dio.put(
        '/api/v1/users/notification-preferences/',
        data: preferences,
      );
    } catch (e) {
      throw handleError(e);
    }
  }

  // ── Account Deletion ─────────────────────────────────────────────────────

  /// Permanently delete the user's account. Requires [password] confirmation.
  Future<void> deleteAccount(
    String userId, {
    required String password,
  }) async {
    try {
      await dio.delete(
        '/api/v1/users/account/',
        data: {'password': password},
      );
    } catch (e) {
      throw handleError(e);
    }
  }
}
