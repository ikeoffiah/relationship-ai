import 'package:mobile/features/auth/models/user_profile.dart';

class AuthResponse {
  final UserProfile? user;
  final String? token;
  final String? refreshToken;

  AuthResponse({this.user, this.token, this.refreshToken});

  factory AuthResponse.fromJson(Map<String, dynamic> json) {
    return AuthResponse(
      user: json['user'] != null ? UserProfile.fromJson(json['user']) : null,
      // Django issues `access_token`/`refresh_token` (accounts/views.py:36,64).
      token: json['access_token'] as String?,
      refreshToken: json['refresh_token'] as String?,
    );
  }
}
