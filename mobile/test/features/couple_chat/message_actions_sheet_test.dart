/// The long-press menu.
///
/// This is the menu containing "Delete", so it is the last place in the thread
/// that should go untested. It lives in its own widget precisely so it can be
/// driven here rather than through a long press the harness cannot land.
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/features/couple_chat/models/couple_message.dart';
import 'package:mobile/features/couple_chat/views/message_actions_sheet.dart';

CoupleMessage message({String id = 'm1', String sender = 'me'}) => CoupleMessage(
  id: id,
  senderId: sender,
  kind: 'text',
  body: 'hello',
  sticker: '',
  replyTo: null,
  reactions: const [],
  clientId: id,
  isDeleted: false,
  createdAt: DateTime(2026, 7, 30),
);

void main() {
  late List<String> reacted;
  late int replies;
  late int deletes;

  setUp(() {
    reacted = [];
    replies = 0;
    deletes = 0;
  });

  Future<void> openSheet(WidgetTester tester, {required bool mine}) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => ElevatedButton(
              onPressed: () => MessageActionsSheet.show(
                context,
                message: message(sender: mine ? 'me' : 'them'),
                mine: mine,
                onReact: reacted.add,
                onReply: () => replies++,
                onDelete: () => deletes++,
              ),
              child: const Text('open'),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();
  }

  testWidgets('it offers every couple reaction', (tester) async {
    await openSheet(tester, mine: true);

    for (final emoji in kCoupleReactions) {
      expect(find.byKey(Key('reaction_$emoji')), findsOneWidget);
    }
  });

  testWidgets('the reactions are the affectionate set, not thumbs-up', (
    tester,
  ) async {
    await openSheet(tester, mine: true);

    // This is a thread between partners, not a team channel.
    expect(find.byKey(const Key('reaction_❤️')), findsOneWidget);
    expect(find.byKey(const Key('reaction_👍')), findsNothing);
  });

  testWidgets('picking an emoji reacts and closes', (tester) async {
    await openSheet(tester, mine: true);

    await tester.tap(find.byKey(const Key('reaction_😍')));
    await tester.pumpAndSettle();

    expect(reacted, ['😍']);
    expect(find.byType(MessageActionsSheet), findsNothing);
  });

  testWidgets('reply closes the sheet before the composer is asked for', (
    tester,
  ) async {
    await openSheet(tester, mine: true);

    await tester.tap(find.byKey(const Key('action_reply')));
    await tester.pumpAndSettle();

    // Otherwise the quote lands behind a sheet that is still closing.
    expect(replies, 1);
    expect(find.byType(MessageActionsSheet), findsNothing);
  });

  testWidgets('your own message can be deleted', (tester) async {
    await openSheet(tester, mine: true);

    expect(find.byKey(const Key('action_delete')), findsOneWidget);
    await tester.tap(find.byKey(const Key('action_delete')));
    await tester.pumpAndSettle();

    expect(deletes, 1);
  });

  testWidgets('their message offers no delete at all', (tester) async {
    await openSheet(tester, mine: false);

    // Not disabled — absent. A greyed-out Delete on someone else's message
    // reads as "you could, if only", which is the wrong idea to plant.
    expect(find.byKey(const Key('action_delete')), findsNothing);
    expect(find.byKey(const Key('action_reply')), findsOneWidget);
  });

  testWidgets('dismissing without choosing does nothing', (tester) async {
    await openSheet(tester, mine: true);

    Navigator.of(tester.element(find.byType(MessageActionsSheet))).pop();
    await tester.pumpAndSettle();

    expect(reacted, isEmpty);
    expect(replies, 0);
    expect(deletes, 0);
  });
}
