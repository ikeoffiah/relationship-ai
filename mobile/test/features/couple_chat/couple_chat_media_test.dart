/// Photos and voice notes in the couple's thread.
///
/// The properties worth holding: a media bubble is on screen before the upload
/// finishes, a failed send is recoverable without paying for the upload twice,
/// destroyed bytes render as a tombstone rather than a broken image, and the
/// mic never appears next to a composer that has something to send.
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/features/couple_chat/couple_chat_api_service.dart';
import 'package:mobile/features/couple_chat/couple_chat_viewmodel.dart';
import 'package:mobile/features/couple_chat/models/couple_message.dart';
import 'package:mobile/features/couple_chat/models/message_media.dart';
import 'package:mobile/features/couple_chat/views/media_bubbles.dart';

CoupleMessage _message({
  required String kind,
  MessageMedia? media,
  String body = '',
  bool isPending = false,
  bool failed = false,
  double? uploadProgress,
  String id = 'm1',
}) {
  return CoupleMessage(
    id: id,
    senderId: 'me',
    kind: kind,
    body: body,
    sticker: '',
    media: media,
    replyTo: null,
    reactions: const [],
    clientId: id,
    isDeleted: false,
    createdAt: DateTime(2026, 7, 30),
    isPending: isPending,
    failed: failed,
    uploadProgress: uploadProgress,
  );
}

MessageMedia _remoteVoice({
  String transcript = '',
  TranscriptStatus status = TranscriptStatus.skipped,
  List<int> waveform = const [40, 80, 20],
}) {
  return MessageMedia(
    id: 'media-1',
    kind: 'voice',
    mime: 'audio/mp4',
    byteSize: 1024,
    url: '/api/v1/chat/media/media-1',
    thumbUrl: null,
    durationMs: 8000,
    waveform: waveform,
    transcript: transcript,
    transcriptStatus: status,
    width: null,
    height: null,
  );
}

class _FakeApi implements CoupleChatApiService {
  bool uploadThrows = false;
  bool sendThrows = false;
  int uploadCalls = 0;
  int sendCalls = 0;
  String? lastMediaId;
  String? lastMediaKind;
  List<int>? lastWaveform;
  MessageMedia metaResult = _remoteVoice(
    transcript: 'i miss you',
    status: TranscriptStatus.ok,
  );

  @override
  Future<MessageMedia> uploadMedia(
    String relationshipId, {
    required String path,
    required String kind,
    int? durationMs,
    List<int>? waveform,
    void Function(double)? onProgress,
    dynamic cancelToken,
  }) async {
    uploadCalls++;
    lastWaveform = waveform;
    onProgress?.call(0.5);
    if (uploadThrows) throw Exception('offline');
    return MessageMedia(
      id: 'media-uploaded',
      kind: kind,
      mime: kind == 'voice' ? 'audio/mp4' : 'image/jpeg',
      byteSize: 2048,
      url: '/api/v1/chat/media/media-uploaded',
      thumbUrl: kind == 'image' ? '/api/v1/chat/media/media-uploaded/thumb' : null,
      durationMs: durationMs,
      waveform: waveform ?? const [],
      transcript: '',
      transcriptStatus: TranscriptStatus.skipped,
      width: kind == 'image' ? 800 : null,
      height: kind == 'image' ? 600 : null,
    );
  }

  @override
  Future<MessageMedia> mediaMeta(String mediaId) async => metaResult;

  @override
  Future<CoupleMessage> send(
    String relationshipId, {
    required String clientId,
    String? body,
    String? sticker,
    String? replyTo,
    String? mediaId,
    String? mediaKind,
  }) async {
    sendCalls++;
    lastMediaId = mediaId;
    lastMediaKind = mediaKind;
    if (sendThrows) throw Exception('offline');
    return _message(
      kind: mediaKind ?? 'text',
      id: 'server-$clientId',
      body: body ?? '',
    );
  }

