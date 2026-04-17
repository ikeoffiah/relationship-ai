import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/auth/models/user_profile.dart';
import 'package:mobile/features/auth/models/responses/auth_response.dart';

void main() {
  group('UserProfile Tests', () {
    test('toJson creates correct map', () {
      const profile = UserProfile(
        id: '1',
        name: 'Test',
        email: 'test@example.com',
        avatarUrl: 'http://example.com',
      );
      
      final json = profile.toJson();
      
      expect(json['id'], '1');
      expect(json['name'], 'Test');
      expect(json['email'], 'test@example.com');
      expect(json['avatarUrl'], 'http://example.com');
    });

    test('fromJson parses correctly', () {
      final json = {
        'id': '1',
        'name': 'Test',
        'email': 'test@example.com',
        'avatarUrl': 'http://example.com',
      };
      
      final profile = UserProfile.fromJson(json);
      
      expect(profile.id, '1');
      expect(profile.name, 'Test');
      expect(profile.email, 'test@example.com');
      expect(profile.avatarUrl, 'http://example.com');
    });

    test('sample returns valid const profile', () {
      final profile = UserProfile.sample;
      expect(profile.id, '1');
      expect(profile.name, 'Test User');
    });
  });

  group('AuthResponse Tests', () {
    test('fromJson parses full data correctly', () {
      final json = {
        'token': 'super_secret',
        'user': {
          'id': '1',
          'name': 'Test',
          'email': 'test@example.com',
          'avatarUrl': null,
        }
      };
      
      final response = AuthResponse.fromJson(json);
      
      expect(response.token, 'super_secret');
      expect(response.user?.id, '1');
      expect(response.user?.name, 'Test');
    });

    test('fromJson parses null user correctly', () {
      final json = {
        'token': 'hello',
        'user': null
      };
      
      final response = AuthResponse.fromJson(json);
      
      expect(response.token, 'hello');
      expect(response.user, null);
    });
  });
}
