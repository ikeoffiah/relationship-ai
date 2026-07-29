import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:mobile/features/bliss/bliss_viewmodel.dart';
import 'package:mobile/features/couple_chat/couple_chat_api_service.dart';
import 'package:mobile/features/couple_chat/couple_chat_viewmodel.dart';
import 'package:mobile/features/couple_chat/models/couple_message.dart';
import 'package:mobile/features/couple_chat/views/couple_chat_screen.dart';
import 'package:mobile/features/couple_chat/views/sticker_picker_sheet.dart';

/// What the thread actually renders.
///
/// The viewmodel tests cover what the statuses mean; these cover whether the
/// right thing appears on screen for each one — which is where a correct model
/// and a wrong widget still add up to a user being misled.
class _StubApi implements CoupleChatApiService {
  List<CoupleMessage> history_ = [];

  @override
  Future<({List<CoupleMessage> messages, bool hasMore, String? nextBefore})>
  history(String relationshipId, {String? before, int limit = 50}) async {
    return (messages: history_, hasMore: false, nextBefore: null);
  }

  @override
  Future<void> markRead(String relationshipId) async {}

  @override
  Future<void> markDelivered(String relationshipId) async {}

  @override
  Future<bool> intimateUnlocked(String relationshipId) async => false;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// The socket is never connected in a widget test, so nothing here needs to be
/// stubbed beyond keeping load() from hanging.
class _StubVm extends CoupleChatViewModel {
  _StubVm(_StubApi api)
    : super(relationshipId: 'r1', userId: 'me', api: api, uuid: null);
}

void main() {
  CoupleMessage message({
    required String id,
    String? senderId = 'me',
    String kind = 'text',
    String body = 'hello',
    String sticker = '',
    DateTime? at,
  }) {
    return CoupleMessage(
      id: id,
      senderId: senderId,
      kind: kind,
      body: body,
      sticker: sticker,
      replyTo: null,
      reactions: const [],
      clientId: id,
      isDeleted: false,
      createdAt: at ?? DateTime(2026, 7, 28, 12),
    );
  }

  Future<CoupleChatViewModel> pump(
    WidgetTester tester,
    List<CoupleMessage> history,
  ) async {
    final api = _StubApi()..history_ = history;
    final vm = _StubVm(api);
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<CoupleChatViewModel>.value(value: vm),
          ChangeNotifierProvider(create: (_) => BlissViewModel()),
        ],
        child: const MaterialApp(
          home: CoupleChatScreen(
            relationshipId: 'r1',
            userId: 'me',
            partnerName: 'Sam',
          ),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();
    return vm;
  }

  testWidgets('a message you sent shows one tick until they receive it', (
    tester,
  ) async {
    await pump(tester, [message(id: 'a')]);
    expect(find.text('Sent'), findsOneWidget);
    expect(find.text('Delivered'), findsNothing);
    expect(find.text('Seen'), findsNothing);
  });

  testWidgets('their delivery receipt moves it to Delivered', (tester) async {
    final vm = await pump(tester, [message(id: 'a')]);
    vm.onPartnerReceipt(deliveredAt: DateTime(2026, 7, 28, 12, 1));
    await tester.pump();
    expect(find.text('Delivered'), findsOneWidget);
  });

  testWidgets('their read receipt moves it to Seen', (tester) async {
    final vm = await pump(tester, [message(id: 'a')]);
    vm.onPartnerReceipt(readAt: DateTime(2026, 7, 28, 12, 1));
    await tester.pump();
    expect(find.text('Seen'), findsOneWidget);
  });

  testWidgets('only the newest of your messages spells the status out', (
    tester,
  ) async {
    // Repeating "Delivered" down the whole thread is noise; the bottom one is
    // the one anyone is asking about.
    await pump(tester, [
      message(id: 'a', at: DateTime(2026, 7, 28, 12)),
      message(id: 'b', at: DateTime(2026, 7, 28, 12, 5)),
    ]);
    expect(find.text('Sent'), findsOneWidget);
  });

  testWidgets('their messages carry no status at all', (tester) async {
    await pump(tester, [message(id: 'a', senderId: 'them')]);
    expect(find.text('Sent'), findsNothing);
    expect(find.text('Delivered'), findsNothing);
    expect(find.text('Seen'), findsNothing);
  });

  testWidgets('presence appears only while they are here', (tester) async {
    final vm = await pump(tester, [message(id: 'a')]);
    expect(find.text('Online'), findsNothing);

    vm.onPartnerPresence(true);
    await tester.pump();
    expect(find.text('Online'), findsOneWidget);

    // Offline is the absence of a line, never a label — the header must not
    // become a board for one partner to watch the other on.
    vm.onPartnerPresence(false);
    await tester.pump();
    expect(find.text('Online'), findsNothing);
    expect(find.text('Offline'), findsNothing);
  });

  testWidgets('a system line is not attributed to the partner', (tester) async {
    await pump(tester, [
      message(
        id: 'sys',
        senderId: null,
        kind: 'system',
        body: 'Bliss will remind you both about call the venue',
      ),
    ]);
    expect(find.textContaining('call the venue'), findsOneWidget);
    // No ticks on a message nobody sent.
    expect(find.text('Sent'), findsNothing);
  });

  testWidgets('a sticker renders as its glyph, not as empty text', (
    tester,
  ) async {
    await pump(tester, [
      message(id: 's', kind: 'sticker', body: '', sticker: 'love.heart'),
    ]);
    expect(find.text('❤️'), findsOneWidget);
  });

  testWidgets('an unknown sticker id degrades rather than vanishing', (
    tester,
  ) async {
    await pump(tester, [
      message(id: 's', kind: 'sticker', body: '', sticker: 'from.the.future'),
    ]);
    expect(find.text('Sticker'), findsOneWidget);
  });

  testWidgets('the sticker tray hides the intimate pack when it is locked', (
    tester,
  ) async {
    await pump(tester, [message(id: 'a')]);
    await tester.tap(find.byKey(const Key('sticker_button')));
    await tester.pumpAndSettle();

    expect(find.byType(StickerPickerSheet), findsOneWidget);
    expect(find.text('Repair'), findsOneWidget);
    // Absent, not greyed out: a visible lock is an invitation to ask your
    // partner why it is locked, which is the pressure this gate prevents.
    expect(find.text('Close'), findsNothing);
  });
}
