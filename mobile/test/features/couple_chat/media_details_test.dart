/// The last corners: amplitude sampling, waveform downsampling, sticker
/// picking, and the states a bubble passes through on the way to rendering.
library;

import 'dart:async';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:record/record.dart';

import 'package:mobile/features/couple_chat/media_cache.dart';
import 'package:mobile/features/couple_chat/models/couple_message.dart';
import 'package:mobile/features/couple_chat/models/message_media.dart';
import 'package:mobile/features/couple_chat/models/sticker_catalogue.dart';
import 'package:mobile/features/couple_chat/views/media_bubbles.dart';
import 'package:mobile/features/couple_chat/views/sticker_picker_sheet.dart';
import 'package:mobile/features/couple_chat/views/voice_recorder.dart';

class MockDio extends Mock implements Dio {}

/// A 1x1 JPEG, so a completed download has something decodable in it.
final tinyJpeg = <int>[
  0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
  0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
  0x00, ...List.filled(64, 0x08), 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
  0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x14, 0x00, 0x01,
  ...List.filled(15, 0x00), 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00,
  0x3F, 0x00, 0xD2, 0xCF, 0x20, 0xFF, 0xD9,
];

Response<List<int>> jpegResponse() => Response<List<int>>(
  data: tinyJpeg,
  statusCode: 200,
  requestOptions: RequestOptions(path: '/'),
);

/// Emits amplitudes on demand so the live waveform can be driven.
class _AmplitudeRecorder implements AudioRecorder {
  final _amplitudes = StreamController<Amplitude>.broadcast();
  static String? lastPath;

  void emit(double dbfs) => _amplitudes.add(Amplitude(current: dbfs, max: 0));

  @override
  Future<bool> hasPermission({bool request = true}) async => true;

  @override
  Future<void> start(RecordConfig config, {required String path}) async {
    lastPath = path;
    File(path).writeAsBytesSync([1, 2, 3]);
  }

  @override
  Future<String?> stop() async => lastPath;

  @override
  Stream<Amplitude> onAmplitudeChanged(Duration interval) => _amplitudes.stream;

  @override
  Future<void> dispose() async {
    if (!_amplitudes.isClosed) unawaited(_amplitudes.close());
  }

  @override
  noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

MessageMedia remoteImage() => MessageMedia(
  id: 'media-2',
  kind: 'image',
  mime: 'image/jpeg',
  byteSize: 2048,
  url: '/api/v1/chat/media/media-2',
  thumbUrl: '/api/v1/chat/media/media-2/thumb',
  durationMs: null,
  waveform: const [],
  transcript: '',
  transcriptStatus: TranscriptStatus.skipped,
  width: 800,
  height: 600,
);

CoupleMessage imageMessage(MessageMedia? media) => CoupleMessage(
  id: 'm1',
  senderId: 'them',
  kind: 'image',
  body: '',
  sticker: '',
  media: media,
  replyTo: null,
  reactions: const [],
  clientId: 'c1',
  isDeleted: false,
  createdAt: DateTime(2026, 7, 30),
);

void main() {
  group('the live waveform', () {
    late Directory tempDir;
    late GlobalKey<VoiceRecorderBarState> key;
    late List<VoiceRecording> completed;
    late _AmplitudeRecorder recorder;

    setUp(() {
      tempDir = Directory.systemTemp.createTempSync('wf_test');
      key = GlobalKey<VoiceRecorderBarState>();
      completed = [];
      recorder = _AmplitudeRecorder();
    });

    tearDown(() {
      if (tempDir.existsSync()) tempDir.deleteSync(recursive: true);
    });

    Future<void> pump(WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: VoiceRecorderBar(
              key: key,
              onComplete: completed.add,
              onActiveChanged: (_) {},
              recorderFactory: () => recorder,
              directoryProvider: () async => tempDir,
            ),
          ),
        ),
      );
      unawaited(key.currentState!.start());
      await tester.pump();
      await tester.pump();
    }

    testWidgets('amplitudes become bars', (tester) async {
      await pump(tester);

      recorder.emit(-60); // silence
      recorder.emit(-30); // halfway
      recorder.emit(0); // loud
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 1200));

      unawaited(key.currentState!.onRelease());
      for (var i = 0; i < 8; i++) {
        await tester.pump();
      }

