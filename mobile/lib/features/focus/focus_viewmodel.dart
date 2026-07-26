import 'dart:async';

import 'package:flutter/foundation.dart';

import 'focus_api_service.dart';
import 'focus_models.dart';

/// Drives consensual Focus Mode. Polls the backend every few seconds while a
/// session is live so both partners see accepts/ends promptly; the countdown
/// itself ticks locally from `ends_at`.
class FocusViewModel extends ChangeNotifier {
  final FocusApiService _api;
  final Duration pollInterval;
  FocusViewModel({FocusApiService? api, this.pollInterval = const Duration(seconds: 5)})
      : _api = api ?? FocusApiService();

  FocusSession? _session;
  FocusSession? get session => _session;

  bool _isLoading = false;
  bool get isLoading => _isLoading;

  bool _busy = false;
  bool get busy => _busy;

  String? _error;
  String? get error => _error;

  Timer? _poll;

  Future<void> load() async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      _session = await _api.current();
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
    } finally {
      _isLoading = false;
      _syncPolling();
      notifyListeners();
    }
  }

  Future<bool> propose(int minutes) => _act(() => _api.propose(minutes));
  Future<bool> accept() => _act(() => _api.accept());
  Future<bool> decline() => _act(() => _api.decline());
  Future<bool> end() => _act(() => _api.end());

  Future<bool> _act(Future<FocusSession?> Function() call) async {
    _busy = true;
    _error = null;
    notifyListeners();
    try {
      _session = await call();
      return true;
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      return false;
    } finally {
      _busy = false;
      _syncPolling();
      notifyListeners();
    }
  }

  /// Poll only while there's a live (proposed/active) session.
  void _syncPolling() {
    final live = _session != null && (_session!.isProposed || _session!.isActive);
    if (live && _poll == null) {
      _poll = Timer.periodic(pollInterval, (_) => _refresh());
    } else if (!live) {
      _poll?.cancel();
      _poll = null;
    }
  }

  Future<void> _refresh() async {
    try {
      _session = await _api.current();
      _syncPolling();
      notifyListeners();
    } catch (_) {
      // Transient poll failure is non-fatal; keep the last known state.
    }
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }
}
