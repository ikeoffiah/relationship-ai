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

  /// Create the item.
  ///
  /// [source] is load-bearing, not telemetry: only "couple_chat" causes the
  /// server to announce the item in the couple's thread. An item raised in a
  /// private counseling session must stay out of there, because the
  /// announcement would tell the partner the session happened.
  Future<BlissItem> create(
    BlissDraft draft, {
    String source = 'bliss',
    bool invitePartner = false,
  }) async {
    try {
      final res = await dio.post('$_base/items', data: {
        'kind': draft.kind,
        'title': draft.title,
        'due_at': draft.dueAt?.toUtc().toIso8601String(),
        'source': source,
        'invite_partner': invitePartner,
      });
      return BlissItem.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  /// Answer an invitation. Only the partner who was asked may call this; the
  /// server refuses the sender, so this cannot be used to accept on their
  /// behalf.
  Future<BlissItem> respond(String itemId, {required bool accept}) async {
    try {
      final res = await dio.post(
        '$_base/items/$itemId/respond',
        data: {'accept': accept},
      );
      return BlissItem.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  /// Dated items in a window, already grouped by day.
  ///
  /// Range-scoped rather than "everything": a calendar is scrolled by month,
  /// and fetching a year to draw a week is how a calendar screen becomes the
  /// slowest thing in an app.
  Future<Map<DateTime, List<BlissItem>>> calendar({
    required DateTime from,
    required DateTime to,
  }) async {
    try {
      final res = await dio.get(
        '$_base/calendar',
        queryParameters: {
          'from': from.toUtc().toIso8601String(),
          'to': to.toUtc().toIso8601String(),
        },
      );
      final days = (res.data['days'] as Map?) ?? const {};
      return {
        for (final entry in days.entries)
          DateTime.parse(entry.key as String): (entry.value as List)
              .map((j) => BlissItem.fromJson(j as Map<String, dynamic>))
              .toList(),
      };
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