  @override
  Future<({List<CoupleMessage> messages, bool hasMore, String? nextBefore})>
  history(String relationshipId, {String? before, int limit = 50}) async =>
      (messages: <CoupleMessage>[], hasMore: false, nextBefore: null);

  @override
  noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  group('sending media', () {
    late _FakeApi api;
    late CoupleChatViewModel vm;

    setUp(() {
      api = _FakeApi();
      vm = CoupleChatViewModel(relationshipId: 'r1', userId: 'me', api: api);
    });

    test('the bubble is on screen before the upload finishes', () async {
      final future = vm.sendMedia(localPath: '/tmp/photo.jpg', kind: 'image');

      // Not awaited yet: this is the whole point of the optimistic bubble.
      expect(vm.messages, hasLength(1));
      expect(vm.messages.first.isPending, isTrue);
      expect(vm.messages.first.media?.localPath, '/tmp/photo.jpg');

      await future;
    });

    test('progress reaches the bubble while it uploads', () async {
      // The highest value seen, not the first — the first notify is the
      // optimistic bubble being added at zero.
      var highest = 0.0;
      vm.addListener(() {
        final progress = vm.messages.first.uploadProgress ?? 0;
        if (progress > highest) highest = progress;
      });

      await vm.sendMedia(localPath: '/tmp/photo.jpg', kind: 'image');

      expect(highest, greaterThan(0));
    });

    test('a sent photo is reconciled with the server copy', () async {
      await vm.sendMedia(localPath: '/tmp/photo.jpg', kind: 'image');

      expect(vm.messages.single.id, startsWith('server-'));
      expect(vm.messages.single.isPending, isFalse);
      expect(api.lastMediaId, 'media-uploaded');
      expect(api.lastMediaKind, 'image');
    });

    test('a caption travels with the photo', () async {
      await vm.sendMedia(
        localPath: '/tmp/photo.jpg',
        kind: 'image',
        caption: 'us last summer',
      );

      expect(vm.messages.single.body, 'us last summer');
    });

    test('a voice note carries its duration and waveform', () async {
      await vm.sendMedia(
        localPath: '/tmp/note.m4a',
        kind: 'voice',
        durationMs: 4200,
        waveform: const [10, 90],
      );

      expect(api.lastWaveform, const [10, 90]);
      expect(api.lastMediaKind, 'voice');
    });

    test('a failed upload keeps the bubble and marks it failed', () async {
      api.uploadThrows = true;

      await vm.sendMedia(localPath: '/tmp/photo.jpg', kind: 'image');

      // A message that vanishes on a flaky connection is worse than one you
      // can see and retry.
      expect(vm.messages, hasLength(1));
      expect(vm.messages.single.failed, isTrue);
      expect(vm.messages.single.isPending, isFalse);
    });

    test('retrying a failed upload uploads again', () async {
      api.uploadThrows = true;
      await vm.sendMedia(localPath: '/tmp/photo.jpg', kind: 'image');
      api.uploadThrows = false;

      await vm.retry(vm.messages.single);

      expect(api.uploadCalls, 2);
      expect(vm.messages.single.failed, isFalse);
    });

    test('retrying after a failed *send* does not re-upload', () async {
      // The bytes are already on the server; paying for them twice on a poor
      // connection is exactly what the retry path exists to avoid.
      api.sendThrows = true;
      await vm.sendMedia(localPath: '/tmp/photo.jpg', kind: 'image');
      expect(api.uploadCalls, 1);
      api.sendThrows = false;

      await vm.retry(vm.messages.single);

      expect(api.uploadCalls, 1);
      expect(api.sendCalls, 2);
      expect(api.lastMediaId, 'media-uploaded');
    });

    test('retrying a bubble with no local file does nothing', () async {
      final orphan = _message(kind: 'image', failed: true);

      await vm.retry(orphan);

      expect(api.uploadCalls, 0);
      expect(api.sendCalls, 0);
    });
  });

