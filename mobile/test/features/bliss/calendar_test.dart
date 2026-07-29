import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:mobile/features/bliss/bliss_api_service.dart';
import 'package:mobile/features/bliss/bliss_models.dart';
import 'package:mobile/features/bliss/calendar_viewmodel.dart';
import 'package:mobile/features/bliss/views/calendar_screen.dart';

/// The calendar, and the invitation flow on top of it.
///
/// The property under test almost everywhere is the same one: tagging someone
/// asks them, and until they answer it is a question rather than a commitment.
class _StubApi implements BlissApiService {
  Map<DateTime, List<BlissItem>> days = {};
  ({String id, bool accept})? lastResponse;
  DateTime? lastFrom;
  DateTime? lastTo;

  @override
  Future<Map<DateTime, List<BlissItem>>> calendar({
    required DateTime from,
    required DateTime to,
  }) async {
    lastFrom = from;
    lastTo = to;
    return days;
  }

  @override
  Future<BlissItem> respond(String itemId, {required bool accept}) async {
    lastResponse = (id: itemId, accept: accept);
    final existing = days.values
        .expand((i) => i)
        .firstWhere((i) => i.id == itemId);
    return BlissItem(
      id: existing.id,
      kind: existing.kind,
      title: existing.title,
      dueAt: existing.dueAt,
      partnerInvite: accept ? PartnerInvite.accepted : PartnerInvite.declined,
      createdByMe: false,
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  final day = DateTime(2026, 8, 14);

  BlissItem item({
    String id = 'i1',
    String title = 'dinner out',
    PartnerInvite invite = PartnerInvite.none,
    bool createdByMe = false,
    bool awaiting = false,
  }) {
    return BlissItem(
      id: id,
      kind: 'event',
      title: title,
      dueAt: DateTime(2026, 8, 14, 19, 30),
      partnerInvite: invite,
      createdByMe: createdByMe,
      awaitingMyAnswer: awaiting,
    );
  }

  group('calendar viewmodel', () {
    test('groups what it loads by day', () async {
      final api = _StubApi()..days = {
        day: [item()],
      };
      final vm = CalendarViewModel(api: api);
      await vm.load(month: day);

      expect(vm.itemsOn(day), hasLength(1));
      expect(vm.hasAnythingOn(day), isTrue);
      expect(vm.hasAnythingOn(day.add(const Duration(days: 1))), isFalse);
    });

    test('asks for a padded window, not just the month', () async {
      // A month grid shows trailing and leading days of the neighbouring
      // months. Without padding those cells render empty when they are not.
      final api = _StubApi();
      final vm = CalendarViewModel(api: api);
      await vm.load(month: DateTime(2026, 8));

      expect(api.lastFrom!.isBefore(DateTime(2026, 8, 1)), isTrue);
      expect(api.lastTo!.isAfter(DateTime(2026, 8, 31)), isTrue);
    });

    test('surfaces invitations waiting on me, whatever day they fall on', () async {
      // They sit above the grid: an unanswered question must not depend on
      // someone happening to tap the right day.
      final api = _StubApi()..days = {
        day: [item(awaiting: true, invite: PartnerInvite.pending)],
        DateTime(2026, 8, 20): [item(id: 'i2')],
      };
      final vm = CalendarViewModel(api: api);
      await vm.load(month: day);

      expect(vm.pendingInvites, hasLength(1));
      expect(vm.pendingInvites.single.id, 'i1');
    });

    test('flags the days that are waiting on my answer', () async {
      final api = _StubApi()..days = {
        day: [item(awaiting: true, invite: PartnerInvite.pending)],
        DateTime(2026, 8, 20): [item(id: 'i2')],
      };
      final vm = CalendarViewModel(api: api);
      await vm.load(month: day);

      expect(vm.needsMyAnswerOn(day), isTrue);
      expect(vm.needsMyAnswerOn(DateTime(2026, 8, 20)), isFalse);
    });

    test('answering updates the item in place', () async {
      final api = _StubApi()..days = {
        day: [item(awaiting: true, invite: PartnerInvite.pending)],
      };
      final vm = CalendarViewModel(api: api);
      await vm.load(month: day);
      await vm.respond(vm.itemsOn(day).single, accept: true);

      expect(api.lastResponse, (id: 'i1', accept: true));
      expect(vm.itemsOn(day).single.partnerInvite, PartnerInvite.accepted);
      expect(vm.pendingInvites, isEmpty);
    });

    test('a failed answer leaves the invitation standing', () async {
      // Better an invite that is still open than one the UI has quietly
      // resolved on the strength of a request that never landed.
      final api = _StubApi()..days = {
        day: [item(awaiting: true, invite: PartnerInvite.pending)],
      };
      final vm = CalendarViewModel(api: api);
      await vm.load(month: day);
      await vm.respond(item(id: 'nope', awaiting: true), accept: true);

      expect(vm.itemsOn(day).single.partnerInvite, PartnerInvite.pending);
      expect(vm.error, isNotNull);
    });
  });

  group('invite status labels', () {
    test('only the person who asked sees a status line', () {
      final mine = item(invite: PartnerInvite.pending, createdByMe: true);
      final theirs = item(invite: PartnerInvite.pending);
      expect(mine.inviteStatusLabel, 'Waiting for them');
      // The person being asked gets buttons, not a label about themselves.
      expect(theirs.inviteStatusLabel, isNull);
    });

    test('an untagged item has no status at all', () {
      expect(item(createdByMe: true).inviteStatusLabel, isNull);
    });

    test('accepted and declined read differently', () {
      expect(
        item(invite: PartnerInvite.accepted, createdByMe: true).inviteStatusLabel,
        "They're in",
      );
      expect(
        item(invite: PartnerInvite.declined, createdByMe: true).inviteStatusLabel,
        'They said no',
      );
    });
  });

  group('calendar screen', () {
    Future<CalendarViewModel> pump(WidgetTester tester, _StubApi api) async {
      final vm = CalendarViewModel(api: api);
      await tester.pumpWidget(
        ChangeNotifierProvider<CalendarViewModel>.value(
          value: vm,
          child: const MaterialApp(home: CalendarScreen()),
        ),
      );
      await tester.pump();
      await tester.pump();
      return vm;
    }

    testWidgets('an invitation offers both answers', (tester) async {
      final api = _StubApi()..days = {
        CalendarViewModel.dayOf(DateTime.now()): [
          item(awaiting: true, invite: PartnerInvite.pending),
        ],
      };
      await pump(tester, api);

      expect(find.text("I'm in"), findsWidgets);
      // Not "Decline" — a partner asking is not a meeting request, and saying
      // no to a Tuesday is not saying no to them.
      expect(find.text('Not this time'), findsWidgets);
    });

    testWidgets('tapping accept answers it', (tester) async {
      final api = _StubApi()..days = {
        CalendarViewModel.dayOf(DateTime.now()): [
          item(awaiting: true, invite: PartnerInvite.pending),
        ],
      };
      await pump(tester, api);
      await tester.tap(find.byKey(const Key('invite_accept_i1')).first);
      await tester.pump();

      expect(api.lastResponse?.accept, isTrue);
    });

    testWidgets('an empty day says so rather than showing nothing', (
      tester,
    ) async {
      await pump(tester, _StubApi());
      // The agenda sits under the month grid, and ListView builds lazily, so
      // it has to be scrolled into existence before it can be found.
      await tester.dragUntilVisible(
        find.text('Nothing on this day.'),
        find.byType(ListView),
        const Offset(0, -80),
      );
      expect(find.text('Nothing on this day.'), findsOneWidget);
    });

    testWidgets('the month can be stepped', (tester) async {
      final api = _StubApi();
      final vm = await pump(tester, api);
      final before = vm.month;
      await tester.tap(find.byKey(const Key('calendar_next_month')));
      await tester.pump();

      expect(vm.month.month, before.month == 12 ? 1 : before.month + 1);
    });
  });
}
