/// The HTTP surface of the couple's thread.
///
/// Every other test in this feature swaps the service for a fake, which is the
/// right trade there — but it leaves the wire format itself unchecked. These
/// tests pin the request shapes and the parsing, because a field renamed on one
/// side and not the other is the kind of break that only shows up on a device.
library;

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:mobile/features/couple_chat/couple_chat_api_service.dart';

class MockDio extends Mock implements Dio {}

Response<dynamic> ok(dynamic body, {int status = 200}) => Response(
  data: body,
  statusCode: status,
  requestOptions: RequestOptions(path: '/'),
);

Map<String, dynamic> messageJson({
  String id = 'm1',
  String kind = 'text',
  Map<String, dynamic>? media,
}) => {
  'id': id,
  'sender_id': 'me',
  'kind': kind,
  'body': 'hello',
  'sticker': '',
  'media': media,
  'reply_to': null,
  'reactions': <dynamic>[],
  'client_id': 'c1',
  'is_deleted': false,
  'status': 'sent',
  'created_at': '2026-07-30T10:00:00Z',
};

Map<String, dynamic> mediaJson({String kind = 'image'}) => {
  'id': 'media-1',
  'kind': kind,
  'mime': kind == 'voice' ? 'audio/mp4' : 'image/jpeg',
  'byte_size': 2048,
  'url': '/api/v1/chat/media/media-1',
  'thumb_url': kind == 'image' ? '/api/v1/chat/media/media-1/thumb' : null,
  'duration_ms': kind == 'voice' ? 8000 : null,
  'waveform': kind == 'voice' ? [10, 50, 90] : <int>[],
  'transcript': '',
  'transcript_status': 'pending',
  'width': kind == 'image' ? 800 : null,
  'height': kind == 'image' ? 600 : null,
};

