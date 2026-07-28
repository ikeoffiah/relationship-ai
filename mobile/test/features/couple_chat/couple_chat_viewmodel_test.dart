import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/couple_chat/couple_chat_api_service.dart';
import 'package:mobile/features/couple_chat/couple_chat_viewmodel.dart';
import 'package:mobile/features/couple_chat/models/couple_message.dart';

/// The behaviour that matters most here is what happens when the network
/// misbehaves: a message must never silently vanish, and the thread must never
/// wait on a round-trip to feel alive.
class _FakeApi implements CoupleChatApiService {
  List<CoupleMessage> historyResult = [];
  bool sendThrows = false;
  bool reactThrows = false;
  DraftVerdict verdict = DraftVerdict.ok;
  int sendCalls = 0;
  int readCoachCalls = 0;
  ({String? guidance, bool deferToSupport}) coachResult = (
    guidance: null,
    deferToSupport: false,
  );
  CoupleMessage? reactionResult;

  @override
  Future<({List<CoupleMessage> messages, bool hasMore, String? nextBefore})>
  history(String relationshipId, {String? before, int limit = 50}) async {
    return (messages: historyResult, hasMore: false, nextBefore: null);
  }

  @override
  Future<CoupleMessage> send(
    String relationshipId, {
    required String clientId,
    String? body,
    String? sticker,
    String? replyTo,
  }) async {
    sendCalls++;
    if (sendThrows) throw Exception('offline');
    return CoupleMessage(
      id: 'server-$clientId',
      senderId: 'me',
      kind: 'text',
      body: body ?? '',
      sticker: '',
      // The real API echoes the quoted stub back; the double must too, or the
      // test passes against behaviour the server does not have.
      replyTo: replyTo == null
          ? null
          : ReplyPreview(
              id: replyTo,
              senderId: 'them',
              body: 'are we still on?',
              isDeleted: false,
            ),
      reactions: const [],
      clientId: clientId,
      isDeleted: false,
      createdAt: DateTime.now(),
    );
  }

  @override
  Future<CoupleMessage> toggleReaction(String messageId, String emoji) async {
    if (reactThrows) throw Exception('offline');
    return reactionResult!;
  }

  @override
  Future<void> deleteMessage(String messageId) async {}

  @override
  Future<void> markRead(String relationshipId) async {}

  @override
  Future<DraftVerdict> checkDraft(String relationshipId, String draft) async =>
      verdict;

  @override
  Future<String?> rephrase(String relationshipId, String draft) async => null;

