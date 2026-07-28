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

  WebSocket? _socket;
  StreamSubscription<dynamic>? _subscription;
  Timer? _reconnect;
  bool _disposed = false;

  /// Backoff between reconnection attempts, capped so a long outage doesn't
  /// leave the thread silently dead once the network returns.
  static const _initialBackoff = Duration(seconds: 2);
  static const _maxBackoff = Duration(seconds: 30);
  Duration _backoff = _initialBackoff;

  CoupleChatSocket({required this.relationshipId, required this.onEvent});

  bool get isConnected => _socket != null;

  Future<void> connect() async {
    if (_disposed) return;
    final token = await StorageService.getToken();
    if (token == null) return;

    // ws:// against a local http backend, wss:// against production.
    final scheme = CertConfig.scheme == 'https' ? 'wss' : 'ws';
    final url =
        '$scheme://${CertConfig.fastapiHost}/ws/couple/$relationshipId?token=$token';

    try {
      final socket = await WebSocket.connect(url);
      if (_disposed) {
        await socket.close();
        return;
      }
      _socket = socket;
      _backoff = _initialBackoff; // a good connection resets the backoff
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

  void _scheduleReconnect() {
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
    _reconnect?.cancel();
    await _subscription?.cancel();
    await _socket?.close();
    _socket = null;
  }
}
