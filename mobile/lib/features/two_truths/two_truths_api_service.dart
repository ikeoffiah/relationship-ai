import '../../core/api_services/base_api_service.dart';
import 'two_truths_models.dart';

/// API client for Two Truths & a Lie (Django host). Extends [BaseApiService]
/// for JWT injection, refresh and pinning.
class TwoTruthsApiService extends BaseApiService {
  TwoTruthsApiService({super.injectedDio});

  static const _base = '/api/v1/engagement/two-truths';

  Future<TwoTruthsState> fetchState() async {
    try {
      final res = await dio.get(_base);
      return TwoTruthsState.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<TwoTruthsState> author(List<String> statements, int lieIndex) async {
    try {
      final res = await dio.post('$_base/author',
          data: {'statements': statements, 'lie_index': lieIndex});
      return TwoTruthsState.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<TwoTruthsState> guess(int guessIndex) async {
    try {
      final res = await dio.post('$_base/guess', data: {'guess_index': guessIndex});
      return TwoTruthsState.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  Future<void> reset() async {
    try {
      await dio.post('$_base/reset');
    } catch (e) {
      throw handleError(e);
    }
  }
}
