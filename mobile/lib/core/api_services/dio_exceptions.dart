import 'dart:developer';

import 'package:dio/dio.dart';

/// Handles exceptions from Dio HTTP requests.
class DioExceptions implements Exception {
  /// Creates a [DioExceptions] instance from a [DioException].
  DioExceptions.fromDioException(DioException dioException) {
    switch (dioException.type) {
      case DioExceptionType.cancel:
        errorData["userMsg"] = 'Request to API server was cancelled';
        errorData["status"] = 503;
      case DioExceptionType.connectionTimeout:
        errorData["userMsg"] = 'Connection timeout with API server';
        errorData["status"] = 503;
      case DioExceptionType.unknown:
        errorData["userMsg"] = "Connection failed";
        errorData["status"] = 503;
      case DioExceptionType.receiveTimeout:
        errorData["userMsg"] = "Receive timeout in connection with API server";
        errorData["status"] = 503;
      case DioExceptionType.connectionError:
        errorData["userMsg"] =
            "Connection failed check your internet connection";
        errorData["status"] = 503;
      case DioExceptionType.sendTimeout:
        errorData["userMsg"] = "Send timeout in connection with API server";
        errorData["status"] = 503;
      case DioExceptionType.badCertificate:
        errorData["userMsg"] = "Bad SSL certificate";
        errorData["status"] = 503;
      case DioExceptionType.badResponse:
        errorData = _handleError(dioException.response!);
    }
  }

  /// Stores error data including user message and status code.
  late Map<String, dynamic> errorData = <String, dynamic>{};

  /// Processes the error response and returns a formatted error map.
  Map<String, dynamic> _handleError(Response<dynamic> response) {
    if (response.statusCode != 200) {
      if (response.statusCode == 403) {
        final Map<String, dynamic> errorData =
            response.data as Map<String, dynamic>;
        errorData['status'] = response.statusCode;
        errorData['userMsg'] = errorData['detail'];

        return errorData;
      }
      if (response.statusCode == 422) {
        final Map<String, dynamic> errorData =
            response.data as Map<String, dynamic>;
        errorData['status'] = response.statusCode;
        errorData['userMsg'] = errorData['detail'][0]['msg'];
        return errorData;
      } else if (response.statusCode == 500) {
        final Map<String, dynamic> errorData = <String, dynamic>{};
        log(response.toString());
        errorData['userMsg'] = response.data['userMsg'] ?? 'Server error';
        errorData['status'] = 500;

        return errorData;
      } else if (response.data is Map<String, dynamic>) {
        final Map<String, dynamic> errorData =
            response.data as Map<String, dynamic>;
        errorData['status'] = response.statusCode;
        return errorData;
      } else {
        return <String, dynamic>{
          "userMsg": 'Oops something went wrong',
          "status": response.statusCode,
        };
      }
    } else {
      return <String, dynamic>{
        "userMsg": 'Oops something went wrong',
        "status": response.statusCode,
      };
    }
  }
}
