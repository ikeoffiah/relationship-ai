import 'package:flutter/foundation.dart';

import 'commitment_api_service.dart';
import 'commitment_models.dart';

/// Drives the commitments list and the add flow.
class CommitmentViewModel extends ChangeNotifier {
  final CommitmentApiService _api;
  CommitmentViewModel({CommitmentApiService? api}) : _api = api ?? CommitmentApiService();

  List<Commitment> _items = const [];
  List<Commitment> get items => List.unmodifiable(_items);

  List<Commitment> get forPartner =>
      _items.where((c) => c.kind == 'for_partner').toList();
  List<Commitment> get withPartner =>
      _items.where((c) => c.kind == 'with_partner').toList();

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
      _items = await _api.list();
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> add({required String kind, required String text, DateTime? remindAt}) async {
    _submitting = true;
    _error = null;
    notifyListeners();
    try {
      final item = await _api.create(kind: kind, text: text, remindAt: remindAt);
      _items = [item, ..._items];
      return true;
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      return false;
    } finally {
      _submitting = false;
      notifyListeners();
    }
  }

  Future<void> markDone(String id) => _update(id, _api.setDone);
  Future<void> cancel(String id) => _update(id, _api.setCancelled);

  Future<void> _update(String id, Future<Commitment> Function(String) call) async {
    try {
      await call(id);
      _items = _items.where((c) => c.id != id).toList();
      notifyListeners();
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      notifyListeners();
    }
  }
}
