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
}
