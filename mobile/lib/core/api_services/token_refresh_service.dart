import 'dart:async';

import 'package:flutter/foundation.dart';

import 'package:dio/dio.dart';
import 'package:mobile/core/security/certificate_config.dart';
import 'package:mobile/core/services/storage_service.dart';

/// Refreshes the access token against Django's rotating refresh endpoint.
///
/// The access token lives 15 minutes (accounts/auth.py), so without this the
/// session silently dies. Refresh is single-flight: many requests can 401 at
/// once, but only one network refresh runs and the rest await its result,
/// which also avoids racing the token rotation.
class TokenRefreshService {
  TokenRefreshService._();

  /// The in-flight refresh, if any. Shared so concurrent 401s coalesce.
  static Future<bool>? _inFlight;

  /// A bare Dio with no auth interceptor — refreshing must not recurse through
  /// the interceptor that triggered it.
  static Dio _dio = Dio(
    BaseOptions(
      baseUrl: 'https://${CertConfig.djangoApiHost}',
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
      headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
    ),
  );

  /// For tests: clear any coalesced in-flight refresh so cases don't leak
  /// state into each other, and optionally swap the internal Dio so a 401
  /// through the interceptor drives a controllable refresh.
  @visibleForTesting
  static void debugReset({Dio? dio}) {
    _inFlight = null;
    if (dio != null) _dio = dio;
  }

  /// Attempt to refresh the access token. Returns true on success. Safe to
  /// call concurrently — callers share a single underlying request.
  static Future<bool> refresh({Dio? client}) {
    return _inFlight ??= _doRefresh(client ?? _dio).whenComplete(() {
      _inFlight = null;
    });
  }

  static Future<bool> _doRefresh(Dio client) async {
    final refreshToken = await StorageService.getRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) return false;

    try {
      final res = await client.post(
        '/api/v1/auth/refresh/',
        data: {'refresh_token': refreshToken},
      );

      final data = res.data;
      if (data is! Map) return false;

      final access = data['access_token'] as String?;
      final rotated = data['refresh_token'] as String?;
      if (access == null || rotated == null) return false;

      // Persist the rotated pair before returning; the old refresh token is
      // now dead.
      await StorageService.saveToken(access);
      await StorageService.saveRefreshToken(rotated);
      return true;
    } on DioException {
      // A rejected refresh (expired, reused, revoked family) is terminal —
      // the caller should surface a re-login rather than retry.
      return false;
    }
  }
}
