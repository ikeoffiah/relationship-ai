import 'package:mobile/core/api_services/dio_exceptions.dart';
import 'package:dio/dio.dart';

Dio _dio = Dio();

/// Base request templates for API calls.
///
/// This file contains utility functions for making HTTP requests,
/// including authenticated POST calls.

// Post Requests

/// Performs an authenticated POST request with form data.
///
/// [url] The endpoint URL.
/// [data] The form data to send.
/// [authToken] The authentication token.
/// Returns a [Map] containing the response data.
Future<Map<String, dynamic>> basePostFormCallAuth(
  String url,
  FormData data,
  String authToken,
) async {
  try {
    _dio.options.contentType = Headers.jsonContentType;
    _dio.options.headers["Authorization"] = "Bearer $authToken";
    final Response responseData = await _dio.post(url, data: data);
    final Map<String, dynamic> respondsData =
        responseData.data as Map<String, dynamic>;
    respondsData['status'] = responseData.statusCode;
    return respondsData;
  } on DioException catch (e) {
    final DioExceptions errorMsg = DioExceptions.fromDioException(e);
    return errorMsg.errorData;
  }
}

/// Performs an authenticated POST request without data.
///
/// [url] The endpoint URL.
/// [authToken] The authentication token.
/// Returns a [Map] containing the response data.
Future<Map<String, dynamic>> basePostWithoutDataAuth(
  String url,
  String authToken,
) async {
  try {
    _dio.options.contentType = Headers.jsonContentType;
    _dio.options.headers["Authorization"] = "Bearer $authToken";
    final Response responseData = await _dio.post(url);
    final Map<String, dynamic> respondsData =
        responseData.data as Map<String, dynamic>;
    respondsData['status'] = responseData.statusCode;
    return respondsData;
  } on DioException catch (e) {
    final DioExceptions errorMsg = DioExceptions.fromDioException(e);
    return errorMsg.errorData;
  }
}

/// Performs an authenticated POST request with JSON data.
///
/// [url] The endpoint URL.
/// [data] The JSON data to send.
/// [authToken] The authentication token.
/// Returns a [Map] containing the response data.
Future<Map<String, dynamic>> basePostCallAuth(
  String url,
  Map<String, dynamic> data,
  String authToken,
) async {
  try {
    _dio.options.contentType = Headers.jsonContentType;
    _dio.options.headers["Authorization"] = "Bearer $authToken";
    final Response responseData = await _dio.post(url, data: data);
    final Map<String, dynamic> respondsData =
        responseData.data as Map<String, dynamic>;
    respondsData['status'] = responseData.statusCode;
    return respondsData;
  } on DioException catch (e) {
    final DioExceptions errorMsg = DioExceptions.fromDioException(e);
    return errorMsg.errorData;
  }
}

/// Performs a POST request without authentication.
///
/// [url] The endpoint URL.
/// [data] The JSON data to send.
/// Returns a [Map] containing the response data.
Future<Map<String, dynamic>> basePostCallNoAuth(
  String url,
  Map<String, dynamic> data,
) async {
  try {
    _dio.options.contentType = Headers.jsonContentType;

    final Response responseData = await _dio.post(url, data: data);
    final Map<String, dynamic> respondsData =
        responseData.data as Map<String, dynamic>;
    respondsData['status'] = responseData.statusCode;

    return respondsData;
  } on DioException catch (e) {
    final DioExceptions errorMsg = DioExceptions.fromDioException(e);

    return errorMsg.errorData;
  }
}

// Put Requests

/// Performs an authenticated PUT request with JSON data.
///
/// [url] The endpoint URL.
/// [data] The JSON data to send.
/// [authToken] The authentication token.
/// Returns a [Map] containing the response data.
Future<Map<String, dynamic>> basePutCall(
  String url,
  Map<String, dynamic> data,
  String authToken,
) async {
  try {
    _dio.options.contentType = Headers.jsonContentType;
    _dio.options.headers["Authorization"] = "Bearer $authToken";
    final Response responseData = await _dio.put(url, data: data);
    final Map<String, dynamic> respondsData =
        responseData.data as Map<String, dynamic>;
    respondsData['status'] = responseData.statusCode;
    return respondsData;
  } on DioException catch (e) {
    final DioExceptions errorMsg = DioExceptions.fromDioException(e);
    return errorMsg.errorData;
  }
}

/// Performs a PUT request without authentication.
///
/// [url] The endpoint URL.
/// [data] The JSON data to send.
/// Returns a [Map] containing the response data.
Future<Map<String, dynamic>> basePutNoAuthCall(
  String url,
  Map<String, dynamic> data,
) async {
  try {
    _dio.options.contentType = Headers.jsonContentType;

    final Response responseData = await _dio.put(url, data: data);
    final Map<String, dynamic> respondsData =
        responseData.data as Map<String, dynamic>;
    respondsData['status'] = responseData.statusCode;
    return respondsData;
  } on DioException catch (e) {
    final DioExceptions errorMsg = DioExceptions.fromDioException(e);
    return errorMsg.errorData;
  }
}