      expect(completed.single.waveform, [0, 50, 100]);
    });

    testWidgets('a nonsense amplitude reads as silence', (tester) async {
      await pump(tester);

      // The platform reports -infinity when there is no signal at all, and a
      // NaN bar height throws in layout.
      recorder.emit(double.negativeInfinity);
      recorder.emit(double.nan);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 1200));

      unawaited(key.currentState!.onRelease());
      for (var i = 0; i < 8; i++) {
        await tester.pump();
      }

      expect(completed.single.waveform, [0, 0]);
    });

    testWidgets('a long recording is squeezed into a fixed bar count', (
      tester,
    ) async {
      await pump(tester);

      // A six-second note and a two-minute one have to draw the same shape.
      for (var i = 0; i < 200; i++) {
        recorder.emit(-30);
      }
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 1200));

      unawaited(key.currentState!.onRelease());
      for (var i = 0; i < 8; i++) {
        await tester.pump();
      }

      expect(completed.single.waveform, hasLength(48));
      expect(completed.single.waveform.every((v) => v == 50), isTrue);
    });
  });

  group('the sticker sheet', () {
    testWidgets('picking one closes the sheet and reports it', (tester) async {
      String? picked;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () => StickerPickerSheet.show(
                  context,
                  intimateUnlocked: false,
                  onPick: (id) => picked = id,
                ),
                child: const Text('open'),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('open'));
      await tester.pumpAndSettle();
      final firstSticker = kStickerPacks.first.stickers.first;
      await tester.tap(find.text(firstSticker.glyph).first);
      await tester.pumpAndSettle();

      expect(picked, firstSticker.id);
      // The sheet closes on pick: choosing a sticker is the whole interaction.
      expect(find.text('open'), findsOneWidget);
    });
  });

  group('bubble states', () {
    late Directory tempRoot;
    late MediaCache original;
    late MockDio dio;
    late Completer<Response<List<int>>> pending;

    setUpAll(() => registerFallbackValue(Options()));

    setUp(() {
      tempRoot = Directory.systemTemp.createTempSync('details_test');
      dio = MockDio();
      pending = Completer<Response<List<int>>>();
      when(() => dio.interceptors).thenReturn(Interceptors());
      when(
        () => dio.get<List<int>>(any(), options: any(named: 'options')),
      ).thenAnswer((_) => pending.future);

      original = MediaCache.instance;
      MediaCache.instance = MediaCache(
        injectedDio: dio,
        directoryProvider: () async => tempRoot,
      );
    });

    tearDown(() {
      MediaCache.instance = original;
      if (tempRoot.existsSync()) tempRoot.deleteSync(recursive: true);
    });

    testWidgets('a photo shows a placeholder while it downloads', (
      tester,
    ) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SizedBox(width: 300, child: ImageBubble(message: imageMessage(remoteImage()))),
          ),
        ),
      );
      await tester.pump();

      // Not blank and not an error — the thread keeps its shape while the
      // bytes are in flight.
      expect(find.byType(Image), findsNothing);
      expect(find.text('Unavailable'), findsNothing);
      pending.complete(jpegResponse());
      await tester.pumpAndSettle();
    });

    testWidgets('media with no path at all renders the placeholder', (
      tester,
    ) async {
      final media = MessageMedia(
        id: 'm',
        kind: 'image',
        mime: '',
        byteSize: 0,
        url: '',
        thumbUrl: null,
        durationMs: null,
        waveform: const [],
        transcript: '',
        transcriptStatus: TranscriptStatus.skipped,
        width: null,
        height: null,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SizedBox(width: 300, child: ImageBubble(message: imageMessage(media))),
          ),
        ),
      );
      await tester.pump();

      expect(tester.takeException(), isNull);
      pending.complete(jpegResponse());
      await tester.pumpAndSettle();
    });

    testWidgets('swapping the media re-resolves rather than showing the old one', (
      tester,
    ) async {
      Widget bubbleFor(MessageMedia media) => MaterialApp(
        home: Scaffold(
          body: SizedBox(width: 300, child: ImageBubble(message: imageMessage(media))),
        ),
      );

      await tester.pumpWidget(bubbleFor(remoteImage()));
      await tester.pump();

      final second = MessageMedia(
        id: 'media-3',
        kind: 'image',
        mime: 'image/jpeg',
        byteSize: 1,
        url: '/api/v1/chat/media/media-3',
        thumbUrl: '/api/v1/chat/media/media-3/thumb',
        durationMs: null,
        waveform: const [],
        transcript: '',
        transcriptStatus: TranscriptStatus.skipped,
        width: 800,
        height: 600,
      );
      await tester.pumpWidget(bubbleFor(second));
      await tester.pump();

      final requested = verify(
        () => dio.get<List<int>>(captureAny(), options: any(named: 'options')),
      ).captured;
      expect(requested, [
        '/api/v1/chat/media/media-2/thumb',
        '/api/v1/chat/media/media-3/thumb',
      ]);
      pending.complete(jpegResponse());
      await tester.pumpAndSettle();
    });
  });
}
