/// The on-device cache for decrypted media.
///
/// What lands here is plaintext — the photo, in the clear, on the phone. The
/// properties that matter are therefore about lifetime rather than speed: a
/// partial download must never be mistaken for a cache hit, and everything has
/// to be removable in one call when the app leaves the foreground.
///
/// This file exists because the first version of `file()` deadlocked on itself
/// and nothing caught it: every widget test renders from a local path, and the
/// e2e script exercises the server rather than the client. No photo would have
/// loaded in the app, with no error to show for it.
library;

import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:mobile/features/couple_chat/media_cache.dart';

class MockDio extends Mock implements Dio {}

Response<List<int>> bytesResponse(List<int>? body) => Response<List<int>>(
  data: body,
  statusCode: 200,
  requestOptions: RequestOptions(path: '/'),
);

void main() {
  late MockDio dio;
  late MediaCache cache;
  late Directory tempRoot;

  setUpAll(() => registerFallbackValue(Options()));

  setUp(() {
    tempRoot = Directory.systemTemp.createTempSync('media_cache_test');
    dio = MockDio();
    when(() => dio.interceptors).thenReturn(Interceptors());
    // A real directory rather than path_provider, which is a platform channel
    // with no implementation under `flutter test`.
    cache = MediaCache(injectedDio: dio, directoryProvider: () async => tempRoot);
  });

  tearDown(() {
    if (tempRoot.existsSync()) tempRoot.deleteSync(recursive: true);
  });

  void respondWith(List<int>? body) {
    when(
      () => dio.get<List<int>>(any(), options: any(named: 'options')),
    ).thenAnswer((_) async => bytesResponse(body));
  }

  test('a fetch completes, writes the bytes and returns the file', () async {
    respondWith([1, 2, 3]);

    final file = await cache.file('/api/v1/chat/media/abc');

    // The regression test for the self-awaiting `whenComplete`: before the fix
    // this line never ran, because the Future waited on itself.
    expect(file.existsSync(), isTrue);
    expect(file.readAsBytesSync(), [1, 2, 3]);
  });

  test('the bytes are requested, not JSON', () async {
    respondWith([1]);

    await cache.file('/api/v1/chat/media/abc');

    final options = verify(
      () => dio.get<List<int>>(any(), options: captureAny(named: 'options')),
    ).captured.single as Options;
    expect(options.responseType, ResponseType.bytes);
  });

  test('a second read hits the cache rather than the network', () async {
    respondWith([1, 2, 3]);

    await cache.file('/api/v1/chat/media/abc');
    await cache.file('/api/v1/chat/media/abc');

    // Media is immutable and its id is random, so a file that exists is always
    // the right file.
    verify(() => dio.get<List<int>>(any(), options: any(named: 'options'))).called(1);
  });

  test('two concurrent reads share one download', () async {
    when(
      () => dio.get<List<int>>(any(), options: any(named: 'options')),
    ).thenAnswer((_) async {
      await Future<void>.delayed(const Duration(milliseconds: 20));
      return bytesResponse([1, 2, 3]);
    });

    // A thread scrolling past the same photo twice must not fetch it twice.
    final results = await Future.wait([
      cache.file('/api/v1/chat/media/abc'),
      cache.file('/api/v1/chat/media/abc'),
    ]);

    verify(() => dio.get<List<int>>(any(), options: any(named: 'options'))).called(1);
    expect(results[0].path, results[1].path);
  });

  test('the in-flight entry is released, so a later read still works', () async {
    respondWith([5]);

    await cache.file('/api/v1/chat/media/abc');
    await cache.clear();
    final again = await cache.file('/api/v1/chat/media/abc');

    expect(again.readAsBytesSync(), [5]);
  });

  test('different media get different files', () async {
    respondWith([9]);

    final first = await cache.file('/api/v1/chat/media/one');
    final second = await cache.file('/api/v1/chat/media/two');

    expect(first.path, isNot(second.path));
  });

  test('an empty response is an error, not an empty file', () async {
    respondWith(<int>[]);

    await expectLater(
      cache.file('/api/v1/chat/media/abc'),
      throwsA(isA<StateError>()),
    );
  });

  test('a null body is an error too', () async {
    respondWith(null);

    await expectLater(
      cache.file('/api/v1/chat/media/abc'),
      throwsA(isA<StateError>()),
    );
  });

  test('a failed fetch does not poison the next attempt', () async {
    var calls = 0;
    when(() => dio.get<List<int>>(any(), options: any(named: 'options'))).thenAnswer((
      _,
    ) async {
      calls++;
      if (calls == 1) throw DioException(requestOptions: RequestOptions(path: '/'));
      return bytesResponse([7]);
    });

    await expectLater(cache.file('/api/v1/chat/media/abc'), throwsA(isA<Object>()));
    final file = await cache.file('/api/v1/chat/media/abc');

    expect(file.readAsBytesSync(), [7]);
  });

  test('a truncated file is refetched rather than served', () async {
    respondWith([1, 2, 3]);
    final file = await cache.file('/api/v1/chat/media/abc');

    // What an interrupted download would have left if the write were not
    // staged through a sibling and renamed.
    file.writeAsBytesSync(<int>[]);
    await cache.file('/api/v1/chat/media/abc');

    expect(file.readAsBytesSync(), [1, 2, 3]);
    verify(() => dio.get<List<int>>(any(), options: any(named: 'options'))).called(2);
  });

  test('clearing removes every decrypted file', () async {
    respondWith([1, 2, 3]);
    final file = await cache.file('/api/v1/chat/media/abc');
    expect(file.existsSync(), isTrue);

    await cache.clear();

    // The point of the app lock is that the contents stop being available,
    // including to someone holding the handset and a file browser.
    expect(file.existsSync(), isFalse);
  });

  test('clearing twice is harmless', () async {
    await cache.clear();
    await cache.clear();
  });

  test('a clear that fails does not throw', () async {
    respondWith([1]);
    await cache.file('/api/v1/chat/media/abc');

    // The directory vanishes under it — the alternative to swallowing this is
    // an app that will not lock.
    tempRoot.deleteSync(recursive: true);
    await cache.clear();
  });

  test('after clearing, the next read fetches again', () async {
    respondWith([4]);

    await cache.file('/api/v1/chat/media/abc');
    await cache.clear();
    await cache.file('/api/v1/chat/media/abc');

    verify(() => dio.get<List<int>>(any(), options: any(named: 'options'))).called(2);
  });

  test('a shared instance exists for app-wide clearing', () {
    expect(MediaCache.instance, isNotNull);
  });
}
