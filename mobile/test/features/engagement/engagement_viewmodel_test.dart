import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/engagement/engagement_api_service.dart';
import 'package:mobile/features/relationship/connection_score.dart';
import 'package:mobile/features/relationship/relationship_insight.dart';
import 'package:mobile/features/engagement/engagement_models.dart';
import 'package:mobile/features/engagement/engagement_viewmodel.dart';
import 'package:mocktail/mocktail.dart';

class MockEngagementApi extends Mock implements EngagementApiService {}

void main() {
  late MockEngagementApi api;
  late EngagementViewModel vm;

  setUp(() {
    api = MockEngagementApi();
    vm = EngagementViewModel(api: api);
  });

  void stubRitual({
    DailyQuestionState? question,
    MicroActionState? action,
    EngagementSummary? summary,
  }) {
    when(() => api.fetchSummary())
        .thenAnswer((_) async => summary ?? const EngagementSummary());
    when(() => api.fetchDailyQuestion())
        .thenAnswer((_) async => question ?? const DailyQuestionState());
    when(() => api.fetchMicroAction())
        .thenAnswer((_) async => action ?? const MicroActionState());
    when(() => api.fetchConnectionScore())
        .thenAnswer((_) async => ConnectionScore.unknown);
    when(() => api.fetchInsights())
        .thenAnswer((_) async => const <RelationshipInsight>[]);
  }

  test('loadRitual populates question, action and summary', () async {
    stubRitual(
      question: const DailyQuestionState(promptText: 'How was today?'),
      summary: const EngagementSummary(currentStreak: 3, pointsBalance: 40),
    );

    await vm.loadRitual();

    expect(vm.question.promptText, 'How was today?');
    expect(vm.summary.currentStreak, 3);
    expect(vm.summary.pointsBalance, 40);
    expect(vm.isLoading, isFalse);
    expect(vm.error, isNull);
  });

  test('loadRitual surfaces an error without throwing', () async {
    when(() => api.fetchSummary()).thenThrow(Exception('boom'));
    when(() => api.fetchDailyQuestion())
        .thenAnswer((_) async => const DailyQuestionState());
    when(() => api.fetchMicroAction())
        .thenAnswer((_) async => const MicroActionState());
    when(() => api.fetchConnectionScore())
        .thenAnswer((_) async => ConnectionScore.unknown);
    when(() => api.fetchInsights())
        .thenAnswer((_) async => const <RelationshipInsight>[]);

    await vm.loadRitual();

    expect(vm.error, isNotNull);
    expect(vm.isLoading, isFalse);
  });

  test('answerQuestion refreshes state and returns true on success', () async {
    when(() => api.answerDailyQuestion(any()))
        .thenAnswer((_) async => const ActionReward(pointsAwarded: 10, revealed: true));
    when(() => api.fetchDailyQuestion()).thenAnswer(
        (_) async => const DailyQuestionState(promptText: 'Q', iAnswered: true));
    when(() => api.fetchSummary())
        .thenAnswer((_) async => const EngagementSummary(currentStreak: 1));

    final ok = await vm.answerQuestion('my answer');

    expect(ok, isTrue);
    expect(vm.question.iAnswered, isTrue);
    verify(() => api.answerDailyQuestion('my answer')).called(1);
  });

  test('checkIn returns false and sets error on failure', () async {
    when(() => api.submitCheckIn(
          connectionScore: any(named: 'connectionScore'),
          mood: any(named: 'mood'),
          note: any(named: 'note'),
        )).thenThrow(Exception('already checked in'));

    final ok = await vm.checkIn(score: 4);

    expect(ok, isFalse);
    expect(vm.error, contains('already checked in'));
  });

  test('logGoalProgress updates the matching goal in place', () async {
    when(() => api.fetchGoals()).thenAnswer((_) async => const [
          SharedGoal(id: 'g1', title: 'Run', currentValue: 10),
          SharedGoal(id: 'g2', title: 'Save', currentValue: 0),
        ]);
    await vm.loadGoals();

    when(() => api.logGoalProgress(
          goalId: 'g1',
          value: any(named: 'value'),
          note: any(named: 'note'),
        )).thenAnswer((_) async => const SharedGoal(id: 'g1', title: 'Run', currentValue: 15));
    when(() => api.fetchSummary()).thenAnswer((_) async => const EngagementSummary());

    final ok = await vm.logGoalProgress(goalId: 'g1', value: 5);

    expect(ok, isTrue);
    expect(vm.goals.firstWhere((g) => g.id == 'g1').currentValue, 15);
    expect(vm.goals.firstWhere((g) => g.id == 'g2').currentValue, 0);
  });

  test('loadRitual carries insights through, and empty is the normal case',
      () async {
    stubRitual();
    await vm.loadRitual();
    expect(vm.insights, isEmpty);

    when(() => api.fetchInsights()).thenAnswer((_) async => const [
          RelationshipInsight(
            id: 'i1',
            kind: InsightKind.perceptionGap,
            theme: 'how connected these last few weeks have felt',
          ),
        ]);
    await vm.loadRitual();

    expect(vm.insights, hasLength(1));
    expect(vm.insights.single.kind, InsightKind.perceptionGap);
  });
}
