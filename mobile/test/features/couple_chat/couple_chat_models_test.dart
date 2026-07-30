/// Parsing and the small derived values the UI leans on.
///
/// Unglamorous, and the place a renamed server field goes unnoticed until a
/// bubble renders blank on someone's phone.
library;

import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/features/couple_chat/models/couple_message.dart';
import 'package:mobile/features/couple_chat/models/message_media.dart';

Map<String, dynamic> fullMessageJson() => {
  'id': 'm1',
  'sender_id': 'them',
  'kind': 'image',
  'body': 'a caption',
  'sticker': '',
  'media': {
    'id': 'media-1',
    'kind': 'image',
    'mime': 'image/jpeg',
    'byte_size': 2048,
    'url': '/api/v1/chat/media/media-1',
    'thumb_url': '/api/v1/chat/media/media-1/thumb',
    'duration_ms': null,
    'waveform': <int>[],
    'transcript': '',
    'transcript_status': 'skipped',
    'width': 1600,
    'height': 1200,
  },
  'reply_to': {
    'id': 'm0',
    'sender_id': 'me',
    'body': '',
    'is_deleted': false,
    'kind': 'voice',
    'thumb_url': null,
  },
  'reactions': [
    {'emoji': '😍', 'count': 2, 'user_ids': ['me', 'them']},
  ],
  'client_id': 'c1',
  'is_deleted': false,
  'status': 'seen',
  'created_at': '2026-07-30T10:00:00Z',
};

