import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/chat/tone/tone_api_service.dart';
import 'package:mobile/features/chat/tone/tone_models.dart';
import 'package:mobile/features/chat/tone/tone_viewmodel.dart';
import 'package:mocktail/mocktail.dart';

class MockToneApi extends Mock implements ToneApiService {}

void main() {
  late MockToneApi api;
  late ToneViewModel vm;

  setUp(() {
    api = MockToneApi();
    vm = ToneViewModel(api: api);
  });

  group('refreshSuggestions', () {
    final msgs = [
      {'role': 'partner', 'content': 'rough day'},
    ];

    test('populates suggestions from the api', () async {
      when(() => api.suggest(any())).thenAnswer((_) async => ['Tell me more', "I'm here"]);
      await vm.refreshSuggestions(msgs);
      expect(vm.suggestions, ['Tell me more', "I'm here"]);
      expect(vm.loadingSuggestions, isFalse);
    });

    test('empty message list clears without calling the api', () async {
      await vm.refreshSuggestions([]);
      expect(vm.suggestions, isEmpty);
      verifyNever(() => api.suggest(any()));
    });

    test('failure clears suggestions silently (never blocks chat)', () async {
      when(() => api.suggest(any())).thenThrow(Exception('offline'));
      await vm.refreshSuggestions(msgs);
      expect(vm.suggestions, isEmpty);
      expect(vm.loadingSuggestions, isFalse);
    });

    test('clearSuggestions empties the list', () async {
      when(() => api.suggest(any())).thenAnswer((_) async => ['a']);
      await vm.refreshSuggestions(msgs);
      vm.clearSuggestions();
      expect(vm.suggestions, isEmpty);
    });
  });

  group('coach', () {
    test('returns the coach result', () async {
      when(() => api.coach('you never listen', partnerMood: any(named: 'partnerMood')))
          .thenAnswer((_) async => const CoachResult(
                read: 'This may sting.',
                tone: 'frustrated',
                rewrites: ['I feel unheard when...'],
              ));
      final r = await vm.coach('you never listen');
      expect(r, isNotNull);
      expect(r!.rewrites, isNotEmpty);
      expect(r.declined, isFalse);
    });

    test('surfaces a declined (safety) result as-is', () async {
      when(() => api.coach(any(), partnerMood: any(named: 'partnerMood')))
          .thenAnswer((_) async => const CoachResult(
                safety: CoachSafety(declined: true, reason: 'harm_signals', message: 'see Support'),
              ));
      final r = await vm.coach("you're not allowed to leave");
      expect(r!.declined, isTrue);
      expect(r.safety!.reason, 'harm_signals');
    });

    test('returns null and records error on failure', () async {
      when(() => api.coach(any(), partnerMood: any(named: 'partnerMood')))
          .thenThrow(Exception('boom'));
      final r = await vm.coach('hi');
      expect(r, isNull);
      expect(vm.error, contains('boom'));
    });
  });

  group('readMood', () {
    test('returns a mood read', () async {
      when(() => api.analyze('ugh fine'))
          .thenAnswer((_) async => const MoodRead(mood: 'frustrated', intensity: 'high'));
      final m = await vm.readMood('ugh fine');
      expect(m!.mood, 'frustrated');
    });

    test('returns null on failure', () async {
      when(() => api.analyze(any())).thenThrow(Exception('x'));
      expect(await vm.readMood('hi'), isNull);
    });
  });
}
