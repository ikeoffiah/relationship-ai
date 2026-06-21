import 'package:mobile/core/api_services/base_api_service.dart';
import 'package:mobile/features/consent/models/consent_model.dart';

class ConsentApiService extends BaseApiService {
  ConsentApiService({super.injectedDio});

  /// Fetches the current full consent state for the authenticated user.
  Future<ConsentModel> fetchConsent(String userId) async {
    final response = await dio.get('/api/v1/users/$userId/consent');
    return ConsentModel.fromJson(response.data);
  }

  /// Fetches the history of consent updates.
  Future<List<Map<String, dynamic>>> fetchConsentHistory(String userId) async {
    final response = await dio.get('/api/v1/users/$userId/consent/history');
    return List<Map<String, dynamic>>.from(response.data['results'] ?? response.data['history'] ?? []);
  }

  /// Updates one or more consent dimensions for the authenticated user.
  Future<ConsentModel> updateConsent(String userId, Map<String, dynamic> data) async {
    final response = await dio.put('/api/v1/users/$userId/consent', data: data);
    return ConsentModel.fromJson(response.data);
  }

  /// Logs that the consent summary was shown to the user.
  Future<void> logConsentSummaryShown(String userId) async {
    await dio.post('/api/v1/audit/log', data: {
      'event_type': 'session_consent_summary_shown',
      'user_id': userId,
    });
  }

  /// Fetches memories for the transparency panel.
  Future<List<Map<String, dynamic>>> fetchMemories(String userId) async {
    final response = await dio.get('/api/v1/users/$userId/memory');
    return List<Map<String, dynamic>>.from(response.data['results'] ?? response.data['data'] ?? []);
  }

  /// Updates a specific memory.
  Future<void> updateMemory(String userId, String memoryId, Map<String, dynamic> data) async {
    await dio.put('/api/v1/users/$userId/memory/$memoryId', data: data);
  }

  /// Deletes a specific memory.
  Future<void> deleteMemory(String userId, String memoryId) async {
    await dio.delete('/api/v1/users/$userId/memory/$memoryId');
  }
}
