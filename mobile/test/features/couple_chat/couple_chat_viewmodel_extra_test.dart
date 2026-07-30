/// The view-model paths the main suite leaves alone.
///
/// Pagination, deletion, and the failure branches — the places where a thread
/// quietly loses a message or shows an error it should have absorbed.
library;

import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/features/couple_chat/couple_chat_api_service.dart';
import 'package:mobile/features/couple_chat/couple_chat_viewmodel.dart';
import 'package:mobile/features/couple_chat/models/couple_message.dart';
import 'package:mobile/features/couple_chat/models/message_media.dart';

CoupleMessage message({
  String id = 'm1',
  String sender = 'them',
  String body = 'hello',
  String kind = 'text',
  MessageMedia? media,
  DateTime? at,
}) => CoupleMessage(
  id: id,
  senderId: sender,
  kind: kind,
  body: body,
  sticker: '',
  media: media,
  replyTo: null,
  reactions: const [],
  clientId: id,
  isDeleted: false,
  createdAt: at ?? DateTime(2026, 7, 30, 10),
);

class _FakeApi implements CoupleChatApiService {
  List<CoupleMessage> firstPage = [];
  List<CoupleMessage> olderPage = [];
  bool hasMore = false;
  String? nextBefore;
  bool historyThrows = false;
  bool olderThrows = false;
  bool deleteThrows = false;
  int historyCalls = 0;
  int deleteCalls = 0;
  String? lastBefore;

  @override
  Future<({List<CoupleMessage> messages, bool hasMore, String? nextBefore})>
  history(String relationshipId, {String? before, int limit = 50}) async {
    historyCalls++;
    lastBefore = before;
    if (before == null) {
      if (historyThrows) throw Exception('offline');
      return (messages: firstPage, hasMore: hasMore, nextBefore: nextBefore);
    }
    if (olderThrows) throw Exception('offline');
    return (messages: olderPage, hasMore: false, nextBefore: null);
  }

  @override
  Future<void> markDelivered(String relationshipId) async {}

  @override
  Future<void> markRead(String relationshipId) async {}

  @override
  Future<bool> intimateUnlocked(String relationshipId) async => false;

  @override
  Future<void> deleteMessage(String messageId) async {
    deleteCalls++;
    if (deleteThrows) throw Exception('offline');
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
  }) async => message(id: 'server-$clientId', sender: 'me', body: body ?? '');

  @override
  Future<DraftVerdict> checkDraft(String relationshipId, String draft) async =>
      DraftVerdict.ok;

  @override
  Future<String?> rephrase(String relationshipId, String draft) async =>
      'a kinder version';

  @override
  noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  late _FakeApi api;
  late CoupleChatViewModel vm;

  setUp(() {
    api = _FakeApi();
    vm = CoupleChatViewModel(relationshipId: 'r1', userId: 'me', api: api);
  });

  group('loading', () {
    test('a page populates the thread and its cursor', () async {
      api.firstPage = [message(id: 'm1')];
      api.hasMore = true;
      api.nextBefore = 'cursor';

      await vm.load();

      expect(vm.messages, hasLength(1));
      expect(vm.hasMore, isTrue);
      expect(vm.isLoading, isFalse);
      expect(vm.error, isNull);
    });

    test('a failed load surfaces a readable error', () async {
      api.historyThrows = true;

      await vm.load();

      // The raw "Exception: " prefix is an implementation detail, not
      // something to put in front of someone.
      expect(vm.error, isNotNull);
      expect(vm.error, isNot(contains('Exception:')));
      expect(vm.isLoading, isFalse);
    });

    test('older history is prepended in the right order', () async {
      api.firstPage = [message(id: 'new')];
      api.hasMore = true;
      api.nextBefore = 'cursor';
      await vm.load();
      api.olderPage = [message(id: 'older-2'), message(id: 'older-1')];

      await vm.loadOlder();

      expect(vm.messages.map((m) => m.id), ['older-1', 'older-2', 'new']);
      expect(api.lastBefore, 'cursor');
    });

    test('older history is not fetched without a cursor', () async {
      await vm.loadOlder();
      expect(api.historyCalls, 0);
    });

    test('a failed older fetch does not raise an error banner', () async {
      api.firstPage = [message(id: 'new')];
      api.hasMore = true;
      api.nextBefore = 'cursor';
      await vm.load();
      api.olderThrows = true;

      await vm.loadOlder();

      // Scrolling back and getting nothing is a much smaller failure than the
      // thread appearing broken.
      expect(vm.error, isNull);
      expect(vm.messages, hasLength(1));
      expect(vm.isLoading, isFalse);
    });

    test('a second loadOlder while one is running is ignored', () async {
      api.firstPage = [message(id: 'new')];
      api.hasMore = true;
      api.nextBefore = 'cursor';
      await vm.load();

      final first = vm.loadOlder();
      await vm.loadOlder();
      await first;

      expect(api.historyCalls, 2, reason: 'the initial load plus one older');
    });
  });

  group('deleting', () {
    test('a deleted message leaves the thread', () async {
      api.firstPage = [message(id: 'm1'), message(id: 'm2')];
      await vm.load();
      final target = vm.messages.firstWhere((m) => m.id == 'm1');

      await vm.deleteMessage(target);

      expect(vm.messages.map((m) => m.id), ['m2']);
    });

    test('a failed delete leaves the message in place', () async {
      api.firstPage = [message(id: 'm1')];
      await vm.load();
      api.deleteThrows = true;

      await vm.deleteMessage(vm.messages.single);

      expect(vm.messages, hasLength(1));
    });

    test('deleting something not in the thread is harmless', () async {
      await vm.deleteMessage(message(id: 'ghost'));

      expect(api.deleteCalls, 1);
      expect(vm.messages, isEmpty);
    });
  });

  group('composing', () {
    test('a reply is quoted and then cleared', () async {
      api.firstPage = [message(id: 'm1', body: 'are we still on?')];
      await vm.load();

      vm.startReply(vm.messages.single);
      expect(vm.replyingTo?.id, 'm1');

      vm.cancelReply();
      expect(vm.replyingTo, isNull);
    });

    test('a media send carries the quote through and clears it', () async {
      api.firstPage = [message(id: 'm1', body: 'look at this')];
      await vm.load();
      vm.startReply(vm.messages.single);

      final pending = vm.sendMedia(localPath: '/tmp/a.jpg', kind: 'image');

      expect(vm.messages.last.replyTo?.id, 'm1');
      expect(vm.replyingTo, isNull);
      await pending;
    });

    test('a draft check and a rephrase reach the API', () async {
      expect((await vm.checkDraft('you always')).caution, isFalse);
      expect(await vm.rephrase('you always'), 'a kinder version');
    });
  });

  group('transcripts', () {
    test('a message with no media asks for nothing', () async {
      await vm.loadTranscript(message(id: 'm1'));
      // No media, no request, no crash.
      expect(vm.messages, isEmpty);
    });

    test('an image never asks for a transcript', () async {
      final photo = message(
        id: 'm1',
        kind: 'image',
        media: MessageMedia.local(kind: 'image', localPath: '/tmp/a.jpg'),
      );

      await vm.loadTranscript(photo);

      expect(vm.messages, isEmpty);
    });
  });
}
