import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class StorageService {
  static const _storage = FlutterSecureStorage();
  static const _tokenKey = 'auth_token';
  static const _userIdKey = 'user_id';

  /// Save auth token
  static Future<void> saveToken(String token) async {
    await _storage.write(key: _tokenKey, value: token);
  }

  /// Get auth token
  static Future<String?> getToken() async {
    return await _storage.read(key: _tokenKey);
  }

  /// Delete auth token
  static Future<void> deleteToken() async {
    await _storage.delete(key: _tokenKey);
  }

  /// Save user ID
  static Future<void> saveUserId(String userId) async {
    await _storage.write(key: _userIdKey, value: userId);
  }

  /// Get user ID
  static Future<String?> getUserId() async {
    return await _storage.read(key: _userIdKey);
  }

  /// Delete user ID
  static Future<void> deleteUserId() async {
    await _storage.delete(key: _userIdKey);
  }

  /// Clear all data
  static Future<void> clearAll() async {
    await _storage.deleteAll();
  }
}
