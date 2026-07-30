import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/couple_chat/couple_chat_api_service.dart';
import 'package:mobile/features/couple_chat/couple_chat_viewmodel.dart';
import 'package:mobile/features/couple_chat/models/couple_message.dart';
import 'package:mobile/features/couple_chat/models/sticker_catalogue.dart';

/// Just enough API to exercise the cursors. The network behaviour of the
/// thread is covered in couple_chat_viewmodel_test.dart; this file is only
/// about what the ticks are allowed to claim.
class _StubApi implements CoupleChatApiService {
  List<CoupleMessage> historyResult = [];
  int deliveredCalls = 0;

  @override
  Future<({List<CoupleMessage> messages, bool hasMore, String? nextBefore})>
  history(String relationshipId, {String? before, int limit = 50}) async {
    return (messages: historyResult, hasMore: false, nextBefore: null);
  }

  @override
  Future<void> markDelivered(String relationshipId) async {
    deliveredCalls++;
  }

  bool unlocked = false;
  String? sentSticker;
  bool sendThrows = false;

  @override
  Future<bool> intimateUnlocked(String relationshipId) async => unlocked;

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
    sentSticker = sticker;
    if (sendThrows) throw Exception('offline');
    return CoupleMessage(
      id: 'server-$clientId',
      senderId: 'me',
      kind: sticker != null ? 'sticker' : 'text',
      body: body ?? '',
      sticker: sticker ?? '',
      replyTo: null,
      reactions: const [],
      clientId: clientId,
      isDeleted: false,
      createdAt: DateTime(2026),
    );
  }

  @override
  Future<({String? guidance, bool deferToSupport})> readCoach(
    String relationshipId,
    String incoming,
  ) async => (guidance: null, deferToSupport: false);

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// Ticks.
///
/// Every case here is a way the status could lie, because a delivery receipt
/// that overstates itself is worse than none: it tells someone their message
/// was seen and ignored when it was neither.
void main() {
  CoupleMessage mine(String id, DateTime at, {MessageStatus? serverStatus}) {
    return CoupleMessage(
      id: id,
      senderId: 'me',
      kind: 'text',
      body: id,
      sticker: '',
      replyTo: null,
      reactions: const [],
      clientId: id,
      isDeleted: false,
      createdAt: at,
      serverStatus: serverStatus,
    );
  }

  CoupleChatViewModel build(_StubApi api) =>
      CoupleChatViewModel(relationshipId: 'r1', userId: 'me', api: api);

  final t0 = DateTime(2026, 7, 28, 12, 0);

  group('delivery status', () {
    test('a message with no partner cursor reads as sent', () {
      final vm = build(_StubApi());
      expect(vm.statusFor(mine('a', t0)), MessageStatus.sent);
    });

    test('the partner receiving moves it to delivered, not seen', () {
      final vm = build(_StubApi())
        ..onPartnerReceipt(deliveredAt: t0.add(const Duration(seconds: 1)));
      expect(vm.statusFor(mine('a', t0)), MessageStatus.delivered);
    });

    test('the partner reading moves it to seen', () {
      final vm = build(_StubApi())
        ..onPartnerReceipt(readAt: t0.add(const Duration(seconds: 1)));
      expect(vm.statusFor(mine('a', t0)), MessageStatus.seen);
    });

    test('a read cursor implies delivery even when none was reported', () {
      // Reading straight from a push notification: no delivery ack was ever
      // sent, but the message plainly arrived.
      final vm = build(_StubApi())..onPartnerReceipt(readAt: t0);
      expect(vm.partnerDeliveredAt, isNotNull);
    });

    test('a message sent after they read stays on one tick', () {
      final vm = build(_StubApi())..onPartnerReceipt(readAt: t0);
      expect(
        vm.statusFor(mine('later', t0.add(const Duration(minutes: 5)))),
        MessageStatus.sent,
      );
    });

    test('a late stale receipt cannot walk a tick backwards', () {
      final vm = build(_StubApi())
        ..onPartnerReceipt(readAt: t0)
        ..onPartnerReceipt(
          deliveredAt: t0.subtract(const Duration(hours: 1)),
          readAt: t0.subtract(const Duration(hours: 1)),
        );
      expect(vm.statusFor(mine('a', t0)), MessageStatus.seen);
    });

    test('pending and failed outrank any cursor', () {
      final vm = build(_StubApi())..onPartnerReceipt(readAt: t0);
      final pending = mine('a', t0).copyWith(isPending: true);
      final failed = mine('b', t0).copyWith(failed: true);
      expect(vm.statusFor(pending), MessageStatus.sending);
      expect(vm.statusFor(failed), MessageStatus.failed);
    });

    test('the partner\'s own messages carry no status', () {
      final vm = build(_StubApi())..onPartnerReceipt(readAt: t0);
      final theirs = CoupleMessage(
        id: 'x',
        senderId: 'them',
        kind: 'text',
        body: 'hi',
        sticker: '',
        replyTo: null,
        reactions: const [],
        clientId: '',
        isDeleted: false,
        createdAt: t0,
      );
      expect(vm.statusFor(theirs), isNull);
    });

    test('loading seeds the cursors from what the server said', () async {
      // History reports per-message status, not cursors. Inverting it is what
      // lets a message that arrives over the socket a moment later still get
      // the right tick without another fetch.
      final api = _StubApi()
        ..historyResult = [
          mine('old', t0, serverStatus: MessageStatus.seen),
          mine('mid', t0.add(const Duration(minutes: 1)),
              serverStatus: MessageStatus.delivered),
        ].reversed.toList();
      final vm = build(api);
      await vm.load();

      expect(vm.partnerReadAt, t0);
      expect(vm.partnerDeliveredAt, t0.add(const Duration(minutes: 1)));
    });

    test('loading acknowledges delivery', () async {
      final api = _StubApi();
      await build(api).load();
      expect(api.deliveredCalls, 1);
    });

    test('an incoming message from them acknowledges delivery', () {
      final api = _StubApi();
      final vm = build(api);
      vm.onIncoming(
        CoupleMessage(
          id: 'x',
          senderId: 'them',
          kind: 'text',
          body: 'hi',
          sticker: '',
          replyTo: null,
          reactions: const [],
          clientId: '',
          isDeleted: false,
          createdAt: t0,
        ),
      );
      expect(api.deliveredCalls, 1);
    });
  });

  _stickerTests();

  group('presence', () {
    test('starts offline — we have not heard anything yet', () {
      expect(build(_StubApi()).partnerOnline, isFalse);
    });

    test('a presence event flips it', () {
      final vm = build(_StubApi())..onPartnerPresence(true);
      expect(vm.partnerOnline, isTrue);
    });

    test('losing the socket falls back to offline, not to the last value', () {
      // The risk being tested is a stale "Online" outliving the connection
      // that justified it, while someone waits for a reply that is not coming.
      final vm = build(_StubApi())..onPartnerPresence(true);
      vm.onSocketLost();
      expect(vm.partnerOnline, isFalse);
    });
  });
}

