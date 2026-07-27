import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:dio/dio.dart';
import 'package:mobile/core/api_services/push_api_service.dart';

class MockDio extends Mock implements Dio {}

void main() {
  late MockDio mockDio;
  late PushApiService service;

  setUp(() {
    mockDio = MockDio();
    when(() => mockDio.interceptors).thenReturn(Interceptors());
    service = PushApiService(injectedDio: mockDio);
  });

  test('registerToken posts the token to the fcm-token endpoint', () async {
    when(() => mockDio.post('/api/v1/users/fcm-token/', data: any(named: 'data')))
        .thenAnswer((_) async => Response(
              statusCode: 200,
              requestOptions: RequestOptions(path: '/api/v1/users/fcm-token/'),
            ));

    await service.registerToken('device-token-abc');

    verify(() => mockDio.post('/api/v1/users/fcm-token/',
        data: {'token': 'device-token-abc'})).called(1);
  });

  test('registerToken surfaces an error on failure', () async {
    when(() => mockDio.post(any(), data: any(named: 'data'))).thenThrow(
      DioException(
        requestOptions: RequestOptions(path: '/api/v1/users/fcm-token/'),
        response: Response(
          data: {'detail': 'Token is required.'},
          statusCode: 400,
          requestOptions: RequestOptions(path: '/api/v1/users/fcm-token/'),
        ),
      ),
    );

    expect(() => service.registerToken(''), throwsA(isA<Exception>()));
  });
}
