import '../../core/api_services/base_api_service.dart';
import 'bliss_models.dart';

/// API client for the @bliss assistant (Django host). Extends [BaseApiService]
/// for JWT injection, refresh and pinning.
class BlissApiService extends BaseApiService {
  BlissApiService({super.injectedDio});

  static const _base = '/api/v1/engagement/bliss';

  /// Parse a raw "@bliss …" message into a draft. Returns null when the backend
  /// couldn't find something to schedule (recognized: false).
  Future<BlissDraft?> interpret(String text) async {
    try {
      final res = await dio.post('$_base/interpret', data: {'text': text});
      if (res.data['recognized'] != true) return null;
      return BlissDraft.fromJson(res.data['draft'] as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<BlissItem> create(BlissDraft draft) async {
    try {
      final res = await dio.post('$_base/items', data: {
        'kind': draft.kind,
        'title': draft.title,
        'due_at': draft.dueAt?.toUtc().toIso8601String(),
        'source': 'bliss',
      });
      return BlissItem.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<List<BlissItem>> list() async {
    try {
      final res = await dio.get('$_base/items');
      final items = (res.data['items'] as List).cast<Map<String, dynamic>>();
      return items.map(BlissItem.fromJson).toList();
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<BlissItem> setDone(String id) => _setStatus(id, 'done');
  Future<BlissItem> setCancelled(String id) => _setStatus(id, 'cancel');

  Future<BlissItem> _setStatus(String id, String action) async {
    try {
      final res = await dio.post('$_base/items/$id/$action');
      return BlissItem.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }
}
