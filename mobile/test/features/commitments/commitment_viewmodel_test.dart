import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/commitments/commitment_api_service.dart';
import 'package:mobile/features/commitments/commitment_models.dart';
import 'package:mobile/features/commitments/commitment_viewmodel.dart';
import 'package:mocktail/mocktail.dart';

class MockCommitmentApi extends Mock implements CommitmentApiService {}

void main() {
  late MockCommitmentApi api;
  late CommitmentViewModel vm;

  setUp(() {
    api = MockCommitmentApi();
    vm = CommitmentViewModel(api: api);
  });

  test('load splits items into for/with buckets', () async {
    when(() => api.list()).thenAnswer((_) async => const [
          Commitment(id: '1', kind: 'for_partner', text: 'coffee in bed'),
          Commitment(id: '2', kind: 'with_partner', text: 'weekly walk'),
          Commitment(id: '3', kind: 'for_partner', text: 'surprise note'),
        ]);
    await vm.load();
    expect(vm.forPartner.map((c) => c.id), ['1', '3']);
    expect(vm.withPartner.map((c) => c.id), ['2']);
  });

  test('load surfaces an error', () async {
    when(() => api.list()).thenThrow(Exception('offline'));
    await vm.load();
    expect(vm.error, contains('offline'));
    expect(vm.items, isEmpty);
  });

  test('add prepends the new commitment', () async {
    when(() => api.create(
          kind: any(named: 'kind'),
          text: any(named: 'text'),
          remindAt: any(named: 'remindAt'),
        )).thenAnswer((_) async => const Commitment(id: '9', kind: 'for_partner', text: 'x'));
    final ok = await vm.add(kind: 'for_partner', text: 'x');
    expect(ok, isTrue);
    expect(vm.items.first.id, '9');
  });

  test('add returns false and records error on failure', () async {
    when(() => api.create(
          kind: any(named: 'kind'),
          text: any(named: 'text'),
          remindAt: any(named: 'remindAt'),
        )).thenThrow(Exception('needs a partner'));
    final ok = await vm.add(kind: 'with_partner', text: 'y');
    expect(ok, isFalse);
    expect(vm.error, contains('needs a partner'));
  });

  test('markDone removes from the list', () async {
    when(() => api.list()).thenAnswer((_) async => const [
          Commitment(id: '1', text: 'a'),
          Commitment(id: '2', text: 'b'),
        ]);
    when(() => api.setDone('1'))
        .thenAnswer((_) async => const Commitment(id: '1', text: 'a', status: 'done'));
    await vm.load();
    await vm.markDone('1');
    expect(vm.items.map((c) => c.id), ['2']);
  });

  test('cancel removes from the list', () async {
    when(() => api.list()).thenAnswer((_) async => const [Commitment(id: '5', text: 'z')]);
    when(() => api.setCancelled('5'))
        .thenAnswer((_) async => const Commitment(id: '5', text: 'z', status: 'cancelled'));
    await vm.load();
    await vm.cancel('5');
    expect(vm.items, isEmpty);
  });
}
