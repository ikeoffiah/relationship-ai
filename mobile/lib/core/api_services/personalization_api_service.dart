import 'package:dio/dio.dart';
import 'package:mobile/core/api_services/base_api_service.dart';

class PersonalizationApiService extends BaseApiService {
  PersonalizationApiService({super.injectedDio});

  /// Fetches the full questionnaire definition (RSQ items, stages, comm quiz).
  Future<Map<String, dynamic>> fetchQuestionnaire() async {
    try {
      final response = await dio.get('/api/v1/personalization/questionnaire');
      return response.data as Map<String, dynamic>;
    } catch (e) {
      throw handleError(e);
    }
  }

  /// Fetches the current user's personalization profile.
  Future<Map<String, dynamic>> fetchProfile() async {
    try {
      final response = await dio.get('/api/v1/personalization/profile');
      return response.data as Map<String, dynamic>;
    } catch (e) {
      throw handleError(e);
    }
  }

  /// Submits partial or full onboarding data (PATCH semantics).
  Future<Map<String, dynamic>> submitProfile(Map<String, dynamic> data) async {
    try {
      final response = await dio.post(
        '/api/v1/personalization/profile',
        data: data,
      );
      return response.data as Map<String, dynamic>;
    } catch (e) {
      throw handleError(e);
    }
  }
}
