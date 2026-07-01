import 'package:mobile/features/auth/models/user_profile.dart';

class AuthResponse {
  final UserProfile? user;
  final String? token;

  AuthResponse({this.user, this.token});

  factory AuthResponse.fromJson(Map<String, dynamic> json) {
    return AuthResponse(
      user: json['user'] != null ? UserProfile.fromJson(json['user']) : null,
      token: json['token'],
    );
  }
}
