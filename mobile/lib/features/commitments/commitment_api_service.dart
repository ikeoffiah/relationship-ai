import '../../core/api_services/base_api_service.dart';
import 'commitment_models.dart';

/// API client for partner commitments (Django host). Extends [BaseApiService]
/// for JWT injection, refresh and pinning.
class CommitmentApiService extends BaseApiService {
  CommitmentApiService({super.injectedDio});

  static const _base = '/api/v1/engagement/commitments';

  Future<List<Commitment>> list() async {
    try {
      final res = await dio.get(_base);
      final items = (res.data['commitments'] as List).cast<Map<String, dynamic>>();
      return items.map(Commitment.fromJson).toList();
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<Commitment> create({
    required String kind,
    required String text,
    DateTime? remindAt,
  }) async {
    try {
      final data = <String, dynamic>{'kind': kind, 'text': text};
      if (remindAt != null) data['remind_at'] = remindAt.toUtc().toIso8601String();
      final res = await dio.post(_base, data: data);
      return Commitment.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<Commitment> setDone(String id) => _setStatus(id, 'done');
  Future<Commitment> setCancelled(String id) => _setStatus(id, 'cancel');

  Future<Commitment> _setStatus(String id, String action) async {
    try {
      final res = await dio.post('$_base/$id/$action');
      return Commitment.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }
}
