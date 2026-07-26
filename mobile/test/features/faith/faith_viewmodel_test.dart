import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/faith/faith_api_service.dart';
import 'package:mobile/features/faith/faith_models.dart';
import 'package:mobile/features/faith/faith_viewmodel.dart';
import 'package:mocktail/mocktail.dart';

class MockFaithApi extends Mock implements FaithApiService {}

FaithToday _today({bool reflected = false}) => FaithToday(
      dateKey: '2026-07-26',
      tradition: 'christian',
      reading: const FaithReading(id: 'r1', title: 'Dwelling together', body: '…'),
      practices: const [
        FaithPracticeItem(key: 'morning-prayer', label: 'Morning prayer'),
        FaithPracticeItem(key: 'scripture', label: 'Read the passage'),
      ],
      reflected: reflected,
    );

void main() {
  late MockFaithApi api;
  late FaithViewModel vm;

  setUp(() {
    api = MockFaithApi();
    vm = FaithViewModel(api: api);
  });

  test('loadToday populates today', () async {
    when(() => api.fetchToday()).thenAnswer((_) async => _today());
    await vm.loadToday();
    expect(vm.today?.reading?.title, 'Dwelling together');
    expect(vm.today?.practices, hasLength(2));
    expect(vm.isLoading, isFalse);
    expect(vm.error, isNull);
  });

  test('loadToday surfaces an error without throwing', () async {
    when(() => api.fetchToday()).thenThrow(Exception('boom'));
    await vm.loadToday();
    expect(vm.error, contains('boom'));
    expect(vm.today, isNull);
  });

  test('completePractice optimistically ticks and adds points', () async {
    when(() => api.fetchToday()).thenAnswer((_) async => _today());
    when(() => api.completePractice('morning-prayer')).thenAnswer((_) async => 5);
    await vm.loadToday();

    final ok = await vm.completePractice('morning-prayer');
    expect(ok, isTrue);
    expect(
      vm.today!.practices.firstWhere((p) => p.key == 'morning-prayer').completed,
      isTrue,
    );
    expect(vm.sessionPoints, 5);
  });

  test('completePractice rolls back the optimistic tick on failure', () async {
    when(() => api.fetchToday()).thenAnswer((_) async => _today());
    when(() => api.completePractice('scripture')).thenThrow(Exception('network'));
    await vm.loadToday();

    final ok = await vm.completePractice('scripture');
    expect(ok, isFalse);
    expect(
      vm.today!.practices.firstWhere((p) => p.key == 'scripture').completed,
      isFalse,
    );
    expect(vm.sessionPoints, 0);
    expect(vm.error, contains('network'));
  });

  test('reflect adds points and marks reflected', () async {
    when(() => api.fetchToday()).thenAnswer((_) async => _today());
    when(() => api.reflect('a good day')).thenAnswer((_) async => 10);
    await vm.loadToday();

    final ok = await vm.reflect('a good day');
    expect(ok, isTrue);
    expect(vm.today!.reflected, isTrue);
    expect(vm.sessionPoints, 10);
  });

  test('reflect rejects empty text without calling the API', () async {
    final ok = await vm.reflect('   ');
    expect(ok, isFalse);
    verifyNever(() => api.reflect(any()));
  });
}
