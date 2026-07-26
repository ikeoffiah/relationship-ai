import 'package:flutter/foundation.dart';

import 'bliss_api_service.dart';
import 'bliss_models.dart';

/// Client-side detection of a "@bliss …" command (case-insensitive), so the chat
/// can intercept it before sending to counseling. Mirrors the backend's tag.
final RegExp blissTag = RegExp(r'@bliss\b', caseSensitive: false);
bool isBlissCommand(String text) => blissTag.hasMatch(text);

/// Drives the @bliss flow: interpret a tagged message, create the confirmed
/// item, and manage the couple's shared plan list.
class BlissViewModel extends ChangeNotifier {
  final BlissApiService _api;
  BlissViewModel({BlissApiService? api}) : _api = api ?? BlissApiService();

  List<BlissItem> _items = const [];
  List<BlissItem> get items => List.unmodifiable(_items);

  bool _isLoading = false;
  bool get isLoading => _isLoading;

  String? _error;
  String? get error => _error;

  /// Parse a tagged message. Returns the draft, or null if unrecognized/failed.
  Future<BlissDraft?> interpret(String text) async {
    try {
      return await _api.interpret(text);
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      notifyListeners();
      return null;
    }
  }

  /// Create a confirmed item and prepend it to the local list. Returns it, or
  /// null on failure.
  Future<BlissItem?> create(BlissDraft draft) async {
    try {
      final item = await _api.create(draft);
      _items = [item, ..._items];
      notifyListeners();
      return item;
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      notifyListeners();
      return null;
    }
  }

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

  Future<void> markDone(String id) => _update(id, _api.setDone);
  Future<void> cancel(String id) => _update(id, _api.setCancelled);

  Future<void> _update(String id, Future<BlissItem> Function(String) call) async {
    try {
      await call(id);
      // Both done and cancel remove the item from the pending plan list.
      _items = _items.where((i) => i.id != id).toList();
      notifyListeners();
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      notifyListeners();
    }
  }
}
