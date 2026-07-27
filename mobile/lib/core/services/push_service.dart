import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';

import '../api_services/push_api_service.dart';

/// Wires Firebase Cloud Messaging to the app: asks permission, registers this
/// device's token with the backend, and keeps it fresh on rotation.
///
/// Every Firebase call is guarded — if Firebase isn't configured/initialized
/// (e.g. missing native config), this degrades to a no-op instead of crashing,
/// so the rest of the app is unaffected. Call [register] once the user is
/// authenticated (the token POST needs the session JWT).
class PushService {
  PushService({PushApiService? api, FirebaseMessaging? messaging})
      : _api = api ?? PushApiService(),
        _injectedMessaging = messaging;

  final PushApiService _api;
  // Resolved lazily inside register() — touching FirebaseMessaging.instance
  // before Firebase is initialized throws, so it must stay out of the
  // constructor (which runs at import time / in tests).
  final FirebaseMessaging? _injectedMessaging;
  bool _started = false;

  /// Idempotent: safe to call on every authenticated app-open.
  Future<void> register() async {
    if (_started) return;
    _started = true;
    try {
      final messaging = _injectedMessaging ?? FirebaseMessaging.instance;
      await messaging.requestPermission(); // iOS prompt; Android <13 is a no-op
      final token = await messaging.getToken();
      if (token != null && token.isNotEmpty) {
        await _sendToken(token);
      }
      // Re-register whenever FCM rotates the token.
      messaging.onTokenRefresh.listen(_sendToken);
    } catch (e) {
      // No Firebase config, no network, permission denied — all non-fatal.
      _started = false; // allow a later retry
      debugPrint('PushService.register skipped: $e');
    }
  }

  Future<void> _sendToken(String token) async {
    try {
      await _api.registerToken(token);
    } catch (e) {
      debugPrint('PushService token registration failed: $e');
    }
  }
}

/// App-wide instance; call `pushService.register()` once authenticated.
final PushService pushService = PushService();

