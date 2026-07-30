import 'package:dio/dio.dart';

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

/// Email verification and password change.
///
/// Split into its own service rather than added to SettingsApiService: these
/// are account-credential operations under /auth, not profile settings, and the
/// error codes matter to the caller in a way profile updates' do not.
class AccountSecurityApiService extends BaseApiService {
  AccountSecurityApiService({super.injectedDio});

  static const _base = '/api/v1/auth';

  /// Where the address stands and what may be done to it.
  ///
  /// `canChange` comes from the server rather than being derived from
  /// `verified` here — the rule lives in the change endpoint, and a second
  /// implementation of it on the client is how a UI offers a button the API
  /// refuses.
  Future<({String email, bool verified, bool canChange, int resendIn})>
  emailStatus() async {
    try {
      final res = await dio.get('$_base/email/status');
      final d = res.data as Map<String, dynamic>;
      return (
        email: d['email'] as String? ?? '',
        verified: d['verified'] as bool? ?? false,
        canChange: d['can_change'] as bool? ?? false,
        resendIn: d['resend_available_in'] as int? ?? 0,
      );
    } catch (e) {
      throw handleError(e);
    }
  }

  /// Ask for a fresh code. Returns null on success, or a message to show.
  Future<String?> sendVerificationCode() async {
    try {
      await dio.post('$_base/email/send');
      return null;
    } on DioException catch (e) {
      return _messageFrom(e) ?? 'Could not send a code just now.';
    } catch (_) {
      return 'Could not send a code just now.';
    }
  }

  /// Returns null when verified, or a message explaining why not.
  Future<String?> confirmCode(String code) async {
    try {
      await dio.post('$_base/email/confirm', data: {'code': code});
      return null;
    } on DioException catch (e) {
      return _messageFrom(e) ?? 'That code did not work.';
    } catch (_) {
      return 'That code did not work.';
    }
  }

  Future<String?> changeEmail(String email) async {
    try {
      await dio.post('$_base/email/change', data: {'email': email});
      return null;
    } on DioException catch (e) {
      return _messageFrom(e) ?? 'Could not change that address.';
    } catch (_) {
      return 'Could not change that address.';
    }
  }

  Future<String?> changePassword({
    required String current,
    required String next,
  }) async {
    try {
      await dio.post(
        '$_base/change-password',
        data: {'current_password': current, 'new_password': next},
      );
      return null;
    } on DioException catch (e) {
      return _messageFrom(e) ?? 'Could not change your password.';
    } catch (_) {
      return 'Could not change your password.';
    }
  }

  /// The server's own wording, when it has some.
  ///
  /// These endpoints answer with a `message` written for a person — "That is not
  /// your current password" — and surfacing it beats replacing it with a
  /// generic client-side string that says less.
  String? _messageFrom(DioException e) {
    final data = e.response?.data;
    if (data is Map && data['message'] is String) return data['message'] as String;
    return null;
  }
}
