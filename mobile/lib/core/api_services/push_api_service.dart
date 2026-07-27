import 'base_api_service.dart';

/// Registers this device's FCM token with the backend so it can receive push.
/// Talks to the Django host (inherits JWT + pinning from [BaseApiService]).
class PushApiService extends BaseApiService {
  PushApiService({super.injectedDio});

  /// Store/refresh the caller's device token. Requires an authenticated session
  /// (the interceptor attaches the JWT).
  Future<void> registerToken(String token) async {
    try {
      await dio.post('/api/v1/users/fcm-token/', data: {'token': token});
    } catch (e) {
      throw handleError(e);
    }
  }
}
