import 'package:mobile/core/api_services/base_api_service.dart';
import 'package:mobile/features/history/models/session_history_model.dart';

class SessionHistoryApiService extends BaseApiService {
  SessionHistoryApiService({super.injectedDio});

  /// Fetches a paginated list of sessions for the authenticated user.
  ///
  /// [page] is 1-indexed. [filter] can be 'all', 'individual', 'joint', 'relay'.
  Future<Map<String, dynamic>> listSessions({
    int page = 1,
    String filter = 'all',
    int pageSize = 20,
  }) async {
    final queryParams = <String, dynamic>{
      'page': page,
      'page_size': pageSize,
    };
    if (filter != 'all') {
      queryParams['type'] = filter;
    }

    final response = await dio.get(
      '/api/v1/sessions',
      queryParameters: queryParams,
    );

    final data = response.data as Map<String, dynamic>;
    final rawResults = data['results'] ?? data['data'] ?? [];
    final List<SessionHistoryItem> items = (rawResults as List)
        .map((e) => SessionHistoryItem.fromJson(e as Map<String, dynamic>))
        .toList();

    return {
      'items': items,
      'hasMore': data['next'] != null,
      'count': data['count'] ?? items.length,
    };
  }

  /// Fetches the AI-generated summary and metadata for a specific session.
  Future<SessionDetail> getSessionSummary(String sessionId) async {
    final response = await dio.get('/api/v1/sessions/$sessionId/summary');
    return SessionDetail.fromJson(response.data as Map<String, dynamic>);
  }

  /// Fetches memories extracted from a specific session.
  Future<List<SessionMemory>> getSessionMemories(
    String userId,
    String sessionId,
  ) async {
    final response = await dio.get(
      '/api/v1/users/$userId/memories',
      queryParameters: {'session_id': sessionId},
    );
    final raw = response.data['results'] ?? response.data['data'] ?? [];
    return (raw as List)
        .map((e) => SessionMemory.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Updates (corrects) a specific memory inline.
  Future<SessionMemory> updateMemory(
    String userId,
    String memoryId,
    Map<String, dynamic> data,
  ) async {
    final response = await dio.put(
      '/api/v1/users/$userId/memories/$memoryId',
      data: data,
    );
    return SessionMemory.fromJson(response.data as Map<String, dynamic>);
  }

  /// Deletes a specific memory.
  Future<void> deleteMemory(String userId, String memoryId) async {
    await dio.delete('/api/v1/users/$userId/memories/$memoryId');
  }

  /// Bulk-deletes all memories extracted from a specific session.
  Future<void> deleteSessionMemories(String userId, String sessionId) async {
    await dio.delete(
      '/api/v1/users/$userId/memories',
      queryParameters: {'session_id': sessionId},
    );
  }
}