  group('transcripts', () {
    late _FakeApi api;
    late CoupleChatViewModel vm;

    setUp(() {
      api = _FakeApi();
      vm = CoupleChatViewModel(relationshipId: 'r1', userId: 'me', api: api);
    });

    test('a transcript that arrives later is fetched on demand', () async {
      await vm.sendMedia(
        localPath: '/tmp/note.m4a',
        kind: 'voice',
        durationMs: 3000,
      );
      final message = _message(kind: 'voice', media: _remoteVoice(), id: 'server-x');
      vm.onIncoming(message);

      await vm.loadTranscript(vm.messages.last);

      expect(vm.messages.last.media?.transcript, 'i miss you');
    });

    test('a note that already has its transcript is not refetched', () async {
      vm.onIncoming(
        _message(
          kind: 'voice',
          id: 'v1',
          media: _remoteVoice(transcript: 'already here', status: TranscriptStatus.ok),
        ),
      );
      api.metaResult = _remoteVoice(transcript: 'SHOULD NOT APPEAR');

      await vm.loadTranscript(vm.messages.last);

      expect(vm.messages.last.media?.transcript, 'already here');
    });
  });

  group('model', () {
    test('a media message whose bytes are gone is a tombstone', () {
      expect(_message(kind: 'image').isMediaTombstone, isTrue);
      expect(
        _message(kind: 'voice', media: _remoteVoice()).isMediaTombstone,
        isFalse,
      );
    });

    test('duration renders as mm:ss', () {
      expect(_remoteVoice().durationLabel, '0:08');
    });

    test('a photo without dimensions falls back to a stable ratio', () {
      final local = MessageMedia.local(kind: 'image', localPath: '/tmp/a.jpg');
      expect(local.aspectRatio, closeTo(4 / 3, 0.001));
      expect(local.isLocal, isTrue);
    });

    test('a quoted photo shows a label rather than an empty line', () {
      const quote = ReplyPreview(
        id: 'q',
        senderId: 'them',
        body: '',
        isDeleted: false,
        kind: 'image',
      );
      expect(quote.label, '📷 Photo');
    });

    test('a quoted voice note names itself', () {
      const quote = ReplyPreview(
        id: 'q',
        senderId: 'them',
        body: '',
        isDeleted: false,
        kind: 'voice',
      );
      expect(quote.label, '🎤 Voice message');
    });

    test('transcript status parses from the wire', () {
      final media = MessageMedia.fromJson({
        'id': 'm',
        'kind': 'voice',
        'transcript_status': 'pending',
        'waveform': [1, 2],
      });
      expect(media.transcriptStatus, TranscriptStatus.pending);
      expect(media.hasTranscript, isFalse);
    });
  });

