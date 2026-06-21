import 'package:mobile/core/api_services/base_api_service.dart';

class CounselingApiService extends BaseApiService {
  CounselingApiService({super.injectedDio});

  Future<void> endSession(String sessionId) async {
    await dio.post(
      '/api/counseling/sessions/end/',
      data: {'session_id': sessionId},
    );
  }
}
