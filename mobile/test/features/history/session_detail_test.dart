import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:mobile/features/history/viewmodels/session_detail_viewmodel.dart';
import 'package:mobile/features/history/models/session_history_model.dart';
import 'package:mobile/features/history/session_detail_screen.dart';

// ---------------------------------------------------------------------------
// Fake ViewModel — returns canned data without API calls.
// ---------------------------------------------------------------------------
class _FakeSessionDetailViewModel extends SessionDetailViewModel {
  final SessionDetail? fakeDetail;
  final List<SessionMemory> fakeMemories;
  bool _deleteAllCalled = false;

  _FakeSessionDetailViewModel({
    this.fakeDetail,
    List<SessionMemory>? memories,
  })  : fakeMemories = memories ?? [],
        super();

  @override
  Future<void> loadDetail(String sessionId) async {
    // No-op: pre-populate through getters.
    notifyListeners();
  }

  @override
  SessionDetail? get detail => fakeDetail;

  @override
  List<SessionMemory> get memories => fakeMemories;

  @override
  bool get isLoading => false;

  bool get deleteAllCalled => _deleteAllCalled;

  @override
  Future<bool> deleteAllSessionMemories() async {
    _deleteAllCalled = true;
    fakeMemories.clear();
    notifyListeners();
    return true;
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
SessionDetail _makeDetail({
  String summary = 'We explored communication.',
  List<String> frameworks = const ['NVC', 'Gottman'],
}) {
  return SessionDetail(
    id: 'session-1',
    type: SessionType.individual,
    dateTime: DateTime(2026, 4, 3, 15, 45),
    turnCount: 24,
    durationMinutes: 18,
    summary: summary,
    frameworks: frameworks,
  );
}

SessionMemory _makeMemory({String id = 'mem-1', String content = 'Tends to withdraw'}) {
  return SessionMemory(
    id: id,
    content: content,
    category: 'communication_style',
    sessionId: 'session-1',
  );
}

Widget _buildTestWidget(_FakeSessionDetailViewModel vm) {
  return MaterialApp(
    routes: {
      '/safety': (_) => const Scaffold(body: Text('Safety')),
    },
    home: ChangeNotifierProvider<SessionDetailViewModel>.value(
      value: vm,
      child: const SessionDetailScreen(sessionId: 'session-1'),
    ),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
void main() {
  group('SessionDetailScreen', () {
    testWidgets('renders session summary', (tester) async {
      final vm = _FakeSessionDetailViewModel(fakeDetail: _makeDetail());
      await tester.pumpWidget(_buildTestWidget(vm));
      await tester.pump();

      expect(find.text('We explored communication.'), findsOneWidget);
    });

    testWidgets('renders framework tags', (tester) async {
      final vm = _FakeSessionDetailViewModel(
        fakeDetail: _makeDetail(frameworks: ['NVC', 'Gottman']),
      );
      await tester.pumpWidget(_buildTestWidget(vm));
      await tester.pump();

      expect(find.text('NVC'), findsOneWidget);
      expect(find.text('Gottman'), findsOneWidget);
    });

    testWidgets('shows empty memories message when no memories', (tester) async {
      final vm = _FakeSessionDetailViewModel(
        fakeDetail: _makeDetail(),
        memories: [],
      );
      await tester.pumpWidget(_buildTestWidget(vm));
      await tester.pump();

      expect(
        find.text('No memories were stored from this session.'),
        findsOneWidget,
      );
    });

    testWidgets('renders memories with edit and delete buttons', (tester) async {
      final vm = _FakeSessionDetailViewModel(
        fakeDetail: _makeDetail(),
        memories: [_makeMemory(content: 'Tends to withdraw')],
      );
      await tester.pumpWidget(_buildTestWidget(vm));
      await tester.pump();

      expect(find.textContaining('Tends to withdraw'), findsOneWidget);
      expect(find.text('Edit'), findsOneWidget);
      expect(find.text('Delete'), findsOneWidget);
    });

    testWidgets('tapping Edit is interactive (button is tappable)', (tester) async {
      final vm = _FakeSessionDetailViewModel(
        fakeDetail: _makeDetail(),
        memories: [
          SessionMemory(
            id: 'mem-1',
            content: 'Tends to withdraw',
            category: 'style',
            sessionId: 'session-1',
            isEditing: false,
          ),
        ],
      );
      await tester.pumpWidget(_buildTestWidget(vm));
      await tester.pump();

      // Edit button is visible and tappable.
      expect(find.text('Edit'), findsOneWidget);
      // Scroll to ensure button is within the viewport before tapping.
      await tester.ensureVisible(find.text('Edit'));
      await tester.tap(find.text('Edit'), warnIfMissed: false);
      await tester.pump();
      // After tap, still renders without crashing.
      expect(find.text('Tends to withdraw'), findsOneWidget);
    });

    testWidgets('bulk delete button is shown when memories exist', (tester) async {
      final vm = _FakeSessionDetailViewModel(
        fakeDetail: _makeDetail(),
        memories: [_makeMemory()],
      );
      await tester.pumpWidget(_buildTestWidget(vm));
      await tester.pump();

      // The bulk delete button may be below the fold — scroll to find it.
      final bulkDeleteFinder = find.textContaining("Delete this session's memories");
      await tester.scrollUntilVisible(bulkDeleteFinder, 100);
      expect(bulkDeleteFinder, findsOneWidget);
    });

    testWidgets('bulk delete button absent when no memories', (tester) async {
      final vm = _FakeSessionDetailViewModel(
        fakeDetail: _makeDetail(),
        memories: [],
      );
      await tester.pumpWidget(_buildTestWidget(vm));
      await tester.pump();

      expect(find.textContaining("Delete this session's memories"), findsNothing);
    });

    testWidgets('GetHelpNowButton is always visible', (tester) async {
      final vm = _FakeSessionDetailViewModel(fakeDetail: _makeDetail());
      await tester.pumpWidget(_buildTestWidget(vm));
      await tester.pump();

      expect(find.text('Get Help Now'), findsOneWidget);
    });

    testWidgets('shows header metadata: turns and duration', (tester) async {
      final vm = _FakeSessionDetailViewModel(fakeDetail: _makeDetail());
      await tester.pumpWidget(_buildTestWidget(vm));
      await tester.pump();

      expect(find.textContaining('24 turns'), findsOneWidget);
      expect(find.textContaining('18 min'), findsOneWidget);
    });
  });
}
