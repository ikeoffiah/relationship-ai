import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:mobile/core/api_services/token_refresh_service.dart';
import 'package:mobile/core/security/certificate_config.dart';
import 'package:mobile/core/security/pinned_http_client.dart';
import 'package:mobile/core/services/storage_service.dart';

abstract class BaseApiService {
  late final Dio dio;

  /// If [injectedDio] is provided (e.g. in tests), it is used as-is.
  ///
  /// In release builds the service uses [PinnedHttpClient.create] which
  /// enforces TLS 1.3 and SPKI certificate pinning.  Debug builds fall back
  /// to the standard [Dio] so local development with self-signed certificates
  /// remains possible.
  /// [baseUrl] defaults to the Django REST host. Services that talk to the
  /// FastAPI host pass it explicitly.
  ///
  /// [receiveTimeout] may be set to null for streaming endpoints (SSE), where
  /// a fixed receive timeout would abort a healthy long-lived response.
  BaseApiService({
    Dio? injectedDio,
    String baseUrl = 'https://${CertConfig.djangoApiHost}',
    Duration? receiveTimeout = const Duration(seconds: 10),
  }) {
    final baseOptions = BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: receiveTimeout,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    );

    if (injectedDio != null) {
      dio = injectedDio;
    } else if (kReleaseMode) {
      // Release: hardened Dio — TLS 1.3 + certificate pinning enforced.
      dio = PinnedHttpClient.create(baseOptions: baseOptions);
    } else {
      // Debug / profile: plain Dio with request/response logging.
      dio = Dio(baseOptions);
      dio.interceptors.add(
        LogInterceptor(requestBody: true, responseBody: true),
      );
    }

    // Auth interceptor — always applied regardless of build mode.
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await StorageService.getToken();
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          return handler.next(options);
        },
        onError: (error, handler) async {
          // On a 401, try one token refresh and replay the request. The
          // 15-minute access token expires mid-session otherwise, and every
          // request would fail until the user logged out and back in.
          if (!_shouldAttemptRefresh(error)) {
            return handler.next(error);
          }

          final refreshed = await TokenRefreshService.refresh();
          if (!refreshed) {
            // Refresh itself failed — the session is genuinely over.
            return handler.next(error);
          }

          try {
            final response = await _retry(error.requestOptions);
            return handler.resolve(response);
          } on DioException catch (e) {
            return handler.next(e);
          }
        },
      ),
    );
  }

  /// Refresh only on a genuine 401, and never for the refresh call itself
  /// (which would loop), nor when the request was already a retry.
  bool _shouldAttemptRefresh(DioException error) {
    if (error.response?.statusCode != 401) return false;
    final path = error.requestOptions.path;
    if (path.contains('/auth/refresh')) return false;
    if (error.requestOptions.extra['__retried__'] == true) return false;
    return true;
  }

  Future<Response<dynamic>> _retry(RequestOptions options) {
    // The onRequest interceptor re-reads the (now refreshed) token.
    options.extra['__retried__'] = true;
    return dio.fetch(options);
  }

  /// Translates a [DioException] into a user-friendly [Exception].
  Exception handleError(dynamic e) {
    if (e is DioException) {
      final data = e.response?.data;
      String message = e.message ?? 'Unknown error';

      if (data != null && data is Map<String, dynamic>) {
        if (data.containsKey('message')) {
          message = data['message'];
        }
      }

      return Exception(message);
    }
    return Exception(e.toString());
  }
}
