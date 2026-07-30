/// Playback, the full-screen viewer, and resolving media from the cache.
///
/// These are the paths a person actually touches — tapping play, dragging the
/// waveform, opening a photo — and until the two seams landed they could only
/// be exercised on a device.
library;

import 'dart:async';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:just_audio/just_audio.dart';
import 'package:mocktail/mocktail.dart';

import 'package:mobile/features/couple_chat/media_cache.dart';
import 'package:mobile/features/couple_chat/models/couple_message.dart';
import 'package:mobile/features/couple_chat/models/message_media.dart';
import 'package:mobile/features/couple_chat/views/media_bubbles.dart';

class MockDio extends Mock implements Dio {}

/// A player that records what it was asked to do.
///
/// Only the members the bubble touches; the rest is noise.
class FakePlayer implements AudioPlayer {
  final _position = StreamController<Duration>.broadcast();
  final _state = StreamController<PlayerState>.broadcast();

  String? loadedPath;
  bool didPlay = false;
  bool didPause = false;
  bool disposed = false;
  double? appliedSpeed;
  final seeks = <Duration>[];
  bool _playing = false;
  bool failOnLoad = false;

  @override
  bool get playing => _playing;

  @override
  Stream<Duration> get positionStream => _position.stream;

  @override
  Stream<PlayerState> get playerStateStream => _state.stream;

  @override
  Future<Duration?> setFilePath(String path, {dynamic initialPosition, bool preload = true, dynamic tag}) async {
    if (failOnLoad) throw Exception('cannot decode');
    loadedPath = path;
    return const Duration(seconds: 8);
  }

  @override
  Future<void> play() async {
    didPlay = true;
    _playing = true;
    _state.add(PlayerState(true, ProcessingState.ready));
  }

  @override
  Future<void> pause() async {
    didPause = true;
    _playing = false;
    _state.add(PlayerState(false, ProcessingState.ready));
  }

  @override
  Future<void> seek(Duration? position, {int? index}) async {
    seeks.add(position ?? Duration.zero);
  }

  @override
  Future<void> setSpeed(double value) async => appliedSpeed = value;

  @override
  Future<void> dispose() async {
    disposed = true;
    await _position.close();
    await _state.close();
  }

  void emitPosition(Duration d) => _position.add(d);
  void emitCompleted() => _state.add(PlayerState(false, ProcessingState.completed));

