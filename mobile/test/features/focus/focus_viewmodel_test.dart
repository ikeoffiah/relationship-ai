import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/focus/focus_api_service.dart';
import 'package:mobile/features/focus/focus_models.dart';
import 'package:mobile/features/focus/focus_viewmodel.dart';
import 'package:mocktail/mocktail.dart';

class MockFocusApi extends Mock implements FocusApiService {}

void main() {
  late MockFocusApi api;
  late FocusViewModel vm;

  setUp(() {
    api = MockFocusApi();
    // Long poll interval so the timer never fires during a test.
    vm = FocusViewModel(api: api, pollInterval: const Duration(hours: 1));
  });

  tearDown(() => vm.dispose());

  group('FocusSession model', () {
    test('liveRemaining computes from endsAt', () {
      final now = DateTime(2026, 7, 26, 12, 0, 0);
      final s = FocusSession(id: '1', status: 'active', endsAt: now.add(const Duration(minutes: 5)));
      expect(s.liveRemaining(now), 300);
      // Past end clamps to 0.
      expect(s.liveRemaining(now.add(const Duration(minutes: 10))), 0);
    });

    test('status helpers', () {
      expect(const FocusSession(id: '1', status: 'proposed').isProposed, isTrue);
      expect(const FocusSession(id: '1', status: 'active').isActive, isTrue);
    });
  });

  test('load stores the current session', () async {
    when(() => api.current())
        .thenAnswer((_) async => const FocusSession(id: '1', status: 'proposed', iInitiated: true));
    await vm.load();
    expect(vm.session?.status, 'proposed');
    expect(vm.isLoading, isFalse);
  });

  test('load handles no session', () async {
    when(() => api.current()).thenAnswer((_) async => null);
    await vm.load();
    expect(vm.session, isNull);
  });

  test('propose stores the proposed session', () async {
    when(() => api.propose(20))
        .thenAnswer((_) async => const FocusSession(id: '9', status: 'proposed', iInitiated: true));
    final ok = await vm.propose(20);
    expect(ok, isTrue);
    expect(vm.session?.iInitiated, isTrue);
  });

  test('accept activates', () async {
    when(() => api.accept())
        .thenAnswer((_) async => const FocusSession(id: '9', status: 'active', remainingSeconds: 1200));
    final ok = await vm.accept();
    expect(ok, isTrue);
    expect(vm.session?.isActive, isTrue);
  });

  test('end clears the session', () async {
    when(() => api.end()).thenAnswer((_) async => null);
    final ok = await vm.end();
    expect(ok, isTrue);
    expect(vm.session, isNull);
  });

  test('propose surfaces an error and returns false', () async {
    when(() => api.propose(any())).thenThrow(Exception('invite your partner first'));
    final ok = await vm.propose(20);
    expect(ok, isFalse);
    expect(vm.error, contains('invite your partner first'));
  });
}
