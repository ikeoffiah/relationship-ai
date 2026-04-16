import 'package:dio/dio.dart';
import 'package:mobile/core/api_services/base_api_service.dart';
import 'package:mobile/features/consent/models/consent_model.dart';

/// API service for reading and updating user consent state.
///
/// Consent data is NEVER cached — every call fetches fresh from the server
/// per Section 4.2 of the architecture spec.
class ConsentApiService extends BaseApiService {
  ConsentApiService({super.injectedDio});

  /// Fetches the current consent state for [userId].
  ///
  /// Maps to: GET /api/v1/users/{id}/consent
  /// Always performs a live network request — caching is forbidden for consent.
  Future<ConsentModel> fetchConsent(String userId) async {
    try {
      final response = await dio.get(
        '/api/v1/users/$userId/consent',
        options: Options(
          // Explicitly disable any HTTP caching headers
          headers: {
            'Cache-Control': 'no-cache, no-store',
            'Pragma': 'no-cache',
          },
        ),
      );
      return ConsentModel.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  /// Partially updates the consent record for [userId].
  ///
  /// Maps to: PUT /api/v1/users/{id}/consent
  /// [fields] should be a partial map, e.g. {'therapist_summary_access': true}
  Future<ConsentModel> updateConsent(
    String userId,
    Map<String, dynamic> fields,
  ) async {
    try {
      final response = await dio.put(
        '/api/v1/users/$userId/consent',
        data: fields,
      );
      return ConsentModel.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }
}