  @override
  noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

CoupleMessage voiceMessage({
  MessageMedia? media,
  bool isPending = false,
  bool failed = false,
}) => CoupleMessage(
  id: 'm1',
  senderId: 'them',
  kind: 'voice',
  body: '',
  sticker: '',
  media: media ?? remoteVoice(),
  replyTo: null,
  reactions: const [],
  clientId: 'c1',
  isDeleted: false,
  createdAt: DateTime(2026, 7, 30),
  isPending: isPending,
  failed: failed,
);

MessageMedia remoteVoice({List<int> waveform = const [20, 60, 90, 40]}) =>
    MessageMedia(
      id: 'media-1',
      kind: 'voice',
      mime: 'audio/mp4',
      byteSize: 1024,
      url: '/api/v1/chat/media/media-1',
      thumbUrl: null,
      durationMs: 8000,
      waveform: waveform,
      transcript: '',
      transcriptStatus: TranscriptStatus.skipped,
      width: null,
      height: null,
    );

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

/// A 1x1 JPEG, so `Image.file` has something real to decode.
final tinyJpeg = <int>[
  0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
  0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
  0x00, ...List.filled(64, 0x08), 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
  0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x14, 0x00, 0x01,
  ...List.filled(15, 0x00), 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00,
  0x3F, 0x00, 0xD2, 0xCF, 0x20, 0xFF, 0xD9,
];

void main() {
  late Directory tempRoot;
  late MediaCache original;
  late MockDio dio;

  setUpAll(() => registerFallbackValue(Options()));

  setUp(() {
    tempRoot = Directory.systemTemp.createTempSync('bubbles_test');
    dio = MockDio();
    when(() => dio.interceptors).thenReturn(Interceptors());
    when(
      () => dio.get<List<int>>(any(), options: any(named: 'options')),
    ).thenAnswer(
      (_) async => Response<List<int>>(
        data: tinyJpeg,
        statusCode: 200,
        requestOptions: RequestOptions(path: '/'),
      ),
    );

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

  Widget wrap(Widget child) => MaterialApp(
    home: Scaffold(body: Center(child: SizedBox(width: 300, child: child))),
  );

  group('resolving from the cache', () {
    testWidgets('a received photo is fetched and rendered', (tester) async {
      await tester.pumpWidget(
        wrap(ImageBubble(message: CoupleMessage(
          id: 'm2', senderId: 'them', kind: 'image', body: '', sticker: '',
          media: remoteImage(), replyTo: null, reactions: const [],
          clientId: 'c2', isDeleted: false, createdAt: DateTime(2026, 7, 30),
        ))),
      );
      await tester.pumpAndSettle();

      // The thumbnail, not the full image — a scroll past twenty photos must
      // not pull twenty full-size files.
      final requested = verify(
        () => dio.get<List<int>>(captureAny(), options: any(named: 'options')),
      ).captured.single as String;
      expect(requested, '/api/v1/chat/media/media-2/thumb');
      expect(find.byType(Image), findsOneWidget);
    });

    testWidgets('a fetch failure renders unavailable, not a broken image', (
      tester,
    ) async {
      when(
        () => dio.get<List<int>>(any(), options: any(named: 'options')),
      ).thenThrow(DioException(requestOptions: RequestOptions(path: '/')));

      await tester.pumpWidget(
        wrap(ImageBubble(message: CoupleMessage(
          id: 'm2', senderId: 'them', kind: 'image', body: '', sticker: '',
          media: remoteImage(), replyTo: null, reactions: const [],
          clientId: 'c2', isDeleted: false, createdAt: DateTime(2026, 7, 30),
        ))),
      );
      await tester.pumpAndSettle();

      expect(find.text('Unavailable'), findsOneWidget);
    });

    testWidgets('tapping a received photo opens the viewer', (tester) async {
      await tester.pumpWidget(
        wrap(ImageBubble(message: CoupleMessage(
          id: 'm2', senderId: 'them', kind: 'image', body: '', sticker: '',
          media: remoteImage(), replyTo: null, reactions: const [],
          clientId: 'c2', isDeleted: false, createdAt: DateTime(2026, 7, 30),
        ))),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byType(Image).first);
      await tester.pumpAndSettle();

      expect(find.byType(ImageViewer), findsOneWidget);
      expect(find.byType(InteractiveViewer), findsOneWidget);
    });

    testWidgets('a photo still uploading cannot be opened', (tester) async {
      await tester.pumpWidget(
        wrap(ImageBubble(
          message: CoupleMessage.pendingMedia(
            clientId: 'c1', senderId: 'me', kind: 'image',
            localPath: '/tmp/nope.jpg',
          ),
        )),
      );
      await tester.pump();

      // Opening a full-screen view of a file that is still going up would have
      // nothing to show.
      expect(find.byType(GestureDetector), findsNothing);
    });
  });

  group('the full-screen viewer', () {
    Future<void> openViewer(WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(home: Scaffold(body: ImageViewer(media: remoteImage()))),
      );
      await tester.pumpAndSettle();
    }

    testWidgets('it renders the full image, not the thumbnail', (tester) async {
      await openViewer(tester);

      final requested = verify(
        () => dio.get<List<int>>(captureAny(), options: any(named: 'options')),
      ).captured.single as String;
      expect(requested, '/api/v1/chat/media/media-2');
    });

    testWidgets('a small drag springs back', (tester) async {
      await openViewer(tester);

      await tester.dragFrom(const Offset(400, 300), const Offset(0, 40));
      await tester.pumpAndSettle();

      expect(find.byType(ImageViewer), findsOneWidget);
    });

    testWidgets('a long drag dismisses it', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => ImageViewer(media: remoteImage())),
                ),
                child: const Text('open'),
              ),
            ),
          ),
        ),
      );
      await tester.tap(find.text('open'));
      await tester.pumpAndSettle();
      expect(find.byType(ImageViewer), findsOneWidget);

      // Dragged from the middle of the screen rather than from the image: the
      // dismiss listener wraps the whole body, and targeting the decoded image
      // makes the test depend on it having laid out.
      await tester.dragFrom(const Offset(400, 300), const Offset(0, 300));
      await tester.pumpAndSettle();

      expect(find.byType(ImageViewer), findsNothing);
    });
  });

  group('voice playback', () {
    testWidgets('tapping play loads the file and starts', (tester) async {
      final player = FakePlayer();
      await tester.pumpWidget(
        wrap(VoiceBubble(
          message: voiceMessage(), mine: false, playerFactory: () => player,
        )),
      );

      await tester.tap(find.byIcon(Icons.play_arrow_rounded));
      await tester.pumpAndSettle();

      expect(player.loadedPath, isNotNull);
      expect(player.didPlay, isTrue);
      expect(find.byIcon(Icons.pause_rounded), findsOneWidget);
    });

    testWidgets('tapping again pauses rather than restarting', (tester) async {
      final player = FakePlayer();
      await tester.pumpWidget(
        wrap(VoiceBubble(
          message: voiceMessage(), mine: false, playerFactory: () => player,
        )),
      );
      await tester.tap(find.byIcon(Icons.play_arrow_rounded));
      await tester.pumpAndSettle();

      await tester.tap(find.byIcon(Icons.pause_rounded));
      await tester.pumpAndSettle();

      expect(player.didPause, isTrue);
    });

    testWidgets('position updates move the clock', (tester) async {
      final player = FakePlayer();
      await tester.pumpWidget(
        wrap(VoiceBubble(
          message: voiceMessage(), mine: false, playerFactory: () => player,
        )),
      );
      await tester.tap(find.byIcon(Icons.play_arrow_rounded));
      await tester.pumpAndSettle();

      player.emitPosition(const Duration(seconds: 3));
      await tester.pumpAndSettle();

      expect(find.text('0:03'), findsOneWidget);
    });

    testWidgets('finishing rewinds rather than leaving the bar full', (
      tester,
    ) async {
      final player = FakePlayer();
      await tester.pumpWidget(
        wrap(VoiceBubble(
          message: voiceMessage(), mine: false, playerFactory: () => player,
        )),
      );
      await tester.tap(find.byIcon(Icons.play_arrow_rounded));
      await tester.pumpAndSettle();

      player.emitCompleted();
      await tester.pumpAndSettle();

      // The natural next action on a voice note is to play it again.
      expect(player.seeks, contains(Duration.zero));
      expect(player.didPause, isTrue);
    });

    testWidgets('a file that will not load leaves the bubble usable', (
      tester,
    ) async {
      final player = FakePlayer()..failOnLoad = true;
      await tester.pumpWidget(
        wrap(VoiceBubble(
          message: voiceMessage(), mine: false, playerFactory: () => player,
        )),
      );

      await tester.tap(find.byIcon(Icons.play_arrow_rounded));
      await tester.pumpAndSettle();

      expect(player.didPlay, isFalse);
      expect(find.byIcon(Icons.play_arrow_rounded), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('speed cycles 1x, 1.5x, 2x and back', (tester) async {
      final player = FakePlayer();
      await tester.pumpWidget(
        wrap(VoiceBubble(
          message: voiceMessage(), mine: false, playerFactory: () => player,
        )),
      );
      await tester.tap(find.byIcon(Icons.play_arrow_rounded));
      await tester.pumpAndSettle();

      await tester.tap(find.text('1×'));
      await tester.pumpAndSettle();
      expect(player.appliedSpeed, 1.5);

      await tester.tap(find.text('1.5×'));
      await tester.pumpAndSettle();
      expect(player.appliedSpeed, 2.0);

      await tester.tap(find.text('2×'));
      await tester.pumpAndSettle();
      expect(player.appliedSpeed, 1.0);
    });

    testWidgets('dragging the waveform seeks', (tester) async {
      final player = FakePlayer();
      await tester.pumpWidget(
        wrap(VoiceBubble(
          message: voiceMessage(), mine: false, playerFactory: () => player,
        )),
      );
      await tester.tap(find.byIcon(Icons.play_arrow_rounded));
      await tester.pumpAndSettle();

      final waveform = find.byKey(const Key('voice_waveform'));
      expect(waveform, findsOneWidget);
      await tester.dragFrom(tester.getCenter(waveform), const Offset(60, 0));
      await tester.pumpAndSettle();

      // A separate thumb would be a 6px target on a bar that is already the
      // control.
      expect(player.seeks, isNotEmpty);
    });

    testWidgets('the player is disposed with the bubble', (tester) async {
      final player = FakePlayer();
      await tester.pumpWidget(
        wrap(VoiceBubble(
          message: voiceMessage(), mine: false, playerFactory: () => player,
        )),
      );
      await tester.tap(find.byIcon(Icons.play_arrow_rounded));
      await tester.pumpAndSettle();

      await tester.pumpWidget(wrap(const SizedBox()));
      await tester.pumpAndSettle();

      expect(player.disposed, isTrue);
    });

    testWidgets('a pending voice note shows upload progress', (tester) async {
      await tester.pumpWidget(
        wrap(VoiceBubble(
          message: voiceMessage(isPending: true).copyWith(uploadProgress: 0.5),
          mine: true,
        )),
      );
      await tester.pump();

      final bar = tester.widget<LinearProgressIndicator>(
        find.byType(LinearProgressIndicator),
      );
      expect(bar.value, 0.5);
    });

    testWidgets('a failed voice note offers a retry', (tester) async {
      var retried = false;
      await tester.pumpWidget(
        wrap(VoiceBubble(
          message: voiceMessage(failed: true),
          mine: false,
          onRetry: () => retried = true,
        )),
      );
      await tester.pump();

      await tester.tap(find.text('Retry'));
      expect(retried, isTrue);
    });
  });
}
