import 'package:flutter/foundation.dart';

import 'two_truths_api_service.dart';
import 'two_truths_models.dart';

/// Drives Two Truths & a Lie: load state, author statements, guess the
/// partner's lie, and reset for a new round.
class TwoTruthsViewModel extends ChangeNotifier {
  final TwoTruthsApiService _api;
  TwoTruthsViewModel({TwoTruthsApiService? api}) : _api = api ?? TwoTruthsApiService();

  TwoTruthsState? _state;
  TwoTruthsState? get state => _state;

  bool _isLoading = false;
  bool get isLoading => _isLoading;

  bool _submitting = false;
  bool get submitting => _submitting;

  String? _error;
  String? get error => _error;

  Future<void> load() async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      _state = await _api.fetchState();
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> author(List<String> statements, int lieIndex) =>
      _run(() => _api.author(statements, lieIndex));

  Future<bool> guess(int guessIndex) => _run(() => _api.guess(guessIndex));

  Future<bool> reset() async {
    final ok = await _run(() async {
      await _api.reset();
      return _api.fetchState();
    });
    return ok;
  }

  Future<bool> _run(Future<TwoTruthsState> Function() call) async {
    _submitting = true;
    _error = null;
    notifyListeners();
    try {
      _state = await call();
      return true;
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      return false;
    } finally {
      _submitting = false;
      notifyListeners();
    }
  }
}