  @override
  Future<({String? guidance, bool deferToSupport})> readCoach(
    String relationshipId,
    String message,
  ) async {
    readCoachCalls++;
    return coachResult;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

CoupleMessage _message({
  String id = 'm1',
  String sender = 'them',
  String body = 'hi',
  List<MessageReactionGroup> reactions = const [],
}) {
  return CoupleMessage(
    id: id,
    senderId: sender,
    kind: 'text',
    body: body,
    sticker: '',
    replyTo: null,
    reactions: reactions,
    clientId: '',
    isDeleted: false,
    createdAt: DateTime.now(),
  );
}

void main() {
  late _FakeApi api;
  late CoupleChatViewModel vm;

  setUp(() {
    api = _FakeApi();
    vm = CoupleChatViewModel(
      relationshipId: 'rel-1',
      userId: 'me',
      api: api,
    );
  });

  group('optimistic send', () {
    test('the bubble appears before the server answers', () async {
      final future = vm.send('hello');

      // Rendered synchronously — the thread does not wait on the network.
      expect(vm.messages.single.body, 'hello');
      expect(vm.messages.single.isPending, isTrue);

      await future;
      expect(vm.messages.single.isPending, isFalse);
      expect(vm.messages.single.id, startsWith('server-'));
    });

    test('a failed send keeps the message and marks it retryable', () async {
      api.sendThrows = true;

      await vm.send('important thing');

      // A message that vanishes on a flaky connection is worse than one the
      // user can see and retry.
      expect(vm.messages.single.body, 'important thing');
      expect(vm.messages.single.failed, isTrue);
      expect(vm.messages.single.isPending, isFalse);
    });

    test('retry resends and clears the failed state', () async {
      api.sendThrows = true;
      await vm.send('try me');
      api.sendThrows = false;

      await vm.retry(vm.messages.single);

      expect(vm.messages.single.failed, isFalse);
      expect(vm.messages.length, 1, reason: 'retry must not duplicate');
      expect(api.sendCalls, 2);
    });

    test('empty and whitespace drafts are ignored', () async {
      await vm.send('   ');
      expect(vm.messages, isEmpty);
      expect(api.sendCalls, 0);
    });

    test('each send carries a distinct client id for idempotency', () async {
      await vm.send('one');
      await vm.send('two');
      final ids = vm.messages.map((m) => m.clientId).toSet();
      expect(ids.length, 2);
    });
  });

  group('replies', () {
    test('a reply carries the quoted message and clears after sending',
        () async {
      final quoted = _message(body: 'are we still on?');
      vm.startReply(quoted);
      expect(vm.replyingTo, quoted);

      await vm.send('yes!');

      expect(vm.replyingTo, isNull, reason: 'reply state resets after send');
      expect(vm.messages.last.replyTo?.body, 'are we still on?');
    });

    test('cancelling a reply clears it', () {
      vm.startReply(_message());
      vm.cancelReply();
      expect(vm.replyingTo, isNull);
    });
  });

  group('reactions', () {
    test('a failed reaction rolls back to the previous state', () async {
      api.historyResult = [_message(id: 'm1')];
      await vm.load();
      api.reactThrows = true;

      await vm.toggleReaction(vm.messages.single, '❤️');

      expect(vm.messages.single.reactions, isEmpty);
    });

    test('a successful reaction replaces the message', () async {
      api.historyResult = [_message(id: 'm1')];
      await vm.load();
      api.reactionResult = _message(
        id: 'm1',
        reactions: const [
          MessageReactionGroup(emoji: '❤️', count: 1, userIds: ['me']),
        ],
      );

      await vm.toggleReaction(vm.messages.single, '❤️');

      expect(vm.messages.single.reactions.single.emoji, '❤️');
    });

    test('the offered emoji are affectionate, not a generic set', () {
      expect(kCoupleReactions, contains('❤️'));
      expect(kCoupleReactions, isNot(contains('👍')));
    });
  });

  group('incoming messages', () {
    test('a duplicate push is ignored', () {
      vm.onIncoming(_message(id: 'x'));
      vm.onIncoming(_message(id: 'x'));
      expect(vm.messages.length, 1);
    });

    test("our own echo does not trigger private coaching", () async {
      vm.onIncoming(_message(id: 'mine', sender: 'me', body: 'you always'));
      await Future<void>.delayed(Duration.zero);
      expect(api.readCoachCalls, 0);
    });

    test('a hard message from the partner can surface private guidance',
        () async {
      api.coachResult = (guidance: 'Take a breath first.', deferToSupport: false);

      vm.onIncoming(_message(id: 'theirs', body: 'you never listen'));
      await Future<void>.delayed(Duration.zero);

      expect(vm.coachGuidance, 'Take a breath first.');
      vm.dismissCoach();
      expect(vm.coachGuidance, isNull);
    });

    test('abuse signals surface support rather than coaching', () async {
      api.coachResult = (guidance: null, deferToSupport: true);

      vm.onIncoming(_message(id: 'theirs', body: "you're not allowed to go"));
      await Future<void>.delayed(Duration.zero);

      expect(vm.coachDefersToSupport, isTrue);
      expect(vm.coachGuidance, isNull);
    });
  });

  group('draft check', () {
    test('a caution is reported to the caller, not enforced', () async {
      api.verdict = const DraftVerdict(
        caution: true,
        reason: 'sweeping',
        suggestion: 'I felt unheard.',
      );

      final verdict = await vm.checkDraft('you never listen');

      expect(verdict.caution, isTrue);
      // The view model never blocks — sending remains entirely the caller's call.
      await vm.send('you never listen');
      expect(vm.messages.single.body, 'you never listen');
    });
  });

  group('history', () {
    test('history renders oldest first', () async {
      // The API returns newest-first.
      api.historyResult = [
        _message(id: 'b', body: 'second'),
        _message(id: 'a', body: 'first'),
      ];

      await vm.load();

      expect(vm.messages.map((m) => m.body), ['first', 'second']);
    });
  });
}
