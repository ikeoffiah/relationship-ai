import 'package:mobile/features/auth/models/responses/auth_response.dart';
import 'package:mobile/core/api_services/base_api_service.dart';

class AuthApiService extends BaseApiService {
  AuthApiService({super.injectedDio});
  Future<AuthResponse> login(String email, String password) async {
    try {
      final response = await dio.post(
        '/auth/login',
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
        '/auth/signup',
        data: {'name': name, 'email': email, 'password': password},
      );
      return AuthResponse.fromJson(response.data);
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<AuthResponse> googleSignIn(String idToken) async {
    try {
      final response = await dio.post(
        '/auth/google',
        data: {'id_token': idToken},
      );
      return AuthResponse.fromJson(response.data);
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<void> logout() async {
    try {
      await dio.post('/auth/logout');
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<void> forgotPassword(String email) async {
    try {
      await dio.post('/auth/forgot-password', data: {'email': email});
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<void> resetPassword(String newPassword, String token) async {
    try {
      await dio.post(
        '/auth/reset-password',
        data: {'new_password': newPassword, 'token': token},
      );
    } catch (e) {
      throw handleError(e);
    }
  }
}
