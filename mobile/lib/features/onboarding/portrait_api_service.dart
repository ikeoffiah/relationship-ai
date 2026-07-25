import '../../core/api_services/base_api_service.dart';
import 'portrait_models.dart';

/// Fetches the relationship portrait (Django host). Extends [BaseApiService] for
/// JWT injection, refresh and pinning.
class PortraitApiService extends BaseApiService {
  PortraitApiService({super.injectedDio});

  Future<RelationshipPortrait> fetch() async {
    try {
      final res = await dio.get('/api/v1/personalization/portrait');
      return RelationshipPortrait.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }
}
