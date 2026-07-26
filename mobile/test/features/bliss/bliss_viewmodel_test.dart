import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/bliss/bliss_api_service.dart';
import 'package:mobile/features/bliss/bliss_models.dart';
import 'package:mobile/features/bliss/bliss_viewmodel.dart';
import 'package:mocktail/mocktail.dart';

class MockBlissApi extends Mock implements BlissApiService {}

BlissDraft _draft() => const BlissDraft(kind: 'reminder', title: 'call the venue');

void main() {
  late MockBlissApi api;
  late BlissViewModel vm;

  setUp(() {
    api = MockBlissApi();
    vm = BlissViewModel(api: api);
    registerFallbackValue(_draft());
  });

  group('isBlissCommand', () {
    test('detects the tag case-insensitively', () {
      expect(isBlissCommand('@bliss remind me'), isTrue);
      expect(isBlissCommand('Hey @Bliss add dinner'), isTrue);
      expect(isBlissCommand('just chatting'), isFalse);
      expect(isBlissCommand('blissful morning'), isFalse); // needs the @ + word boundary
    });
  });

  test('interpret returns a draft', () async {
    when(() => api.interpret(any())).thenAnswer((_) async => _draft());
    final d = await vm.interpret('@bliss remind us to call the venue');
    expect(d?.title, 'call the venue');
  });

  test('interpret returns null when unrecognized', () async {
    when(() => api.interpret(any())).thenAnswer((_) async => null);
    expect(await vm.interpret('@bliss ???'), isNull);
  });

  test('interpret records error and returns null on failure', () async {
    when(() => api.interpret(any())).thenThrow(Exception('offline'));
    expect(await vm.interpret('@bliss x'), isNull);
    expect(vm.error, contains('offline'));
  });

  test('create prepends the new item', () async {
    when(() => api.create(any()))
        .thenAnswer((_) async => const BlissItem(id: '1', title: 'call the venue'));
    final item = await vm.create(_draft());
    expect(item?.id, '1');
    expect(vm.items.first.title, 'call the venue');
  });

  test('load populates items', () async {
    when(() => api.list()).thenAnswer((_) async => const [
          BlissItem(id: '1', title: 'a'),
          BlissItem(id: '2', title: 'b', kind: 'event'),
        ]);
    await vm.load();
    expect(vm.items, hasLength(2));
    expect(vm.isLoading, isFalse);
  });

  test('markDone removes the item from the pending list', () async {
    when(() => api.list()).thenAnswer((_) async => const [
          BlissItem(id: '1', title: 'a'),
          BlissItem(id: '2', title: 'b'),
        ]);
    when(() => api.setDone('1'))
        .thenAnswer((_) async => const BlissItem(id: '1', title: 'a', status: 'done'));
    await vm.load();
    await vm.markDone('1');
    expect(vm.items.map((i) => i.id), ['2']);
  });

  test('cancel removes the item too', () async {
    when(() => api.list()).thenAnswer((_) async => const [BlissItem(id: '9', title: 'x')]);
    when(() => api.setCancelled('9'))
        .thenAnswer((_) async => const BlissItem(id: '9', title: 'x', status: 'cancelled'));
    await vm.load();
    await vm.cancel('9');
    expect(vm.items, isEmpty);
  });
}