  group('bubbles', () {
    // Width-constrained the way a real bubble is (76% of screen). Without it
    // a 4:3 photo exactly fills the 800x600 test surface and any caption
    // overflows — an artefact of the harness, not of the bubble.
    Widget wrap(Widget child) => MaterialApp(
      home: Scaffold(
        body: Center(child: SizedBox(width: 300, child: child)),
      ),
    );

    testWidgets('a photo still uploading shows a progress ring', (tester) async {
      await tester.pumpWidget(
        wrap(
          ImageBubble(
            message: _message(
              kind: 'image',
              media: MessageMedia.local(kind: 'image', localPath: '/tmp/x.jpg'),
              isPending: true,
              uploadProgress: 0.4,
            ),
          ),
        ),
      );

      final indicator = tester.widget<CircularProgressIndicator>(
        find.byType(CircularProgressIndicator),
      );
      expect(indicator.value, 0.4);
    });

    testWidgets('a stalled upload shows an indeterminate ring', (tester) async {
      await tester.pumpWidget(
        wrap(
          ImageBubble(
            message: _message(
              kind: 'image',
              media: MessageMedia.local(kind: 'image', localPath: '/tmp/x.jpg'),
              isPending: true,
              uploadProgress: 0,
            ),
          ),
        ),
      );

      // Null rather than a confident 0%, which would read as progress.
      final indicator = tester.widget<CircularProgressIndicator>(
        find.byType(CircularProgressIndicator),
      );
      expect(indicator.value, isNull);
    });

    testWidgets('a failed photo offers a retry', (tester) async {
      var retried = false;
      await tester.pumpWidget(
        wrap(
          ImageBubble(
            message: _message(
              kind: 'image',
              media: MessageMedia.local(kind: 'image', localPath: '/tmp/x.jpg'),
              failed: true,
            ),
            onRetry: () => retried = true,
          ),
        ),
      );

      await tester.tap(find.byIcon(Icons.refresh_rounded));
      expect(retried, isTrue);
    });

    testWidgets('a caption renders under the photo', (tester) async {
      await tester.pumpWidget(
        wrap(
          ImageBubble(
            message: _message(
              kind: 'image',
              media: MessageMedia.local(kind: 'image', localPath: '/tmp/x.jpg'),
              body: 'us last summer',
            ),
          ),
        ),
      );

      expect(find.text('us last summer'), findsOneWidget);
    });

    testWidgets('a media message with no media renders unavailable', (tester) async {
      await tester.pumpWidget(
        wrap(ImageBubble(message: _message(kind: 'image'))),
      );

      expect(find.text('Unavailable'), findsOneWidget);
    });

    testWidgets('a voice bubble shows its duration before playing', (tester) async {
      await tester.pumpWidget(
        wrap(
          VoiceBubble(
            message: _message(kind: 'voice', media: _remoteVoice()),
            mine: false,
          ),
        ),
      );

      expect(find.text('0:08'), findsOneWidget);
      expect(find.byIcon(Icons.play_arrow_rounded), findsOneWidget);
    });

    testWidgets('a note with no transcript offers no transcript control', (
      tester,
    ) async {
      await tester.pumpWidget(
        wrap(
          VoiceBubble(
            message: _message(kind: 'voice', media: _remoteVoice()),
            mine: false,
          ),
        ),
      );

      // assist off means skipped, and a control that reveals nothing is noise.
      expect(find.text('Transcript'), findsNothing);
    });

    testWidgets('tapping Transcript expands it', (tester) async {
      await tester.pumpWidget(
        wrap(
          VoiceBubble(
            message: _message(
              kind: 'voice',
              media: _remoteVoice(
                transcript: 'i felt alone',
                status: TranscriptStatus.ok,
              ),
            ),
            mine: false,
          ),
        ),
      );

      expect(find.text('i felt alone'), findsNothing);
      await tester.tap(find.text('Transcript'));
      await tester.pump();

      expect(find.text('i felt alone'), findsOneWidget);
      expect(find.text('Hide transcript'), findsOneWidget);
    });

    testWidgets('expanding a pending transcript asks the server once', (
      tester,
    ) async {
      var requests = 0;
      await tester.pumpWidget(
        wrap(
          VoiceBubble(
            message: _message(
              kind: 'voice',
              media: _remoteVoice(status: TranscriptStatus.pending),
            ),
            mine: false,
            onRequestTranscript: () async => requests++,
          ),
        ),
      );

      await tester.tap(find.text('Transcript'));
      await tester.pump();

      expect(requests, 1);
      expect(find.text('Still transcribing…'), findsOneWidget);
    });

    testWidgets('a failed transcript says so without alarming anyone', (
      tester,
    ) async {
      await tester.pumpWidget(
        wrap(
          VoiceBubble(
            message: _message(
              kind: 'voice',
              media: _remoteVoice(status: TranscriptStatus.failed),
            ),
            mine: false,
          ),
        ),
      );

      await tester.tap(find.text('Transcript'));
      await tester.pump();

      expect(find.text('No transcript for this one.'), findsOneWidget);
    });

    testWidgets('a note with no waveform still draws bars to scrub', (
      tester,
    ) async {
      await tester.pumpWidget(
        wrap(
          VoiceBubble(
            message: _message(
              kind: 'voice',
              media: _remoteVoice(waveform: const []),
            ),
            mine: false,
          ),
        ),
      );

      // Falls back rather than rendering an empty row that cannot be dragged.
      expect(find.byType(VoiceBubble), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}
