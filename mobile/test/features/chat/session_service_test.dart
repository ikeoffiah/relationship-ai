import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/chat/models/chat_models.dart';
import 'package:mobile/features/chat/services/session_service.dart';
import 'package:mocktail/mocktail.dart';

class MockDio extends Mock implements Dio {}

/// Serves a scripted SSE byte stream, split into caller-chosen chunks so the
/// tests can put a chunk boundary anywhere — including mid-line.
void stubStream(MockDio dio, List<String> chunks) {
  final body = ResponseBody(
    Stream.fromIterable(
      chunks.map((c) => Uint8List.fromList(utf8.encode(c))),
    ),
    200,
  );
  when(
    () => dio.post<dynamic>(
      any(),
      data: any(named: 'data'),
      options: any(named: 'options'),
    ),
  ).thenAnswer(
    (_) async => Response(
      data: body,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/'),
    ),
  );
}

String frame(Map<String, dynamic> payload) => 'data: ${jsonEncode(payload)}\n\n';

void main() {
  late MockDio dio;
  late SessionService service;

  setUp(() {
    dio = MockDio();
    when(() => dio.interceptors).thenReturn(Interceptors());
    service = SessionService(injectedDio: dio);
  });

  test('parses a full turn into typed events', () async {
    stubStream(dio, [
      frame({'type': 'strategy_change', 'strategy': 'Validation'}),
      frame({'type': 'token', 'content': 'Hello '}),
      frame({'type': 'token', 'content': 'there'}),
      frame({'type': 'done'}),
    ]);

    final events = await service.sendMessage('s1', 'hi').toList();

    expect(events, hasLength(4));
    expect(events[0], isA<StrategyChangeEvent>());
    expect((events[1] as ChatTokenEvent).content, 'Hello ');
    expect((events[2] as ChatTokenEvent).content, 'there');
    expect(events.last, isA<MessageCompleteEvent>());
  });

  test('reassembles a frame split across chunk boundaries', () async {
    // The realistic failure mode: TCP does not respect line boundaries.
    final full = frame({'type': 'token', 'content': 'split across chunks'});
    final cut = full.length ~/ 2;

    stubStream(dio, [
      full.substring(0, cut),
      full.substring(cut),
      frame({'type': 'done'}),
    ]);

    final events = await service.sendMessage('s1', 'hi').toList();

    final tokens = events.whereType<ChatTokenEvent>().toList();
    expect(tokens, hasLength(1));
    expect(tokens.single.content, 'split across chunks');
  });

  test('handles several frames arriving in one chunk', () async {
    stubStream(dio, [
      frame({'type': 'token', 'content': 'a'}) +
          frame({'type': 'token', 'content': 'b'}) +
          frame({'type': 'done'}),
    ]);

    final events = await service.sendMessage('s1', 'hi').toList();

    expect(events.whereType<ChatTokenEvent>().map((e) => e.content), ['a', 'b']);
    expect(events.last, isA<MessageCompleteEvent>());
  });

  test('parses a safety event with its resources', () async {
    stubStream(dio, [
      frame({
        'type': 'safety_triggered',
        'level': 'critical',
        'resources': [
          {'name': 'Example Line', 'phone': '000'},
        ],
      }),
      frame({'type': 'done'}),
    ]);

    final events = await service.sendMessage('s1', 'hi').toList();

    final safety = events.whereType<SafetyTriggeredEvent>().single;
    expect(safety.level, 'critical');
    expect(safety.resources, hasLength(1));
  });

  test('tolerates an empty resources list', () async {
    // The backend ships no crisis resources until they are configured.
    stubStream(dio, [
      frame({'type': 'safety_triggered', 'level': 'elevated', 'resources': []}),
      frame({'type': 'done'}),
    ]);

    final events = await service.sendMessage('s1', 'hi').toList();

    expect(events.whereType<SafetyTriggeredEvent>().single.resources, isEmpty);
  });

  test('ignores unknown event types rather than throwing', () async {
    stubStream(dio, [
      frame({'type': 'something_new', 'payload': 1}),
      frame({'type': 'token', 'content': 'ok'}),
      frame({'type': 'done'}),
    ]);

    final events = await service.sendMessage('s1', 'hi').toList();

    expect(events.whereType<ChatTokenEvent>().single.content, 'ok');
    expect(events.last, isA<MessageCompleteEvent>());
  });

  test('ignores malformed JSON without aborting the stream', () async {
    stubStream(dio, [
      'data: {not json\n\n',
      frame({'type': 'token', 'content': 'survived'}),
      frame({'type': 'done'}),
    ]);

    final events = await service.sendMessage('s1', 'hi').toList();

    expect(events.whereType<ChatTokenEvent>().single.content, 'survived');
  });

  test('completes when the request fails so the UI does not hang', () async {
    when(
      () => dio.post<dynamic>(
        any(),
        data: any(named: 'data'),
        options: any(named: 'options'),
      ),
    ).thenThrow(DioException(requestOptions: RequestOptions(path: '/')));

    final events = await service.sendMessage('s1', 'hi').toList();

    expect(events, hasLength(1));
    expect(events.single, isA<MessageCompleteEvent>());
  });

  test('posts to the message endpoint with the content body', () async {
    stubStream(dio, [frame({'type': 'done'})]);

    await service.sendMessage('session-42', 'I feel unheard').toList();

    final captured = verify(
      () => dio.post<dynamic>(
        captureAny(),
        data: captureAny(named: 'data'),
        options: any(named: 'options'),
      ),
    ).captured;

    expect(captured[0], '/api/v1/sessions/session-42/messages');
    expect(captured[1], {'content': 'I feel unheard'});
  });
}
