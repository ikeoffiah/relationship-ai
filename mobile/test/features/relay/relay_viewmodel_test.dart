import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/relay/relay_api_service.dart';
import 'package:mobile/features/relay/relay_models.dart';
import 'package:mobile/features/relay/relay_viewmodel.dart';
import 'package:mocktail/mocktail.dart';

class MockRelayApi extends Mock implements RelayApiService {}

RelayDetail relay(String id) => RelayDetail(
      relayId: id,
      fromUserId: 'a',
      toUserId: 'b',
      relationshipId: 'rel',
      originalContent: 'o',
      translatedContent: 't',
      translationQualityScore: 0.9,
      status: 'ready',
      createdAt: DateTime(2026),
      deliveredAt: null,
      recipientChoseVersion: null,
      expiresAt: DateTime(2026, 2),
    );

void main() {
  late MockRelayApi api;
  late RelayViewModel vm;

  setUp(() {
    api = MockRelayApi();
    vm = RelayViewModel(api: api);
  });

  test('loadPending populates the list', () async {
    when(() => api.fetchPending(any()))
        .thenAnswer((_) async => [relay('r1'), relay('r2')]);

    await vm.loadPending('user-b');

    expect(vm.pending, hasLength(2));
    expect(vm.isLoading, isFalse);
  });

  test('loadPending surfaces an error without throwing', () async {
    when(() => api.fetchPending(any())).thenThrow(Exception('boom'));

    await vm.loadPending('user-b');

    expect(vm.error, isNotNull);
    expect(vm.pending, isEmpty);
  });

  test('send returns the status', () async {
    when(() => api.send(
          content: any(named: 'content'),
          consent: any(named: 'consent'),
        )).thenAnswer((_) async => 'processing');

    final status = await vm.send('hi', consent: true);

    expect(status, 'processing');
  });

  test('deliver removes the relay from pending on success', () async {
    when(() => api.fetchPending(any()))
        .thenAnswer((_) async => [relay('r1'), relay('r2')]);
    when(() => api.deliver(any(), any()))
        .thenAnswer((_) async => relay('r1'));
    await vm.loadPending('user-b');

    final ok = await vm.deliver('r1', RelayVersion.original);

    expect(ok, isTrue);
    expect(vm.pending.map((r) => r.relayId), ['r2']);
  });

  test('deliver keeps the relay on failure', () async {
    when(() => api.fetchPending(any())).thenAnswer((_) async => [relay('r1')]);
    when(() => api.deliver(any(), any())).thenThrow(Exception('nope'));
    await vm.loadPending('user-b');

    final ok = await vm.deliver('r1', RelayVersion.original);

    expect(ok, isFalse);
    expect(vm.pending, hasLength(1));
    expect(vm.error, isNotNull);
  });
}
