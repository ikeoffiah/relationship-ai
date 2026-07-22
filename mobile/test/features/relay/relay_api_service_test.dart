import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/relay/relay_api_service.dart';
import 'package:mobile/features/relay/relay_models.dart';
import 'package:mocktail/mocktail.dart';

class MockDio extends Mock implements Dio {}

Response<dynamic> ok(dynamic body) => Response(
      data: body,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/'),
    );

Map<String, dynamic> relayJson({String status = 'ready', String? translated}) => {
      'relay_id': 'relay-1',
      'from_user_id': 'a',
      'to_user_id': 'b',
      'relationship_id': 'rel-1',
      'original_content': 'the original',
      'translated_content': translated,
      'translation_quality_score': 0.85,
      'status': status,
      'created_at': '2026-01-01T00:00:00Z',
      'delivered_at': null,
      'recipient_chose_version': null,
      'expires_at': '2026-01-08T00:00:00Z',
    };

void main() {
  late MockDio dio;
  late RelayApiService service;

  setUp(() {
    dio = MockDio();
    when(() => dio.interceptors).thenReturn(Interceptors());
    service = RelayApiService(injectedDio: dio);
  });

  test('send posts content + consent and returns status', () async {
    when(() => dio.post<dynamic>(any(), data: any(named: 'data')))
        .thenAnswer((_) async => ok({'relay_id': 'r', 'status': 'ready'}));

    final status = await service.send(content: 'hi', consent: true);

    expect(status, 'ready');
    final captured = verify(
      () => dio.post<dynamic>(captureAny(), data: captureAny(named: 'data')),
    ).captured;
    expect(captured[0], '/api/v1/sessions/async/relay');
    expect(captured[1], {'content': 'hi', 'consent_to_relay': true});
  });

  test('fetchPending parses the pending list', () async {
    when(() => dio.get<dynamic>(any())).thenAnswer(
      (_) async => ok([relayJson(translated: 'kinder version')]),
    );

    final pending = await service.fetchPending('user-b');

    expect(pending, hasLength(1));
    expect(pending.first, isA<RelayDetail>());
    expect(pending.first.translatedContent, 'kinder version');
    verify(() => dio.get<dynamic>('/api/v1/users/user-b/relay/pending'))
        .called(1);
  });

  test('deliver posts the chosen version to the right path', () async {
    when(() => dio.post<dynamic>(any(), data: any(named: 'data')))
        .thenAnswer((_) async => ok(relayJson(status: 'delivered')));

    final result = await service.deliver('relay-1', RelayVersion.original);

    expect(result.status, 'delivered');
    final captured = verify(
      () => dio.post<dynamic>(captureAny(), data: captureAny(named: 'data')),
    ).captured;
    expect(captured[0], '/api/v1/relay/relay-1/deliver');
    expect(captured[1], {'recipient_chose_version': 'original'});
  });

  test('withdraw deletes the relay', () async {
    when(() => dio.delete<dynamic>(any())).thenAnswer((_) async => ok({}));

    await service.withdraw('relay-1');

    verify(() => dio.delete<dynamic>('/api/v1/relay/relay-1')).called(1);
  });
}
