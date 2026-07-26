import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/two_truths/two_truths_api_service.dart';
import 'package:mobile/features/two_truths/two_truths_models.dart';
import 'package:mobile/features/two_truths/two_truths_viewmodel.dart';
import 'package:mocktail/mocktail.dart';

class MockTwoTruthsApi extends Mock implements TwoTruthsApiService {}

void main() {
  late MockTwoTruthsApi api;
  late TwoTruthsViewModel vm;

  setUp(() {
    api = MockTwoTruthsApi();
    vm = TwoTruthsViewModel(api: api);
  });

  group('phase derivation', () {
    test('author when not yet authored', () {
      const s = TwoTruthsState(hasPartner: true, authored: false);
      expect(s.phase, 'author');
    });
    test('guess when authored + partner authored + not guessed', () {
      const s = TwoTruthsState(
          hasPartner: true, authored: true, partnerAuthored: true, iGuessed: false);
      expect(s.phase, 'guess');
    });
    test('waiting when authored but partner has not', () {
      const s = TwoTruthsState(hasPartner: true, authored: true, partnerAuthored: false);
      expect(s.phase, 'waiting');
    });
    test('reveal when revealed', () {
      const s = TwoTruthsState(hasPartner: true, revealed: true);
      expect(s.phase, 'reveal');
    });
  });

  test('fromJson parses reveal + scoring', () {
    final s = TwoTruthsState.fromJson({
      'has_partner': true,
      'partner_name': 'Blake',
      'authored': true,
      'partner_authored': true,
      'i_guessed': true,
      'partner_guessed': true,
      'revealed': true,
      'my_statements': ['a', 'b', 'c'],
      'my_lie_index': 0,
      'partner_statements': ['x', 'y', 'z'],
      'reveal': {
        'partner_lie_index': 2,
        'i_caught_them': true,
        'partner_guess': 1,
        'they_caught_me': false,
        'my_lie_index': 0,
      },
    });
    expect(s.phase, 'reveal');
    expect(s.reveal!.iCaughtThem, isTrue);
    expect(s.reveal!.theyCaughtMe, isFalse);
    expect(s.reveal!.partnerLieIndex, 2);
  });

  test('load populates state', () async {
    when(() => api.fetchState())
        .thenAnswer((_) async => const TwoTruthsState(hasPartner: true));
    await vm.load();
    expect(vm.state?.hasPartner, isTrue);
    expect(vm.isLoading, isFalse);
  });

  test('author returns true and stores new state', () async {
    when(() => api.author(any(), any()))
        .thenAnswer((_) async => const TwoTruthsState(hasPartner: true, authored: true));
    final ok = await vm.author(['a', 'b', 'c'], 1);
    expect(ok, isTrue);
    expect(vm.state?.authored, isTrue);
  });

  test('guess surfaces an error and returns false on failure', () async {
    when(() => api.guess(any())).thenThrow(Exception("partner hasn't authored"));
    final ok = await vm.guess(1);
    expect(ok, isFalse);
    expect(vm.error, contains("partner hasn't authored"));
  });

  test('reset reloads state', () async {
    when(() => api.reset()).thenAnswer((_) async {});
    when(() => api.fetchState())
        .thenAnswer((_) async => const TwoTruthsState(hasPartner: true, authored: false));
    final ok = await vm.reset();
    expect(ok, isTrue);
    expect(vm.state?.phase, 'author');
  });
}
