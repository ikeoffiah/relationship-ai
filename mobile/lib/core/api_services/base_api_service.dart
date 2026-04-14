import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:mobile/core/services/storage_service.dart';

abstract class BaseApiService {
  late final Dio dio;

  BaseApiService({Dio? injectedDio}) {
    dio = injectedDio ?? Dio(
      BaseOptions(
        baseUrl: 'http://localhost:8000',
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    if (injectedDio == null && kDebugMode) {
      dio.interceptors.add(
        LogInterceptor(requestBody: true, responseBody: true),
      );
    }

    // Add Auth Interceptor
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

  /// Handle Dio errors and return a user-friendly exception
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
