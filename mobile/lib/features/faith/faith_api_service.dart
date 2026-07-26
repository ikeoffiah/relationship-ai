import '../../core/api_services/base_api_service.dart';
import 'faith_models.dart';

/// API client for the opt-in faith endpoints (Django host). Extends
/// [BaseApiService] for JWT injection, refresh and pinning.
class FaithApiService extends BaseApiService {
  FaithApiService({super.injectedDio});

  static const _base = '/api/v1/engagement/faith';

  Future<FaithToday> fetchToday() async {
    try {
      final res = await dio.get('$_base/today');
      return FaithToday.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  /// Check off one practice for today. Returns points awarded (0 if already done).
  Future<int> completePractice(String practiceKey) async {
    try {
      final res = await dio.post(
        '$_base/practices/complete',
        data: {'practice_key': practiceKey},
      );
      return (res.data['points_awarded'] as int?) ?? 0;
    } catch (e) {
      throw handleError(e);
    }
  }

  /// Save a private reflection on today's reading. Returns points awarded.
  Future<int> reflect(String text) async {
    try {
      final res = await dio.post('$_base/reflect', data: {'text': text});
      return (res.data['points_awarded'] as int?) ?? 0;
    } catch (e) {
      throw handleError(e);
    }
  }
}
