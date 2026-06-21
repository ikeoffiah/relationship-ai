import 'package:mobile/core/api_services/base_api_service.dart';

class RelationshipApiService extends BaseApiService {
  RelationshipApiService({super.injectedDio});

  Future<Map<String, dynamic>> invitePartner(String email) async {
    try {
      final response = await dio.post(
        '/v1/relationships/invite',
        data: {'invitee_email': email},
      );
      return response.data;
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<Map<String, dynamic>> acceptInvite(String token) async {
    try {
      final response = await dio.post(
        '/v1/relationships/accept/$token',
      );
      return response.data;
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<void> declineInvite(String token) async {
    try {
      await dio.post('/v1/relationships/decline/$token');
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<Map<String, dynamic>> getMyRelationship() async {
    try {
      final response = await dio.get('/v1/relationships/me');
      return response.data;
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<void> dissolveRelationship(String relationshipId) async {
    try {
      await dio.delete('/v1/relationships/$relationshipId');
    } catch (e) {
      throw Exception('Failed to dissolve relationship');
    }
  }

  // --- Shared Context API (REL-65) ---

  Future<Map<String, dynamic>> getSharedContext(String relationshipId) async {
    try {
      // Points to FastAPI service
      final response = await dio.get('https://ws.relationshipai.com/api/v1/relationships/$relationshipId/context');
      return response.data;
    } catch (e) {
      return {};
    }
  }

  Future<void> addRepairEvent(String relationshipId, String description, String sessionId) async {
    try {
      await dio.put(
        'https://ws.relationshipai.com/api/v1/relationships/$relationshipId/context/repairs',
        data: {
          'event_id': DateTime.now().millisecondsSinceEpoch.toString(),
          'description': description,
          'session_id': sessionId,
        },
      );
    } catch (e) {
      throw Exception('Failed to log repair event');
    }
  }

  Future<void> addConflictEvent(String relationshipId, String description, String sessionId) async {
    try {
      await dio.put(
        'https://ws.relationshipai.com/api/v1/relationships/$relationshipId/context/conflicts',
        data: {
          'event_id': DateTime.now().millisecondsSinceEpoch.toString(),
          'description': description,
          'session_id': sessionId,
        },
      );
    } catch (e) {
      throw Exception('Failed to log conflict event');
    }
  }

  Future<void> addGoal(String relationshipId, String description) async {
    try {
      await dio.put(
        'https://ws.relationshipai.com/api/v1/relationships/$relationshipId/context/goals',
        data: {
          'goal_id': DateTime.now().millisecondsSinceEpoch.toString(),
          'description': description,
        },
      );
    } catch (e) {
      throw Exception('Failed to add goal');
    }
  }

  Future<void> updateStructuralFacts(String relationshipId, Map<String, dynamic> facts) async {
    try {
      await dio.put(
        'https://ws.relationshipai.com/api/v1/relationships/$relationshipId/context/structural',
        data: facts,
      );
    } catch (e) {
      throw Exception('Failed to update structural facts');
    }
  }
}
