/// What the screen does with what the server pushes, and with a picked photo.
///
/// The routing in `_handleSocketEvent` is the difference between a thread that
/// updates live and one that only updates on a refetch — which in practice
/// means "never, while someone is looking at it".
library;

import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import 'package:mobile/features/bliss/bliss_viewmodel.dart';
import 'package:mobile/features/couple_chat/couple_chat_api_service.dart';
import 'package:mobile/features/couple_chat/couple_chat_socket.dart';
import 'package:mobile/features/couple_chat/couple_chat_viewmodel.dart';
import 'package:mobile/features/couple_chat/models/couple_message.dart';
import 'package:mobile/features/couple_chat/models/message_media.dart';
import 'package:mobile/features/couple_chat/views/couple_chat_screen.dart';

class _StubApi implements CoupleChatApiService {
  List<CoupleMessage> history_ = [];
  final sent = <Map<String, dynamic>>[];
  bool uploadThrows = false;

  @override
  Future<({List<CoupleMessage> messages, bool hasMore, String? nextBefore})>
  history(String relationshipId, {String? before, int limit = 50}) async =>
      (messages: history_, hasMore: false, nextBefore: null);

  @override
  Future<void> markRead(String relationshipId) async {}

  @override
  Future<void> markDelivered(String relationshipId) async {}

  @override
  Future<bool> intimateUnlocked(String relationshipId) async => false;

  @override
  Future<DraftVerdict> checkDraft(String r, String draft) async =>
      DraftVerdict.ok;

  @override
  Future<({String? guidance, bool deferToSupport})> readCoach(
    String relationshipId,
    String messageId,
  ) async => (guidance: null, deferToSupport: false);

  @override
  Future<CoupleMessage> toggleReaction(String messageId, String emoji) async =>
      history_.firstWhere((m) => m.id == messageId);

