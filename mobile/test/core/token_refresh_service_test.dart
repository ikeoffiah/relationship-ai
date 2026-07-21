import 'package:dio/dio.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/api_services/token_refresh_service.dart';
import 'package:mobile/core/services/storage_service.dart';
import 'package:mocktail/mocktail.dart';

class MockDio extends Mock implements Dio {}

/// In-memory stand-in for the flutter_secure_storage platform channel.
void useFakeSecureStorage(Map<String, String> store) {
  const channel = MethodChannel('plugins.it_nomads.com/flutter_secure_storage');
  TestWidgetsFlutterBinding.ensureInitialized();
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      .setMockMethodCallHandler(channel, (call) async {
    switch (call.method) {
      case 'read':
        return store[call.arguments['key']];
      case 'write':
        store[call.arguments['key']] = call.arguments['value'] as String;
        return null;
      case 'delete':
        store.remove(call.arguments['key']);
        return null;
      case 'readAll':
        return Map<String, String>.from(store);
      case 'deleteAll':
        store.clear();
        return null;
    }
    return null;
  });
}

Response<dynamic> ok(Map<String, dynamic> body) => Response(
      data: body,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/api/v1/auth/refresh/'),
    );

void main() {
  late MockDio dio;
  late Map<String, String> store;

  setUp(() {
    dio = MockDio();
    store = {};
    useFakeSecureStorage(store);
    TokenRefreshService.debugReset();
  });

  test('persists the rotated access and refresh tokens', () async {
    store['refresh_token'] = 'old-jti:old-secret';
    when(() => dio.post<dynamic>(any(), data: any(named: 'data'))).thenAnswer(
      (_) async => ok({
        'access_token': 'new-access',
        'refresh_token': 'new-jti:new-secret',
      }),
    );

    final result = await TokenRefreshService.refresh(client: dio);

    expect(result, isTrue);
    expect(await StorageService.getToken(), 'new-access');
    // Rotation: the new refresh token must overwrite the old one.
    expect(await StorageService.getRefreshToken(), 'new-jti:new-secret');
  });

  test('sends the stored refresh token in the body', () async {
    store['refresh_token'] = 'the-jti:the-secret';
    when(() => dio.post<dynamic>(any(), data: any(named: 'data'))).thenAnswer(
      (_) async => ok({'access_token': 'a', 'refresh_token': 'b:c'}),
    );

    await TokenRefreshService.refresh(client: dio);

    final captured = verify(
      () => dio.post<dynamic>(captureAny(), data: captureAny(named: 'data')),
    ).captured;
    expect(captured[0], '/api/v1/auth/refresh/');
    expect(captured[1], {'refresh_token': 'the-jti:the-secret'});
  });

  test('returns false when there is no stored refresh token', () async {
    final result = await TokenRefreshService.refresh(client: dio);

    expect(result, isFalse);
    verifyNever(() => dio.post<dynamic>(any(), data: any(named: 'data')));
  });

  test('returns false and does not clobber tokens when refresh is rejected',
      () async {
    store['refresh_token'] = 'reused:token';
    store['auth_token'] = 'still-here';
    when(() => dio.post<dynamic>(any(), data: any(named: 'data'))).thenThrow(
      DioException(
        requestOptions: RequestOptions(path: '/api/v1/auth/refresh/'),
        response: Response(
          statusCode: 401,
          requestOptions: RequestOptions(path: '/api/v1/auth/refresh/'),
        ),
      ),
    );

    final result = await TokenRefreshService.refresh(client: dio);

    expect(result, isFalse);
    // A failed refresh must not wipe or alter the existing access token here;
    // the interceptor decides what to do next.
    expect(await StorageService.getToken(), 'still-here');
  });

  test('coalesces concurrent refreshes into a single network call', () async {
    store['refresh_token'] = 'r:t';
    var calls = 0;
    when(() => dio.post<dynamic>(any(), data: any(named: 'data'))).thenAnswer(
      (_) async {
        calls++;
        await Future<void>.delayed(const Duration(milliseconds: 20));
        return ok({'access_token': 'a', 'refresh_token': 'b:c'});
      },
    );

    final results = await Future.wait([
      TokenRefreshService.refresh(client: dio),
      TokenRefreshService.refresh(client: dio),
      TokenRefreshService.refresh(client: dio),
    ]);

    expect(results, everyElement(isTrue));
    expect(calls, 1, reason: 'three concurrent 401s must share one refresh');
  });

  test('a later refresh runs a fresh call after the first completes', () async {
    store['refresh_token'] = 'r:t';
    when(() => dio.post<dynamic>(any(), data: any(named: 'data'))).thenAnswer(
      (_) async => ok({'access_token': 'a', 'refresh_token': 'b:c'}),
    );

    await TokenRefreshService.refresh(client: dio);
    await TokenRefreshService.refresh(client: dio);

    verify(() => dio.post<dynamic>(any(), data: any(named: 'data'))).called(2);
  });
}
