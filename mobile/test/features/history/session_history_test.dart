import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:mobile/features/history/viewmodels/session_history_viewmodel.dart';
import 'package:mobile/features/history/models/session_history_model.dart';
import 'package:mobile/features/history/session_history_screen.dart';

// ---------------------------------------------------------------------------
// A minimal fake ViewModel that never calls the real API.
// ---------------------------------------------------------------------------
class _FakeSessionHistoryViewModel extends SessionHistoryViewModel {
  final List<SessionHistoryItem> _fakeItems;
  final bool startEmpty;

  _FakeSessionHistoryViewModel({List<SessionHistoryItem>? items})
      : _fakeItems = items ?? [],
        startEmpty = (items == null || items.isEmpty),
        super();

  @override
  Future<void> loadSessions() async {
    // Populate synchronously so pumpAndSettle resolves immediately.
    for (final item in _fakeItems) {
      sessions; // warm getter
    }
    // Use the private backing field via the notifier.
    notifyListeners();
  }

  @override
  List<SessionHistoryItem> get sessions => _fakeItems;

  @override
  bool get isLoading => false;

  @override
  bool get isEmpty => _fakeItems.isEmpty;

  @override
  String get filter => 'all';
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
SessionHistoryItem _makeItem(SessionType type, {String id = 'id-1'}) {
  return SessionHistoryItem(
    id: id,
    type: type,
    dateTime: DateTime(2026, 4, 3, 15, 45),
    turnCount: 12,
    summaryPreview: 'We talked about something important',
  );
}

Widget _buildTestWidget(_FakeSessionHistoryViewModel vm) {
  return MaterialApp(
    routes: {
      '/safety': (_) => const Scaffold(body: Text('Safety')),
    },
    home: ChangeNotifierProvider<SessionHistoryViewModel>.value(
      value: vm,
      child: const SessionHistoryScreen(),
    ),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
void main() {
  group('SessionHistoryScreen', () {
    testWidgets('shows empty state when there are no sessions', (tester) async {
      final vm = _FakeSessionHistoryViewModel(items: []);
      await tester.pumpWidget(_buildTestWidget(vm));
      await tester.pump();

      expect(find.text('No sessions yet'), findsOneWidget);
      expect(find.text('Start your first session from the Home tab.'),
          findsOneWidget);
    });

    testWidgets('renders session cards when sessions exist', (tester) async {
      final vm = _FakeSessionHistoryViewModel(items: [
        _makeItem(SessionType.individual, id: 'id-1'),
        _makeItem(SessionType.joint, id: 'id-2'),
      ]);
      await tester.pumpWidget(_buildTestWidget(vm));
      await tester.pump();

      // 'Individual' appears in both the filter tab and the session card.
      expect(find.text('Individual'), findsAtLeastNWidgets(1));
      // 'Joint' similarly appears in both filter tab and card.
      expect(find.text('Joint'), findsAtLeastNWidgets(1));
      // 12 turns appears once per session card (2 cards total).
      expect(find.text('12 turns'), findsNWidgets(2));
    });

    testWidgets('filter tabs are all shown', (tester) async {
      final vm = _FakeSessionHistoryViewModel(items: []);
      await tester.pumpWidget(_buildTestWidget(vm));
      await tester.pump();

      expect(find.text('All'), findsOneWidget);
      expect(find.text('Individual'), findsOneWidget);
      expect(find.text('Joint'), findsOneWidget);
      expect(find.text('Relay'), findsOneWidget);
    });

    testWidgets('shows summary preview in card', (tester) async {
      final vm = _FakeSessionHistoryViewModel(items: [
        _makeItem(SessionType.individual, id: 'id-1'),
      ]);
      await tester.pumpWidget(_buildTestWidget(vm));
      await tester.pump();

      expect(
        find.textContaining('We talked about something important'),
        findsOneWidget,
      );
    });

    testWidgets('GetHelpNowButton is always visible', (tester) async {
      final vm = _FakeSessionHistoryViewModel(items: []);
      await tester.pumpWidget(_buildTestWidget(vm));
      await tester.pump();

      expect(find.text('Get Help Now'), findsOneWidget);
    });

    testWidgets('relay session shows mail-from label', (tester) async {
      final relay = SessionHistoryItem(
        id: 'relay-1',
        type: SessionType.relay,
        dateTime: DateTime.now(),
        turnCount: 5,
        summaryPreview: 'A relay reflection',
        relayFromPartner: 'Alex',
      );
      final vm = _FakeSessionHistoryViewModel(items: [relay]);
      await tester.pumpWidget(_buildTestWidget(vm));
      await tester.pump();

      expect(find.textContaining('From Alex'), findsOneWidget);
    });
  });
}