  @override
  Future<void> deleteMessage(String messageId) async {}

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
    if (uploadThrows) throw Exception('offline');
    return MessageMedia(
      id: 'media-1',
      kind: kind,
      mime: 'image/jpeg',
      byteSize: 1,
      url: '/api/v1/chat/media/media-1',
      thumbUrl: '/api/v1/chat/media/media-1/thumb',
      durationMs: durationMs,
      waveform: waveform ?? const [],
      transcript: '',
      transcriptStatus: TranscriptStatus.skipped,
      width: 800,
      height: 600,
    );
  }

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
    sent.add({'body': body, 'mediaId': mediaId, 'mediaKind': mediaKind});
    return CoupleMessage(
      id: 'server-$clientId',
      senderId: 'me',
      kind: mediaKind ?? 'text',
      body: body ?? '',
      sticker: '',
      replyTo: null,
      reactions: const [],
      clientId: clientId,
      isDeleted: false,
      createdAt: DateTime(2026, 7, 30),
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// A picker that hands back a path without touching a platform channel.
class _StubPicker implements ImagePicker {
  String? path;
  bool throws = false;
  ImageSource? lastSource;
  double? maxWidth;

  @override
  Future<XFile?> pickImage({
    required ImageSource source,
    double? maxWidth,
    double? maxHeight,
    int? imageQuality,
    CameraDevice preferredCameraDevice = CameraDevice.rear,
    bool requestFullMetadata = true,
  }) async {
    lastSource = source;
    this.maxWidth = maxWidth;
    if (throws) throw Exception('no camera');
    return path == null ? null : XFile(path!);
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  late _StubApi api;
  late CoupleChatViewModel vm;
  late _StubPicker picker;
  late void Function(Map<String, dynamic>) emit;
  late File photo;

  setUp(() {
    api = _StubApi();
    picker = _StubPicker();
    photo = File(
      '${Directory.systemTemp.createTempSync('pick_test').path}/photo.jpg',
    )..writeAsBytesSync([0xFF, 0xD8, 0xFF, 0xD9]);
  });

  tearDown(() {
    if (photo.existsSync()) photo.parent.deleteSync(recursive: true);
  });

  Future<void> pump(WidgetTester tester, {List<CoupleMessage> history = const []}) async {
    api.history_ = history;
    vm = CoupleChatViewModel(relationshipId: 'r1', userId: 'me', api: api);
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<CoupleChatViewModel>.value(value: vm),
          ChangeNotifierProvider(create: (_) => BlissViewModel()),
        ],
        child: MaterialApp(
          home: CoupleChatScreen(
            relationshipId: 'r1',
            userId: 'me',
            partnerName: 'Sam',
            imagePicker: picker,
            socketFactory: ({
              required String relationshipId,
              required void Function(Map<String, dynamic>) onEvent,
              required VoidCallback onConnectionLost,
            }) {
              emit = onEvent;
              return CoupleChatSocket(
                relationshipId: relationshipId,
                onEvent: onEvent,
                onConnectionLost: onConnectionLost,
                // Never opens: the events are injected directly.
                tokenProvider: () async => null,
              );
            },
          ),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();
  }

  Map<String, dynamic> incoming(String id, String body) => {
    'type': 'couple_message',
    'message': {
      'id': id,
      'sender_id': 'them',
      'kind': 'text',
      'body': body,
      'sticker': '',
      'reactions': <dynamic>[],
      'client_id': id,
      'is_deleted': false,
      'created_at': '2026-07-30T10:00:00Z',
    },
  };

  group('socket routing', () {
    testWidgets('an incoming message lands in the thread', (tester) async {
      await pump(tester);

      emit(incoming('x', 'are you up?'));
      await tester.pumpAndSettle();

      expect(find.text('are you up?'), findsOneWidget);
    });

    testWidgets('a malformed message payload is ignored', (tester) async {
      await pump(tester);

      emit({'type': 'couple_message', 'message': 'not a map'});
      await tester.pumpAndSettle();

      expect(vm.messages, isEmpty);
      expect(tester.takeException(), isNull);
    });

    testWidgets('a remote delete tombstones the message', (tester) async {
      await pump(tester);
      emit(incoming('x', 'oops'));
      await tester.pumpAndSettle();

      emit({'type': 'couple_message_deleted', 'message_id': 'x'});
      await tester.pumpAndSettle();

      expect(find.text('oops'), findsNothing);
    });

    testWidgets('a remote reaction reaches the bubble', (tester) async {
      await pump(tester);
      emit(incoming('x', 'hello'));
      await tester.pumpAndSettle();

      emit({
        'type': 'couple_message_reaction',
        'message_id': 'x',
        'reactions': [
          {'emoji': '😍', 'count': 1, 'user_ids': ['me']},
        ],
      });
      await tester.pumpAndSettle();

      expect(find.textContaining('😍'), findsOneWidget);
    });

    testWidgets('thread_ready sets presence', (tester) async {
      await pump(tester);

      emit({'type': 'thread_ready', 'partner_online': true});
      await tester.pumpAndSettle();

      expect(find.textContaining('Online'), findsOneWidget);
    });

    testWidgets('a presence change is reflected', (tester) async {
      await pump(tester);
      emit({'type': 'thread_ready', 'partner_online': true});
      await tester.pumpAndSettle();

      emit({'type': 'presence', 'online': false});
      await tester.pumpAndSettle();

      expect(find.textContaining('Online'), findsNothing);
    });

    testWidgets('a receipt advances the sender ticks', (tester) async {
      await pump(tester, history: [
        CoupleMessage(
          id: 'mine',
          senderId: 'me',
          kind: 'text',
          body: 'are we still on?',
          sticker: '',
          replyTo: null,
          reactions: const [],
          clientId: 'mine',
          isDeleted: false,
          createdAt: DateTime.utc(2026, 7, 30, 9),
        ),
      ]);
      expect(find.text('Sent'), findsOneWidget);

      emit({
        'type': 'couple_receipt',
        'last_delivered_at': '2026-07-30T10:00:00Z',
        'last_read_at': null,
      });
      await tester.pumpAndSettle();

      // Without this the sender only ever sees ticks move on a refetch.
      expect(find.text('Delivered'), findsOneWidget);
    });

    testWidgets('an unknown event type is harmless', (tester) async {
      await pump(tester);

      emit({'type': 'something_new'});
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
    });
  });

  group('picking a photo', () {
    Future<void> choose(WidgetTester tester, Key option) async {
      await tester.tap(find.byKey(const Key('attach_button')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(option));
      await tester.pumpAndSettle();
    }

    testWidgets('the library option picks and sends', (tester) async {
      picker.path = photo.path;
      await pump(tester);

      await choose(tester, const Key('attach_library'));

      expect(picker.lastSource, ImageSource.gallery);
      expect(api.sent.single['mediaKind'], 'image');
    });

    testWidgets('the camera option picks from the camera', (tester) async {
      picker.path = photo.path;
      await pump(tester);

      await choose(tester, const Key('attach_camera'));

      expect(picker.lastSource, ImageSource.camera);
    });

    testWidgets('the photo is downscaled before it leaves the device', (
      tester,
    ) async {
      picker.path = photo.path;
      await pump(tester);

      await choose(tester, const Key('attach_library'));

      // Uploading a 12MP original over a phone connection is a slow progress
      // ring for no gain — the server re-encodes anyway.
      expect(picker.maxWidth, 2048);
    });

    testWidgets('the composer text becomes the caption', (tester) async {
      picker.path = photo.path;
      await pump(tester);
      await tester.enterText(find.byType(TextField), 'us last summer');
      await tester.pumpAndSettle();

      await choose(tester, const Key('attach_library'));

      expect(api.sent.single['body'], 'us last summer');
      expect(
        tester.widget<TextField>(find.byType(TextField)).controller!.text,
        '',
      );
    });

    testWidgets('cancelling the picker sends nothing', (tester) async {
      picker.path = null;
      await pump(tester);

      await choose(tester, const Key('attach_library'));

      expect(api.sent, isEmpty);
    });

    testWidgets('a picker failure says so rather than throwing', (
      tester,
    ) async {
      picker.throws = true;
      await pump(tester);

      await choose(tester, const Key('attach_library'));

      expect(find.text('Could not open that photo.'), findsOneWidget);
      expect(api.sent, isEmpty);
      await tester.pump(const Duration(seconds: 5));
    });
  });
}
