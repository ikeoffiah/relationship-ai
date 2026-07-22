import 'package:flutter/foundation.dart';

import 'package:mobile/features/relay/relay_api_service.dart';
import 'package:mobile/features/relay/relay_models.dart';

class RelayViewModel extends ChangeNotifier {
  final RelayApiService _api;

  RelayViewModel({RelayApiService? api}) : _api = api ?? RelayApiService();

  List<RelayDetail> _pending = [];
  List<RelayDetail> get pending => _pending;

  bool _isLoading = false;
  bool get isLoading => _isLoading;

  String? _error;
  String? get error => _error;

  /// Load the relays awaiting this user's review.
  Future<void> loadPending(String userId) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      _pending = await _api.fetchPending(userId);
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Send a relay. Returns the resulting status, or null on failure.
  Future<String?> send(String content, {required bool consent}) async {
    _error = null;
    try {
      return await _api.send(content: content, consent: consent);
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      notifyListeners();
      return null;
    }
  }

  /// Take delivery of a relay, then drop it from the pending list.
  Future<bool> deliver(String relayId, String version) async {
    _error = null;
    try {
      await _api.deliver(relayId, version);
      _pending.removeWhere((r) => r.relayId == relayId);
      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      notifyListeners();
      return false;
    }
  }
}
