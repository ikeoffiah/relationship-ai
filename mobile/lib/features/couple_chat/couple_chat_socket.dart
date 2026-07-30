import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:mobile/core/security/certificate_config.dart';
import 'package:mobile/core/services/storage_service.dart';

/// Live delivery for the couple's thread.
///
/// Deliberately receive-only. Messages are sent over HTTP so they are persisted
/// before anything is rendered anywhere; this socket only carries what the
/// server pushes back. A dropped connection therefore costs a moment of
/// liveness, never a message — which is the failure a chat cannot afford.
///
/// Uses `dart:io`'s WebSocket rather than a package: the app is iOS/Android
/// only, and this avoids taking a dependency for one connection.
class CoupleChatSocket {
  final String relationshipId;

  /// Called for every event the server pushes. The caller decides what each
  /// type means; this class does no interpretation of its own.
  final void Function(Map<String, dynamic> event) onEvent;

  /// Called when the connection drops. Presence has to fall back to "unknown,
  /// so assume offline" here — a socket we no longer hold cannot tell us the
  /// partner left, so without this the app would keep showing a stale "Online"
  /// for as long as the reconnect backoff lasts.
  final VoidCallback? onConnectionLost;

  WebSocket? _socket;
  StreamSubscription<dynamic>? _subscription;
  Timer? _reconnect;
  Timer? _heartbeat;
  bool _disposed = false;

  /// The server treats an inbound frame as proof this socket is still alive and
  /// pushes the presence key's expiry out. Comfortably inside the server's
  /// 90-second window, so one dropped beat does not read as "went offline".
  static const _heartbeatInterval = Duration(seconds: 30);

  /// Backoff between reconnection attempts, capped so a long outage doesn't
  /// leave the thread silently dead once the network returns.
  static const _initialBackoff = Duration(seconds: 2);
  static const _maxBackoff = Duration(seconds: 30);
  Duration _backoff = _initialBackoff;

  /// How the socket is opened. Injectable because `WebSocket.connect` is a
  /// static that reaches the network, so without this the reconnect, backoff
  /// and heartbeat below can only be exercised against a real server.
  final Future<WebSocket> Function(String url)? connector;

  /// Where the bearer token comes from. Injectable for the same reason: the
  /// default goes through secure storage, which is a platform channel with no
  /// implementation under `flutter test`.
  final Future<String?> Function()? tokenProvider;

  CoupleChatSocket({
    required this.relationshipId,
    required this.onEvent,
    this.onConnectionLost,
    this.connector,
    this.tokenProvider,
  });

  bool get isConnected => _socket != null;

  Future<void> connect() async {
    if (_disposed) return;
    final token = await (tokenProvider ?? StorageService.getToken)();
    if (token == null) return;

    // ws:// against a local http backend, wss:// against production.
    final scheme = CertConfig.scheme == 'https' ? 'wss' : 'ws';
    final url =
        '$scheme://${CertConfig.fastapiHost}/ws/couple/$relationshipId?token=$token';

    try {
      final socket = await (connector ?? WebSocket.connect)(url);
      if (_disposed) {
        await socket.close();
        return;
      }
      _socket = socket;
      _backoff = _initialBackoff; // a good connection resets the backoff
      _startHeartbeat();
      _subscription = socket.listen(
        _handleFrame,
        onDone: _scheduleReconnect,
        onError: (_) => _scheduleReconnect(),
        cancelOnError: true,
      );
    } catch (e) {
      debugPrint('CoupleChatSocket connect failed: $e');
      _scheduleReconnect();
    }
  }

  void _handleFrame(dynamic frame) {
    if (frame is! String) return;
    try {
      final decoded = jsonDecode(frame);
      if (decoded is Map<String, dynamic>) onEvent(decoded);
    } catch (_) {
      // A malformed frame is not worth tearing the connection down for.
    }
  }

  void _startHeartbeat() {
    _heartbeat?.cancel();
    _heartbeat = Timer.periodic(_heartbeatInterval, (_) {
      try {
        _socket?.add('{"t":"ping"}');
      } catch (_) {
        // A write onto a half-open socket throws; the listener's onError will
        // schedule the reconnect. Nothing useful to do here.
      }
    });
  }

  void _scheduleReconnect() {
    if (!_disposed) onConnectionLost?.call();
    _heartbeat?.cancel();
    _heartbeat = null;
    _socket = null;
    _subscription?.cancel();
    _subscription = null;
    if (_disposed) return;

    _reconnect?.cancel();
    _reconnect = Timer(_backoff, connect);
    final next = _backoff * 2;
    _backoff = next > _maxBackoff ? _maxBackoff : next;
  }

  Future<void> dispose() async {
    _disposed = true;
    _heartbeat?.cancel();
    _reconnect?.cancel();
    await _subscription?.cancel();
    await _socket?.close();
    _socket = null;
  }
}
