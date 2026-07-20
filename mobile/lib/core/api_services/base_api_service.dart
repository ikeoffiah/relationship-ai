import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
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
      ),
    );
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
