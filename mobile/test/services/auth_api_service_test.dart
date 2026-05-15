import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:dio/dio.dart';
import 'package:mobile/core/api_services/auth_api_service.dart';

class MockDio extends Mock implements Dio {}

void main() {
  late MockDio mockDio;
  late AuthApiService authApiService;

  setUp(() {
    mockDio = MockDio();
    // BaseApiService tries to add interceptors on constructor, so we need to mock interceptors
    when(() => mockDio.interceptors).thenReturn(Interceptors());
    
    authApiService = AuthApiService(injectedDio: mockDio);
  });

  group('AuthApiService Tests', () {
    test('login returns AuthResponse on success', () async {
      when(() => mockDio.post('/auth/login', data: any(named: 'data')))
          .thenAnswer((_) async => Response(
                data: {'token': 'secret123', 'user': {'id': '1', 'name': 'Pius', 'email': 'test@example.com'}},
                statusCode: 200,
                requestOptions: RequestOptions(path: '/auth/login'),
              ));

      final response = await authApiService.login('test@example.com', 'password');
      expect(response.token, 'secret123');
      expect(response.user?.name, 'Pius');
    });

    test('login throws Exception on DioError', () async {
      when(() => mockDio.post('/auth/login', data: any(named: 'data')))
          .thenThrow(DioException(
            requestOptions: RequestOptions(path: '/auth/login'),
            response: Response(
              data: {'message': 'Invalid credentials'},
              statusCode: 401,
              requestOptions: RequestOptions(path: '/'),
            ),
          ));

      expect(() => authApiService.login('test', '123'), throwsA(isA<Exception>()));
    });

    test('signup returns AuthResponse on success', () async {
      when(() => mockDio.post('/auth/signup', data: any(named: 'data')))
          .thenAnswer((_) async => Response(
                data: {'token': 'signed_up_token', 'user': null},
                statusCode: 201,
                requestOptions: RequestOptions(path: '/auth/signup'),
              ));

      final response = await authApiService.signup('Pius', 'test@test.com', '123');
      expect(response.token, 'signed_up_token');
    });

    test('googleSignIn works', () async {
      when(() => mockDio.post('/auth/google', data: any(named: 'data')))
          .thenAnswer((_) async => Response(
                data: {'token': 'google_jwt', 'user': null},
                statusCode: 200,
                requestOptions: RequestOptions(path: '/auth/google'),
              ));

      final response = await authApiService.googleSignIn('id_token_123');
      expect(response.token, 'google_jwt');
    });

    test('logout resolves', () async {
      when(() => mockDio.post('/auth/logout')).thenAnswer((_) async => Response(
          requestOptions: RequestOptions(path: '/auth/logout'),
      ));
      
      await authApiService.logout();
      verify(() => mockDio.post('/auth/logout')).called(1);
    });

    test('forgotPassword resolves', () async {
      when(() => mockDio.post('/auth/forgot-password', data: any(named: 'data'))).thenAnswer((_) async => Response(
          requestOptions: RequestOptions(path: '/auth/forgot-password'),
      ));
      
      await authApiService.forgotPassword('test@test.com');
      verify(() => mockDio.post('/auth/forgot-password', data: {'email': 'test@test.com'})).called(1);
    });

    test('resetPassword resolves', () async {
      when(() => mockDio.post('/auth/reset-password', data: any(named: 'data'))).thenAnswer((_) async => Response(
          requestOptions: RequestOptions(path: '/auth/reset-password'),
      ));
      
      await authApiService.resetPassword('new_pass', 'token123');
      verify(() => mockDio.post('/auth/reset-password', data: {'new_password': 'new_pass', 'token': 'token123'})).called(1);
    });
  });
}