void main() {
  group('CoupleMessage parsing', () {
    test('a full payload round-trips every field', () {
      final message = CoupleMessage.fromJson(fullMessageJson());

      expect(message.id, 'm1');
      expect(message.kind, 'image');
      expect(message.body, 'a caption');
      expect(message.media?.id, 'media-1');
      expect(message.replyTo?.kind, 'voice');
      expect(message.reactions.single.count, 2);
      expect(message.serverStatus, MessageStatus.seen);
      expect(message.isMedia, isTrue);
    });

    test('every server status maps to a state', () {
      for (final entry in {
        'sent': MessageStatus.sent,
        'delivered': MessageStatus.delivered,
        'seen': MessageStatus.seen,
      }.entries) {
        final json = fullMessageJson()..['status'] = entry.key;
        expect(CoupleMessage.fromJson(json).serverStatus, entry.value);
      }
    });

    test('a message with no status has none', () {
      final json = fullMessageJson()..['status'] = null;
      expect(CoupleMessage.fromJson(json).serverStatus, isNull);
    });

    test('an unparseable timestamp falls back rather than throwing', () {
      final json = fullMessageJson()..['created_at'] = 'not a date';

      // A malformed timestamp should cost the bubble its ordering, not the
      // whole thread its render.
      expect(CoupleMessage.fromJson(json).createdAt, isA<DateTime>());
    });

    test('missing optional fields degrade to empties', () {
      final message = CoupleMessage.fromJson({
        'id': 'm1',
        'created_at': '2026-07-30T10:00:00Z',
      });

      expect(message.kind, 'text');
      expect(message.body, '');
      expect(message.media, isNull);
      expect(message.replyTo, isNull);
      expect(message.reactions, isEmpty);
      expect(message.clientId, '');
      expect(message.isDeleted, isFalse);
    });

    test('isMine compares the sender', () {
      final message = CoupleMessage.fromJson(fullMessageJson());
      expect(message.isMine('them'), isTrue);
      expect(message.isMine('me'), isFalse);
    });
  });

  group('reactions', () {
    test('a group knows who reacted', () {
      final group = MessageReactionGroup.fromJson({
        'emoji': '🔥',
        'count': 1,
        'user_ids': ['me'],
      });

      expect(group.reactedBy('me'), isTrue);
      expect(group.reactedBy('them'), isFalse);
    });

    test('a malformed group degrades rather than throwing', () {
      final group = MessageReactionGroup.fromJson({});
      expect(group.emoji, '');
      expect(group.count, 0);
      expect(group.userIds, isEmpty);
    });
  });

  group('reply previews', () {
    test('a quoted photo carries its thumbnail', () {
      final quote = ReplyPreview.fromJson({
        'id': 'm0',
        'sender_id': 'me',
        'body': 'summer',
        'is_deleted': false,
        'kind': 'image',
        'thumb_url': '/api/v1/chat/media/x/thumb',
      });

      expect(quote.thumbUrl, isNotNull);
      expect(quote.label, '📷 Photo');
    });

    test('every kind has a label, and text has none', () {
      ReplyPreview quote(String kind) => ReplyPreview(
        id: 'q',
        senderId: 'me',
        body: '',
        isDeleted: false,
        kind: kind,
      );

      expect(quote('image').label, '📷 Photo');
      expect(quote('voice').label, '🎤 Voice message');
      expect(quote('sticker').label, 'Sticker');
      // A text quote shows its own body; a label would be redundant.
      expect(quote('text').label, '');
    });

    test('a minimal payload parses', () {
      final quote = ReplyPreview.fromJson({'id': 'm0'});
      expect(quote.kind, 'text');
      expect(quote.body, '');
      expect(quote.thumbUrl, isNull);
    });
  });

  group('MessageMedia', () {
    MessageMedia parse(Map<String, dynamic> overrides) => MessageMedia.fromJson({
      'id': 'media-1',
      'kind': 'voice',
      'mime': 'audio/mp4',
      'byte_size': 1024,
      'url': '/api/v1/chat/media/media-1',
      'duration_ms': 65000,
      'waveform': [1, 2],
      'transcript': '',
      'transcript_status': 'skipped',
      ...overrides,
    });

    test('every transcript status maps', () {
      for (final entry in {
        'pending': TranscriptStatus.pending,
        'ok': TranscriptStatus.ok,
        'failed': TranscriptStatus.failed,
        'skipped': TranscriptStatus.skipped,
        'nonsense': TranscriptStatus.skipped,
      }.entries) {
        expect(
          parse({'transcript_status': entry.key}).transcriptStatus,
          entry.value,
        );
      }
    });

    test('kind predicates', () {
      expect(parse({'kind': 'voice'}).isVoice, isTrue);
      expect(parse({'kind': 'voice'}).isImage, isFalse);
      expect(parse({'kind': 'image'}).isImage, isTrue);
    });

    test('hasTranscript needs both a status and some text', () {
      expect(parse({'transcript_status': 'ok', 'transcript': 'hi'}).hasTranscript, isTrue);
      // Status says ok but the text is empty: nothing to show.
      expect(parse({'transcript_status': 'ok'}).hasTranscript, isFalse);
      expect(parse({'transcript_status': 'pending', 'transcript': 'hi'}).hasTranscript, isFalse);
    });

    test('duration renders as mm:ss past a minute', () {
      expect(parse({'duration_ms': 65000}).durationLabel, '1:05');
      expect(parse({'duration_ms': 8000}).durationLabel, '0:08');
      expect(parse({'duration_ms': null}).durationLabel, '0:00');
    });

    test('aspect ratio uses the real dimensions when it has them', () {
      expect(parse({'width': 1600, 'height': 800}).aspectRatio, 2.0);
    });

    test('aspect ratio falls back rather than dividing by zero', () {
      // A zero height would be NaN, and NaN in an AspectRatio throws in layout.
      expect(parse({'width': 100, 'height': 0}).aspectRatio, closeTo(4 / 3, 0.001));
      expect(parse({'width': null, 'height': null}).aspectRatio, closeTo(4 / 3, 0.001));
    });

    test('a local stand-in reports itself as local', () {
      final local = MessageMedia.local(
        kind: 'voice',
        localPath: '/tmp/note.m4a',
        durationMs: 3000,
        waveform: const [5],
      );

      expect(local.isLocal, isTrue);
      expect(local.durationMs, 3000);
      expect(local.waveform, const [5]);
      expect(parse({}).isLocal, isFalse);
    });

    test('copyWith replaces only what it is given', () {
      final original = parse({'transcript_status': 'pending'});

      final updated = original.copyWith(
        transcript: 'i miss you',
        transcriptStatus: TranscriptStatus.ok,
      );

      expect(updated.transcript, 'i miss you');
      expect(updated.transcriptStatus, TranscriptStatus.ok);
      // Everything else is carried through.
      expect(updated.id, original.id);
      expect(updated.url, original.url);
      expect(updated.durationMs, original.durationMs);
      expect(updated.waveform, original.waveform);
    });

    test('copyWith with nothing keeps the original values', () {
      final original = parse({'transcript': 'kept', 'transcript_status': 'ok'});
      final copy = original.copyWith();

      expect(copy.transcript, 'kept');
      expect(copy.transcriptStatus, TranscriptStatus.ok);
    });

    test('missing fields degrade to empties', () {
      final media = MessageMedia.fromJson({'id': 'm'});

      expect(media.kind, 'image');
      expect(media.mime, '');
      expect(media.byteSize, 0);
      expect(media.url, '');
      expect(media.thumbUrl, isNull);
      expect(media.waveform, isEmpty);
      expect(media.transcript, '');
    });
  });

  group('optimistic bubbles', () {
    test('a pending text bubble is marked pending', () {
      final message = CoupleMessage.pending(
        clientId: 'c1',
        senderId: 'me',
        body: 'hello',
      );

      expect(message.isPending, isTrue);
      expect(message.id, 'c1');
      expect(message.kind, 'text');
    });

    test('a pending sticker bubble carries the sticker', () {
      final message = CoupleMessage.pendingSticker(
        clientId: 'c1',
        senderId: 'me',
        sticker: 'hug',
      );

      expect(message.kind, 'sticker');
      expect(message.sticker, 'hug');
      expect(message.isPending, isTrue);
    });

    test('a pending media bubble starts at zero progress', () {
      final message = CoupleMessage.pendingMedia(
        clientId: 'c1',
        senderId: 'me',
        kind: 'image',
        localPath: '/tmp/a.jpg',
        body: 'caption',
      );

      expect(message.uploadProgress, 0);
      expect(message.media?.localPath, '/tmp/a.jpg');
      expect(message.body, 'caption');
      expect(message.isMediaTombstone, isFalse);
    });

    test('copyWith carries media and progress through', () {
      final message = CoupleMessage.pendingMedia(
        clientId: 'c1',
        senderId: 'me',
        kind: 'image',
        localPath: '/tmp/a.jpg',
      );

      final updated = message.copyWith(uploadProgress: 0.6, failed: true);

      expect(updated.uploadProgress, 0.6);
      expect(updated.failed, isTrue);
      expect(updated.media?.localPath, '/tmp/a.jpg');
    });
  });
}