/// Stickers.
///
/// The catalogue is data, so the tests that matter are about the promises the
/// data makes: stable ids, a gate that fails closed, and an unknown id that
/// degrades rather than disappearing.
void _stickerTests() {
  group('sticker catalogue', () {
    test('ids are unique across every pack', () {
      final ids = [
        for (final pack in kStickerPacks)
          for (final sticker in pack.stickers) sticker.id,
      ];
      expect(ids.toSet().length, ids.length);
    });

    test('ids are namespaced strings, never positional', () {
      // A sticker's meaning is stored in the thread forever. If ids were
      // indexes, reordering this file would rewrite what someone said.
      for (final pack in kStickerPacks) {
        for (final sticker in pack.stickers) {
          expect(sticker.id, startsWith('${pack.key}.'));
          expect(int.tryParse(sticker.id), isNull);
        }
      }
    });

    test('every sticker has a label a screen reader can say', () {
      for (final pack in kStickerPacks) {
        for (final sticker in pack.stickers) {
          expect(sticker.label.trim(), isNotEmpty);
        }
      }
    });

    test('exactly the intimate pack is gated', () {
      final gated = kStickerPacks.where((p) => p.intimate).map((p) => p.key);
      expect(gated, ['close']);
    });

    test('there is a repair pack, and it is not gated', () {
      // The one pack that earns its place in this product specifically: a
      // repair attempt has to be reachable at the worst moment, not behind
      // a consent flow.
      final repair = kStickerPacks.firstWhere((p) => p.key == 'repair');
      expect(repair.intimate, isFalse);
      expect(repair.stickers, isNotEmpty);
    });

    test('an unknown id resolves to null rather than throwing', () {
      expect(stickerById('nope.gone'), isNull);
    });
  });

  group('sending stickers', () {
    test('a sticker sends as a sticker, not as text', () async {
      final api = _StubApi();
      final vm = CoupleChatViewModel(
        relationshipId: 'r1',
        userId: 'me',
        api: api,
      );
      await vm.sendSticker('love.heart');
      expect(api.sentSticker, 'love.heart');
      expect(vm.messages.single.kind, 'sticker');
      expect(vm.messages.single.sticker, 'love.heart');
    });

    test('a failed sticker keeps the bubble and retries as a sticker', () async {
      final api = _StubApi()..sendThrows = true;
      final vm = CoupleChatViewModel(
        relationshipId: 'r1',
        userId: 'me',
        api: api,
      );
      await vm.sendSticker('repair.sorry');
      expect(vm.messages.single.failed, isTrue);

      api
        ..sendThrows = false
        ..sentSticker = null;
      await vm.retry(vm.messages.single);
      // The bug this guards: retry() used to resend `body`, which is empty on
      // a sticker — the retry would have silently sent nothing.
      expect(api.sentSticker, 'repair.sorry');
    });

    test('the intimate gate is closed until the server opens it', () async {
      final api = _StubApi();
      final vm = CoupleChatViewModel(
        relationshipId: 'r1',
        userId: 'me',
        api: api,
      );
      expect(vm.intimateUnlocked, isFalse);
      await vm.load();
      await Future<void>.delayed(Duration.zero);
      expect(vm.intimateUnlocked, isFalse);

      api.unlocked = true;
      await vm.load();
      await Future<void>.delayed(Duration.zero);
      expect(vm.intimateUnlocked, isTrue);
    });
  });
}