/// Performs an authenticated PUT request without data.
///
/// [url] The endpoint URL.
/// [authToken] The authentication token.
/// Returns a [Map] containing the response data.
Future<Map<String, dynamic>> basePutCallAuthNoData(
  String url,
  String authToken,
) async {
  try {
    _dio.options.contentType = Headers.jsonContentType;
    _dio.options.headers["Authorization"] = "Bearer $authToken";
    final Response responseData = await _dio.put(url);
    final Map<String, dynamic> respondsData =
        responseData.data as Map<String, dynamic>;
    respondsData['status'] = responseData.statusCode;
    return respondsData;
  } on DioException catch (e) {
    final DioExceptions errorMsg = DioExceptions.fromDioException(e);
    return errorMsg.errorData;
  }
}

// Get request

/// Performs an authenticated GET request.
///
/// [url] The endpoint URL.
/// [authToken] The authentication token.
/// Returns a [Map] containing the response data.
Future<Map<String, dynamic>> baseGetCallAuth(
  String url,
  String authToken,
) async {
  try {
    _dio.options.contentType = Headers.jsonContentType;
    _dio.options.headers["Authorization"] = "Bearer $authToken";
    final Response responseData = await _dio.get(url);

    final Map<String, dynamic> respondsData =
        responseData.data as Map<String, dynamic>;
    respondsData['status'] = responseData.statusCode;

    return respondsData;
  } on DioException catch (e) {
    final DioExceptions errorMsg = DioExceptions.fromDioException(e);
    return errorMsg.errorData;
  }
}

/// Performs a GET request without authentication.
///
/// [url] The endpoint URL.
/// Returns a [Map] containing the response data.
Future<Map<String, dynamic>> baseGetCallNoAuth(String url) async {
  try {
    _dio.options.contentType = Headers.jsonContentType;

    final Response responseData = await _dio.get(url);
    final Map<String, dynamic> respondsData =
        responseData.data as Map<String, dynamic>;
    respondsData['status'] = responseData.statusCode;

    return respondsData;
  } on DioException catch (e) {
    final DioExceptions errorMsg = DioExceptions.fromDioException(e);

    return errorMsg.errorData;
  }
}

//Patch request

/// Performs an authenticated PATCH request with JSON data.
///
/// [url] The endpoint URL.
/// [data] The JSON data to send.
/// [authToken] The authentication token.
/// Returns a [Map] containing the response data.
Future<Map<String, dynamic>> basePatchCallAuth(
  String url,
  Map<String, dynamic> data,
  String authToken,
) async {
  try {
    _dio.options.contentType = Headers.jsonContentType;
    _dio.options.headers["Authorization"] = "Bearer $authToken";
    final Response responseData = await _dio.patch(url, data: data);
    final Map<String, dynamic> respondsData =
        responseData.data as Map<String, dynamic>;
    respondsData['status'] = responseData.statusCode;
    return respondsData;
  } on DioException catch (e) {
    final DioExceptions errorMsg = DioExceptions.fromDioException(e);
    return errorMsg.errorData;
  }
}

/// Performs a PATCH request without authentication.
///
/// [url] The endpoint URL.
/// [data] The JSON data to send.
/// Returns a [Map] containing the response data.
Future<Map<String, dynamic>> basePatchNoAuthCall(
  String url,
  Map<String, dynamic> data,
) async {
  try {
    _dio.options.contentType = Headers.jsonContentType;

    final Response responseData = await _dio.patch(url, data: data);
    final Map<String, dynamic> respondsData =
        responseData.data as Map<String, dynamic>;
    respondsData['status'] = responseData.statusCode;
    return respondsData;
  } on DioException catch (e) {
    final DioExceptions errorMsg = DioExceptions.fromDioException(e);
    return errorMsg.errorData;
  }
}

/// Performs an authenticated PATCH request without data.
///
/// [url] The endpoint URL.
/// [authToken] The authentication token.
/// Returns a [Map] containing the response data.
Future<Map<String, dynamic>> basePatchCallAuthNoData(
  String url,
  String authToken,
) async {
  try {
    _dio.options.contentType = Headers.jsonContentType;
    _dio.options.headers["Authorization"] = "Bearer $authToken";
    final Response responseData = await _dio.patch(url);
    final Map<String, dynamic> respondsData =
        responseData.data as Map<String, dynamic>;
    respondsData['status'] = responseData.statusCode;
    return respondsData;
  } on DioException catch (e) {
    final DioExceptions errorMsg = DioExceptions.fromDioException(e);
    return errorMsg.errorData;
  }
}

/// Performs a PATCH request without authentication and without data.
///
/// [url] The endpoint URL.
/// Returns a [Map] containing the response data.
Future<Map<String, dynamic>> basePatchNoAuthCallNoData(String url) async {
  try {
    _dio.options.contentType = Headers.jsonContentType;

    final Response responseData = await _dio.patch(url);
    final Map<String, dynamic> respondsData =
        responseData.data as Map<String, dynamic>;
    respondsData['status'] = responseData.statusCode;
    return respondsData;
  } on DioException catch (e) {
    final DioExceptions errorMsg = DioExceptions.fromDioException(e);
    return errorMsg.errorData;
  }
}
