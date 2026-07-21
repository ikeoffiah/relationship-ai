import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/api_services/base_api_service.dart';
import 'package:mobile/core/api_services/token_refresh_service.dart';
import 'package:mobile/core/services/storage_service.dart';

import 'token_refresh_service_test.dart' show useFakeSecureStorage;

/// A minimal concrete BaseApiService so the shared interceptor is exercised.
class _TestApi extends BaseApiService {
  _TestApi({super.injectedDio});
}

/// Adapter that yields a scripted status per request and echoes the request's
/// Authorization header so a test can prove which token a retry carried.
class ScriptedAdapter implements HttpClientAdapter {
  ScriptedAdapter(this.statuses);
  final List<int> statuses;
  int calls = 0;

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    final status = statuses[calls.clamp(0, statuses.length - 1)];
    calls++;
    return ResponseBody.fromString(
      jsonEncode({'auth': options.headers['Authorization']}),
      status,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }
}

/// Refresh adapter: always returns a fresh rotated token pair with 200.
class RefreshAdapter implements HttpClientAdapter {
  int calls = 0;

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    calls++;
    return ResponseBody.fromString(
      jsonEncode({
        'access_token': 'new-access',
        'refresh_token': 'new-jti:new-secret',
      }),
      200,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }
}

Dio _refreshDio(HttpClientAdapter adapter) => Dio()..httpClientAdapter = adapter;

void main() {
  late Map<String, String> store;
  late RefreshAdapter refreshAdapter;

  setUp(() {
    store = {};
    useFakeSecureStorage(store);
    refreshAdapter = RefreshAdapter();
    TokenRefreshService.debugReset(dio: _refreshDio(refreshAdapter));
  });

  test('refreshes and replays the original request after a 401', () async {
    store['auth_token'] = 'stale';
    store['refresh_token'] = 'r:t';

    final dio = Dio()..httpClientAdapter = ScriptedAdapter([401, 200]);
    final api = _TestApi(injectedDio: dio);

    final res = await api.dio.get<dynamic>('https://example.test/thing');

    expect(res.statusCode, 200);
    // The replay carried the refreshed token, not the stale one.
    expect(res.data['auth'], 'Bearer new-access');
    expect(refreshAdapter.calls, 1);
    expect(await StorageService.getToken(), 'new-access');
    expect(await StorageService.getRefreshToken(), 'new-jti:new-secret');
  });

  test('surfaces the 401 when there is no refresh token to use', () async {
    store['auth_token'] = 'stale';

    final dio = Dio()..httpClientAdapter = ScriptedAdapter([401]);
    final api = _TestApi(injectedDio: dio);

    await expectLater(
      api.dio.get<dynamic>('https://example.test/thing'),
      throwsA(
        isA<DioException>()
            .having((e) => e.response?.statusCode, 'status', 401),
      ),
    );
    expect(refreshAdapter.calls, 0);
  });

  test('does not retry more than once if the replay also 401s', () async {
    store['auth_token'] = 'stale';
    store['refresh_token'] = 'r:t';

    final adapter = ScriptedAdapter([401, 401]);
    final api = _TestApi(injectedDio: Dio()..httpClientAdapter = adapter);

    await expectLater(
      api.dio.get<dynamic>('https://example.test/thing'),
      throwsA(isA<DioException>()),
    );
    // original + one replay only; the retried request is not refreshed again.
    expect(adapter.calls, 2);
    expect(refreshAdapter.calls, 1);
  });

  test('a successful request is untouched', () async {
    store['auth_token'] = 'good';

    final adapter = ScriptedAdapter([200]);
    final api = _TestApi(injectedDio: Dio()..httpClientAdapter = adapter);

    final res = await api.dio.get<dynamic>('https://example.test/thing');

    expect(res.statusCode, 200);
    expect(res.data['auth'], 'Bearer good');
    expect(refreshAdapter.calls, 0);
  });
}
