import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/api_services/settings_api_service.dart';
import 'package:mocktail/mocktail.dart';

class MockDio extends Mock implements Dio {}

Response<dynamic> ok([Map<String, dynamic> body = const {}]) => Response(
      data: body,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/'),
    );

void main() {
  late MockDio dio;
  late SettingsApiService service;

  setUp(() {
    dio = MockDio();
    when(() => dio.interceptors).thenReturn(Interceptors());
    service = SettingsApiService(injectedDio: dio);
  });

  test('getProfile hits the user-scoped endpoint (no id in path)', () async {
    when(() => dio.get<dynamic>(any())).thenAnswer(
      (_) async => ok({'full_name': 'Ada', 'email': 'a@e.com'}),
    );

    await service.getProfile('user-123');

    verify(() => dio.get<dynamic>('/api/v1/users/profile/')).called(1);
  });

  test('updateProfile PUTs full_name to the user-scoped endpoint', () async {
    when(() => dio.put<dynamic>(any(), data: any(named: 'data')))
        .thenAnswer((_) async => ok());

    await service.updateProfile('user-123', displayName: 'Grace');

    final captured = verify(
      () => dio.put<dynamic>(captureAny(), data: captureAny(named: 'data')),
    ).captured;
    expect(captured[0], '/api/v1/users/profile/');
    expect(captured[1], {'full_name': 'Grace'});
  });

  test('getNotificationPreferences hits the user-scoped endpoint', () async {
    when(() => dio.get<dynamic>(any())).thenAnswer((_) async => ok());

    await service.getNotificationPreferences('user-123');

    verify(() => dio.get<dynamic>('/api/v1/users/notification-preferences/'))
        .called(1);
  });

  test('deleteAccount targets /account/, not /{id}', () async {
    when(() => dio.delete<dynamic>(any(), data: any(named: 'data')))
        .thenAnswer((_) async => ok());

    await service.deleteAccount('user-123', password: 'pw');

    verify(
      () => dio.delete<dynamic>('/api/v1/users/account/',
          data: any(named: 'data')),
    ).called(1);
  });
}
