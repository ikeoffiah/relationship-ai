import 'package:mobile/core/api_services/base_api_service.dart';

class JointSessionApiService extends BaseApiService {
  JointSessionApiService({super.injectedDio});

  Future<Map<String, dynamic>> initiateJointSession() async {
    final response = await dio.post('/api/v1/sessions/joint/initiate');
    return response.data;
  }

  Future<Map<String, dynamic>> confirmReady(String sessionId) async {
    final response = await dio.post('/api/v1/sessions/joint/$sessionId/confirm');
    return response.data;
  }

  Future<void> exitSession(String sessionId) async {
    await dio.post('/api/v1/sessions/joint/$sessionId/exit');
  }

  Future<Map<String, dynamic>> getSessionStatus(String sessionId) async {
    final response = await dio.get('/api/v1/sessions/joint/$sessionId/status');
    return response.data;
  }

  /// LiveKit room credentials for this joint session's video call.
  /// Returns {url, room, token}. Throws (503) if video isn't configured.
  Future<Map<String, dynamic>> fetchVideoToken(String sessionId) async {
    final response =
        await dio.post('/api/v1/sessions/joint/$sessionId/video-token');
    return response.data as Map<String, dynamic>;
  }
}
