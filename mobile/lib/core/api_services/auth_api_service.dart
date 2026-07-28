import 'package:mobile/features/auth/models/responses/auth_response.dart';
import 'package:mobile/features/auth/models/user_profile.dart';
import 'package:mobile/core/api_services/base_api_service.dart';

class AuthApiService extends BaseApiService {
  AuthApiService({super.injectedDio});

  /// Fetch the currently-authenticated user, validating the stored access
  /// token (the base client auto-refreshes on a 401 using the refresh token).
  Future<UserProfile> me() async {
    try {
      final response = await dio.get('/api/v1/auth/me/');
      return UserProfile.fromJson(response.data);
    } catch (e) {
      throw handleError(e);
    }
  }
  Future<AuthResponse> login(String email, String password) async {
    try {
      final response = await dio.post(
        '/api/v1/auth/login/',
        data: {'email': email, 'password': password},
      );
      return AuthResponse.fromJson(response.data);
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<AuthResponse> signup(
    String name,
    String email,
    String password,
  ) async {
    try {
      final response = await dio.post(
        '/api/v1/auth/signup/',
        data: {'full_name': name, 'email': email, 'password': password},
      );
      return AuthResponse.fromJson(response.data);
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<AuthResponse> googleSignIn(String idToken) async {
    try {
      final response = await dio.post(
        '/api/v1/auth/google/',
        data: {'id_token': idToken},
      );
      return AuthResponse.fromJson(response.data);
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<void> logout() async {
    try {
      await dio.post('/api/v1/auth/logout/');
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<void> forgotPassword(String email) async {
    try {
      await dio.post('/api/v1/auth/forgot-password/', data: {'email': email});
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<void> resetPassword(String newPassword, String token, String email) async {
    try {
      await dio.post(
        '/api/v1/auth/reset-password/',
        // The backend's ResetPasswordView reads `email` alongside token +
        // new_password to look up the user, so all three must be sent.
        data: {'new_password': newPassword, 'token': token, 'email': email},
      );
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<Map<String, dynamic>> verifyAge(DateTime dob) async {
    try {
      final response = await dio.post(
        '/api/v1/auth/verify-age/',
        data: {
          'dob': dob.toIso8601String().split('T')[0], // YYYY-MM-DD
        },
      );
      return response.data;
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<void> submitGuardianEmail(String guardianEmail) async {
    try {
      await dio.post(
        '/api/v1/auth/guardian-consent/',
        data: {'guardian_email': guardianEmail},
      );
    } catch (e) {
      throw handleError(e);
    }
  }
}