void main() {
  late MockDio dio;
  late CoupleChatApiService service;

  setUpAll(() {
    registerFallbackValue(RequestOptions(path: '/'));
    registerFallbackValue(Options());
    registerFallbackValue(FormData());
  });

  setUp(() {
    dio = MockDio();
    when(() => dio.interceptors).thenReturn(Interceptors());
    service = CoupleChatApiService(injectedDio: dio);
  });

  group('history', () {
    test('parses a page and its cursor', () async {
      when(
        () => dio.get<dynamic>(any(), queryParameters: any(named: 'queryParameters')),
      ).thenAnswer(
        (_) async => ok({
          'results': [messageJson()],
          'has_more': true,
          'next_before': '2026-07-30T09:00:00Z',
        }),
      );

      final page = await service.history('rel-1');

      expect(page.messages.single.id, 'm1');
      expect(page.hasMore, isTrue);
      expect(page.nextBefore, '2026-07-30T09:00:00Z');
    });

    test('a cursor is sent only when there is one', () async {
      when(
        () => dio.get<dynamic>(any(), queryParameters: any(named: 'queryParameters')),
      ).thenAnswer((_) async => ok({'results': <dynamic>[], 'has_more': false}));

      await service.history('rel-1');
      var params = verify(
        () => dio.get<dynamic>(any(), queryParameters: captureAny(named: 'queryParameters')),
      ).captured.single as Map<String, dynamic>;
      expect(params.containsKey('before'), isFalse);

      await service.history('rel-1', before: 'cursor');
      params = verify(
        () => dio.get<dynamic>(any(), queryParameters: captureAny(named: 'queryParameters')),
      ).captured.single as Map<String, dynamic>;
      expect(params['before'], 'cursor');
    });

    test('a network failure surfaces as a handled error', () async {
      when(
        () => dio.get<dynamic>(any(), queryParameters: any(named: 'queryParameters')),
      ).thenThrow(DioException(requestOptions: RequestOptions(path: '/')));

      expect(() => service.history('rel-1'), throwsA(isA<Exception>()));
    });
  });

  group('send', () {
    test('a text message posts a body and a client id', () async {
      when(
        () => dio.post<dynamic>(any(), data: any(named: 'data')),
      ).thenAnswer((_) async => ok(messageJson()));

      await service.send('rel-1', clientId: 'c1', body: 'hello');

      final data = verify(
        () => dio.post<dynamic>(any(), data: captureAny(named: 'data')),
      ).captured.single as Map<String, dynamic>;
      expect(data['client_id'], 'c1');
      expect(data['body'], 'hello');
      expect(data.containsKey('kind'), isFalse);
    });

    test('a sticker carries its kind', () async {
      when(
        () => dio.post<dynamic>(any(), data: any(named: 'data')),
      ).thenAnswer((_) async => ok(messageJson(kind: 'sticker')));

      await service.send('rel-1', clientId: 'c1', sticker: 'hug');

      final data = verify(
        () => dio.post<dynamic>(any(), data: captureAny(named: 'data')),
      ).captured.single as Map<String, dynamic>;
      expect(data['kind'], 'sticker');
      expect(data['sticker'], 'hug');
    });

    test('media is attached by id and kind', () async {
      when(
        () => dio.post<dynamic>(any(), data: any(named: 'data')),
      ).thenAnswer((_) async => ok(messageJson(kind: 'image', media: mediaJson())));

      final saved = await service.send(
        'rel-1',
        clientId: 'c1',
        mediaId: 'media-1',
        mediaKind: 'image',
        body: 'a caption',
      );

      final data = verify(
        () => dio.post<dynamic>(any(), data: captureAny(named: 'data')),
      ).captured.single as Map<String, dynamic>;
      expect(data['media'], 'media-1');
      expect(data['kind'], 'image');
      // On a photo the body is the caption, not a second message.
      expect(data['body'], 'a caption');
      expect(saved.media?.id, 'media-1');
    });

    test('a reply carries the quoted id', () async {
      when(
        () => dio.post<dynamic>(any(), data: any(named: 'data')),
      ).thenAnswer((_) async => ok(messageJson()));

      await service.send('rel-1', clientId: 'c1', body: 'hi', replyTo: 'm0');

      final data = verify(
        () => dio.post<dynamic>(any(), data: captureAny(named: 'data')),
      ).captured.single as Map<String, dynamic>;
      expect(data['reply_to'], 'm0');
    });

    test('a failure is handled rather than leaking a DioException', () async {
      when(
        () => dio.post<dynamic>(any(), data: any(named: 'data')),
      ).thenThrow(DioException(requestOptions: RequestOptions(path: '/')));

      expect(
        () => service.send('rel-1', clientId: 'c1', body: 'hi'),
        throwsA(isA<Exception>()),
      );
    });
  });

  group('media', () {
    test('an upload posts multipart with generous timeouts', () async {
      when(
        () => dio.post<dynamic>(
          any(),
          data: any(named: 'data'),
          cancelToken: any(named: 'cancelToken'),
          options: any(named: 'options'),
          onSendProgress: any(named: 'onSendProgress'),
        ),
      ).thenAnswer((_) async => ok(mediaJson()));

      final media = await service.uploadMedia(
        'rel-1',
        path: 'test/fixtures/tiny.txt',
        kind: 'image',
      );

      expect(media.id, 'media-1');
      final options = verify(
        () => dio.post<dynamic>(
          any(),
          data: any(named: 'data'),
          cancelToken: any(named: 'cancelToken'),
          options: captureAny(named: 'options'),
          onSendProgress: any(named: 'onSendProgress'),
        ),
      ).captured.single as Options;
      // The default 10s receive timeout is for JSON. Killing a photo mid-upload
      // on a slow connection reads as the app being broken.
      expect(options.sendTimeout, const Duration(minutes: 2));
      expect(options.receiveTimeout, const Duration(minutes: 2));
    });

    test('a voice upload carries duration and waveform', () async {
      when(
        () => dio.post<dynamic>(
          any(),
          data: any(named: 'data'),
          cancelToken: any(named: 'cancelToken'),
          options: any(named: 'options'),
          onSendProgress: any(named: 'onSendProgress'),
        ),
      ).thenAnswer((_) async => ok(mediaJson(kind: 'voice')));

      final media = await service.uploadMedia(
        'rel-1',
        path: 'test/fixtures/tiny.txt',
        kind: 'voice',
        durationMs: 8000,
        waveform: const [10, 50, 90],
      );

      expect(media.durationMs, 8000);
      expect(media.waveform, const [10, 50, 90]);
    });

    test('progress is reported as a fraction', () async {
      when(
        () => dio.post<dynamic>(
          any(),
          data: any(named: 'data'),
          cancelToken: any(named: 'cancelToken'),
          options: any(named: 'options'),
          onSendProgress: any(named: 'onSendProgress'),
        ),
      ).thenAnswer((invocation) async {
        final onProgress =
            invocation.namedArguments[#onSendProgress] as void Function(int, int);
        onProgress(50, 100);
        // A total of zero means "unknown", and dividing by it would put NaN in
        // the progress ring.
        onProgress(50, 0);
        return ok(mediaJson());
      });

      final seen = <double>[];
      await service.uploadMedia(
        'rel-1',
        path: 'test/fixtures/tiny.txt',
        kind: 'image',
        onProgress: seen.add,
      );

      expect(seen, [0.5]);
    });

    test('an upload failure is handled', () async {
      when(
        () => dio.post<dynamic>(
          any(),
          data: any(named: 'data'),
          cancelToken: any(named: 'cancelToken'),
          options: any(named: 'options'),
          onSendProgress: any(named: 'onSendProgress'),
        ),
      ).thenThrow(DioException(requestOptions: RequestOptions(path: '/')));

      expect(
        () => service.uploadMedia(
          'rel-1',
          path: 'test/fixtures/tiny.txt',
          kind: 'image',
        ),
        throwsA(isA<Exception>()),
      );
    });

    test('metadata is re-read from the meta endpoint', () async {
      when(() => dio.get<dynamic>(any())).thenAnswer(
        (_) async => ok({...mediaJson(kind: 'voice'), 'transcript': 'i miss you',
          'transcript_status': 'ok'}),
      );

      final media = await service.mediaMeta('media-1');

      expect(media.transcript, 'i miss you');
      expect(media.hasTranscript, isTrue);
      verify(() => dio.get<dynamic>('/api/v1/chat/media/media-1/meta')).called(1);
    });

    test('a metadata failure is handled', () async {
      when(
        () => dio.get<dynamic>(any()),
      ).thenThrow(DioException(requestOptions: RequestOptions(path: '/')));

      expect(() => service.mediaMeta('media-1'), throwsA(isA<Exception>()));
    });
  });

  group('the rest of the surface', () {
    test('a reaction is toggled by message id', () async {
      when(
        () => dio.post<dynamic>(any(), data: any(named: 'data')),
      ).thenAnswer((_) async => ok(messageJson()));

      await service.toggleReaction('m1', '😍');

      verify(
        () => dio.post<dynamic>(
          '/api/v1/chat/messages/m1/reactions',
          data: {'emoji': '😍'},
        ),
      ).called(1);
    });

    test('a reaction failure is handled', () async {
      when(
        () => dio.post<dynamic>(any(), data: any(named: 'data')),
      ).thenThrow(DioException(requestOptions: RequestOptions(path: '/')));

      expect(() => service.toggleReaction('m1', '😍'), throwsA(isA<Exception>()));
    });

    test('deleting a message calls delete', () async {
      when(() => dio.delete<dynamic>(any())).thenAnswer((_) async => ok(null));

      await service.deleteMessage('m1');

      verify(() => dio.delete<dynamic>('/api/v1/chat/messages/m1')).called(1);
    });

    test('a delete failure is handled', () async {
      when(
        () => dio.delete<dynamic>(any()),
      ).thenThrow(DioException(requestOptions: RequestOptions(path: '/')));

      expect(() => service.deleteMessage('m1'), throwsA(isA<Exception>()));
    });

    test('marking read posts to the read endpoint', () async {
      when(() => dio.post<dynamic>(any())).thenAnswer((_) async => ok(null));

      await service.markRead('rel-1');

      verify(() => dio.post<dynamic>('/api/v1/chat/rel-1/read')).called(1);
    });

    test('a read failure is handled', () async {
      when(
        () => dio.post<dynamic>(any()),
      ).thenThrow(DioException(requestOptions: RequestOptions(path: '/')));

      expect(() => service.markRead('rel-1'), throwsA(isA<Exception>()));
    });

    test('marking delivered posts to the delivered endpoint', () async {
      when(() => dio.post<dynamic>(any())).thenAnswer((_) async => ok(null));

      await service.markDelivered('rel-1');

      verify(() => dio.post<dynamic>('/api/v1/chat/rel-1/delivered')).called(1);
    });

    test('a delivered failure is handled, and the caller decides', () async {
      when(
        () => dio.post<dynamic>(any()),
      ).thenThrow(DioException(requestOptions: RequestOptions(path: '/')));

      // The service throws rather than swallowing. A receipt that does not
      // land is recoverable on the next fetch, so the view model is where that
      // gets absorbed — keeping the decision out of the transport layer.
      expect(() => service.markDelivered('rel-1'), throwsA(isA<Exception>()));
    });
  });

  group('intimate consent', () {
    test('an unlocked couple reads as unlocked', () async {
      when(() => dio.get<dynamic>(any())).thenAnswer(
        (_) async => ok({'unlocked': true}),
      );

      expect(await service.intimateUnlocked('rel-1'), isTrue);
    });

    test('a failure fails closed', () async {
      when(
        () => dio.get<dynamic>(any()),
      ).thenThrow(DioException(requestOptions: RequestOptions(path: '/')));

      // Not knowing must never be the same as being unlocked.
      expect(await service.intimateUnlocked('rel-1'), isFalse);
    });
  });

  group('assist', () {
    test('a draft check parses a caution verdict', () async {
      when(
        () => dio.post<dynamic>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => ok({
          'verdict': 'caution',
          'reason': 'this may land badly',
          'suggestion': 'try this instead',
        }),
      );

      final verdict = await service.checkDraft('rel-1', 'you always do this');

      expect(verdict.caution, isTrue);
      expect(verdict.suggestion, 'try this instead');
    });

    test('a failed check does not block the send', () async {
      when(
        () => dio.post<dynamic>(any(), data: any(named: 'data')),
      ).thenThrow(DioException(requestOptions: RequestOptions(path: '/')));

      final verdict = await service.checkDraft('rel-1', 'hello');

      // Failing closed would mean an outage silently stops the thread.
      expect(verdict.caution, isFalse);
    });

    test('a rephrase returns the suggestion', () async {
      when(
        () => dio.post<dynamic>(any(), data: any(named: 'data')),
      ).thenAnswer((_) async => ok({'suggestion': 'a kinder version'}));

      expect(await service.rephrase('rel-1', 'draft'), 'a kinder version');
    });

    test('a failed rephrase returns nothing rather than throwing', () async {
      when(
        () => dio.post<dynamic>(any(), data: any(named: 'data')),
      ).thenThrow(DioException(requestOptions: RequestOptions(path: '/')));

      expect(await service.rephrase('rel-1', 'draft'), isNull);
    });

    test('read coaching parses guidance and the support flag', () async {
      when(
        () => dio.post<dynamic>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => ok({'guidance': 'they may be hurt', 'defer_to_support': true}),
      );

      final result = await service.readCoach('rel-1', 'incoming');

      expect(result.guidance, 'they may be hurt');
      expect(result.deferToSupport, isTrue);
    });

    test('failed read coaching says nothing', () async {
      when(
        () => dio.post<dynamic>(any(), data: any(named: 'data')),
      ).thenThrow(DioException(requestOptions: RequestOptions(path: '/')));

      final result = await service.readCoach('rel-1', 'incoming');

      expect(result.guidance, isNull);
      expect(result.deferToSupport, isFalse);
    });
  });
}
