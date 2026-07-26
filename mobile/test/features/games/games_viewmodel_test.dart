import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/games/games_api_service.dart';
import 'package:mobile/features/games/games_models.dart';
import 'package:mobile/features/games/games_viewmodel.dart';
import 'package:mocktail/mocktail.dart';

class MockGamesApi extends Mock implements GamesApiService {}

void main() {
  late MockGamesApi api;
  late GamesViewModel vm;

  setUp(() {
    api = MockGamesApi();
    vm = GamesViewModel(api: api);
  });

  test('loadGames populates the list', () async {
    when(() => api.fetchGames()).thenAnswer((_) async => const [
          GameSummary(key: 'kyp-1', title: 'Know Me', questionCount: 5),
        ]);
    await vm.loadGames();
    expect(vm.games, hasLength(1));
    expect(vm.games.first.title, 'Know Me');
    expect(vm.isLoading, isFalse);
    expect(vm.error, isNull);
  });

  test('loadGames surfaces an error without throwing', () async {
    when(() => api.fetchGames()).thenThrow(Exception('boom'));
    await vm.loadGames();
    expect(vm.error, contains('boom'));
    expect(vm.games, isEmpty);
  });

  test('loadGame stores the detail', () async {
    when(() => api.fetchGame('kyp-1')).thenAnswer(
      (_) async => const GameDetail(key: 'kyp-1', title: 'Know Me', hasPartner: true),
    );
    await vm.loadGame('kyp-1');
    expect(vm.detail?.key, 'kyp-1');
  });

  test('submitAnswers posts each answer then refreshes detail', () async {
    when(() => api.submitAnswer(
          key: any(named: 'key'),
          questionId: any(named: 'questionId'),
          selfAnswer: any(named: 'selfAnswer'),
          guessAnswer: any(named: 'guessAnswer'),
        )).thenAnswer((_) async => {'progress': {}, 'just_completed': true});
    when(() => api.fetchGame('kyp-1')).thenAnswer(
      (_) async => GameDetail(
        key: 'kyp-1',
        title: 'Know Me',
        hasPartner: true,
        reveal: const GameReveal(myScore: 2, partnerScore: 3, outOf: 3),
      ),
    );

    final result = await vm.submitAnswers('kyp-1', {
      'q1': (self: 0, guess: 1),
      'q2': (self: 2, guess: 2),
    });

    expect(result?.reveal?.myScore, 2);
    verify(() => api.submitAnswer(
          key: 'kyp-1',
          questionId: 'q1',
          selfAnswer: 0,
          guessAnswer: 1,
        )).called(1);
    verify(() => api.submitAnswer(
          key: 'kyp-1',
          questionId: 'q2',
          selfAnswer: 2,
          guessAnswer: 2,
        )).called(1);
  });

  test('submitAnswers returns null and sets error on failure', () async {
    when(() => api.submitAnswer(
          key: any(named: 'key'),
          questionId: any(named: 'questionId'),
          selfAnswer: any(named: 'selfAnswer'),
          guessAnswer: any(named: 'guessAnswer'),
        )).thenThrow(Exception('needs a partner'));
    final result = await vm.submitAnswers('kyp-1', {'q1': (self: 0, guess: 1)});
    expect(result, isNull);
    expect(vm.error, contains('needs a partner'));
  });

  test('toggleSpicy sets consent and refreshes games', () async {
    when(() => api.setSpicyConsent(true)).thenAnswer(
      (_) async => const SpicyConsent(you: true, partner: true, bothAgeVerified: true, unlocked: true),
    );
    when(() => api.fetchGames()).thenAnswer((_) async => const []);
    final ok = await vm.toggleSpicy(true);
    expect(ok, isTrue);
    expect(vm.spicyConsent?.unlocked, isTrue);
    verify(() => api.fetchGames()).called(1);
  });

  test('toggleSpicy returns false and sets error on failure', () async {
    when(() => api.setSpicyConsent(any())).thenThrow(Exception('verify your age'));
    final ok = await vm.toggleSpicy(true);
    expect(ok, isFalse);
    expect(vm.error, contains('verify your age'));
  });

  group('This or That (agreement mode)', () {
    test('GameReveal parses agreement mode + matched flags', () {
      final reveal = GameReveal.fromJson({
        'mode': 'agreement',
        'agree_count': 2,
        'out_of': 3,
        'questions': [
          {'question_id': 'q1', 'prompt': 'Beach or mountains?', 'options': ['Beach', 'Mountains'],
           'my_answer': 0, 'partner_answer': 0, 'matched': true},
          {'question_id': 'q2', 'prompt': 'Sweet or savoury?', 'options': ['Sweet', 'Savoury'],
           'my_answer': 0, 'partner_answer': 1, 'matched': false},
        ],
      });
      expect(reveal.isAgreement, isTrue);
      expect(reveal.agreeCount, 2);
      expect(reveal.questions.first.matched, isTrue);
      expect(reveal.questions[1].matched, isFalse);
    });

    test('default mode is guess (backward compatible)', () {
      final reveal = GameReveal.fromJson({'my_score': 1, 'partner_score': 2, 'out_of': 3});
      expect(reveal.isAgreement, isFalse);
      expect(reveal.mode, 'guess');
    });

    test('submitAnswers passes a null guess through for agreement games', () async {
      when(() => api.submitAnswer(
            key: any(named: 'key'),
            questionId: any(named: 'questionId'),
            selfAnswer: any(named: 'selfAnswer'),
            guessAnswer: any(named: 'guessAnswer'),
          )).thenAnswer((_) async => {'progress': {}, 'just_completed': false});
      when(() => api.fetchGame('tot-us')).thenAnswer(
        (_) async => const GameDetail(key: 'tot-us', title: 'This or That', gameType: 'this_or_that'),
      );
      await vm.submitAnswers('tot-us', {'q1': (self: 0, guess: null)});
      verify(() => api.submitAnswer(
            key: 'tot-us',
            questionId: 'q1',
            selfAnswer: 0,
            guessAnswer: null,
          )).called(1);
    });
  });
}
