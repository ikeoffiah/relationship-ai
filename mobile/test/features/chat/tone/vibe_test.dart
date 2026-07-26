import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/chat/tone/tone_api_service.dart';
import 'package:mobile/features/chat/tone/tone_viewmodel.dart';
import 'package:mobile/features/chat/tone/vibe_models.dart';
import 'package:mocktail/mocktail.dart';

class MockToneApi extends Mock implements ToneApiService {}

void main() {
  group('DailyVibe.fromJson', () {
    test('parses full payload', () {
      final v = DailyVibe.fromJson({
        'label': 'Playful',
        'emoji': '😄',
        'blurb': 'Teasing and light.',
        'disclaimer': 'Just for fun.',
      });
      expect(v.label, 'Playful');
      expect(v.emoji, '😄');
      expect(v.blurb, 'Teasing and light.');
    });

    test('defaults to Quiet when fields missing', () {
      final v = DailyVibe.fromJson({});
      expect(v.label, 'Quiet');
      expect(v.emoji, '🌙');
    });
  });

  group('ToneViewModel.readVibe', () {
    late MockToneApi api;
    late ToneViewModel vm;

    setUp(() {
      api = MockToneApi();
      vm = ToneViewModel(api: api);
    });

    test('returns the vibe from the api', () async {
      when(() => api.vibe(any()))
          .thenAnswer((_) async => const DailyVibe(label: 'Intimate', emoji: '🔥'));
      final v = await vm.readVibe([
        {'role': 'me', 'content': 'love you'},
      ]);
      expect(v?.label, 'Intimate');
    });

    test('returns null and records error on failure', () async {
      when(() => api.vibe(any())).thenThrow(Exception('down'));
      final v = await vm.readVibe(const []);
      expect(v, isNull);
      expect(vm.error, contains('down'));
    });
  });
}
