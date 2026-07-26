import '../../core/api_services/base_api_service.dart';
import 'focus_models.dart';

/// API client for consensual Focus Mode (Django host). Extends [BaseApiService]
/// for JWT injection, refresh and pinning.
class FocusApiService extends BaseApiService {
  FocusApiService({super.injectedDio});

  static const _base = '/api/v1/engagement/focus';

  /// The couple's current session, or null when there is none.
  Future<FocusSession?> current() => _sessionFrom(() => dio.get(_base));

  Future<FocusSession?> propose(int durationMinutes) =>
      _sessionFrom(() => dio.post('$_base/propose', data: {'duration_minutes': durationMinutes}));

  Future<FocusSession?> accept() => _sessionFrom(() => dio.post('$_base/accept'));

  Future<FocusSession?> decline() => _sessionFrom(() => dio.post('$_base/decline'));

  Future<FocusSession?> end() => _sessionFrom(() => dio.post('$_base/end'));

  Future<FocusSession?> _sessionFrom(Future Function() call) async {
    try {
      final res = await call();
      final session = res.data['session'];
      return session == null ? null : FocusSession.fromJson(session as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }
}
