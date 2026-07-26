import '../../../core/api_services/base_api_service.dart';
import '../../../core/security/certificate_config.dart';
import 'tone_models.dart';

/// API client for the in-chat tone coach. Targets the FastAPI host (like
/// [SessionService]) and inherits JWT injection + pinning from [BaseApiService].
class ToneApiService extends BaseApiService {
  ToneApiService({super.injectedDio})
      : super(baseUrl: 'https://${CertConfig.fastapiHost}');

  static const _base = '/api/v1/tone';

  /// Read the emotional tone of a message (e.g. the partner's last one).
  Future<MoodRead> analyze(String text) async {
    try {
      final res = await dio.post('$_base/analyze', data: {'text': text});
      return MoodRead.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  /// Judge the caller's own draft and get kinder rewrites.
  Future<CoachResult> coach(String draft, {String? partnerMood}) async {
    try {
      final data = <String, dynamic>{'draft': draft};
      if (partnerMood != null) data['partner_mood'] = partnerMood;
      final res = await dio.post('$_base/coach', data: data);
      return CoachResult.fromJson(res.data as Map<String, dynamic>);
    } catch (e) {
      throw handleError(e);
    }
  }

  /// Auto-suggest up to 3 attuned things to say next.
  /// [messages] is ordered oldest→newest, each {'role': 'me'|'partner', 'content': ...}.
  Future<List<String>> suggest(List<Map<String, String>> messages) async {
    try {
      final res = await dio.post('$_base/suggest', data: {'messages': messages});
      final list = (res.data['suggestions'] as List?) ?? const [];
      return list.map((e) => e.toString()).toList();
    } catch (e) {
      throw handleError(e);
    }
  }
}
