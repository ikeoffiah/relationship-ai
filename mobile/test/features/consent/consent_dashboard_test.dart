import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/features/auth/models/user_profile.dart';
import 'package:mobile/features/consent/viewmodels/consent_viewmodel.dart';
import 'package:mobile/features/consent/models/consent_model.dart';
import 'package:mobile/features/consent/models/memory_model.dart';
import 'package:mobile/features/consent/consent_dashboard_screen.dart';
import 'package:mobile/core/api_services/consent_api_service.dart';

class MockConsentApiService extends Mock implements ConsentApiService {}
class MockAuthViewModel extends Mock implements AuthViewModel {}

void main() {
  late ConsentViewModel consentViewModel;
  late MockConsentApiService mockApiService;
  late MockAuthViewModel mockAuthViewModel;
  const userId = 'user123';

  setUp(() {
    mockApiService = MockConsentApiService();
    mockAuthViewModel = MockAuthViewModel();
    consentViewModel = ConsentViewModel(apiService: mockApiService);

    const mockUser = UserProfile(id: userId, email: 'test@example.com', name: 'Test User');
    when(() => mockAuthViewModel.user).thenReturn(mockUser);

    const mockConsent = ConsentModel(
      id: '1',
      userId: userId,
      sessionTranscriptRetention: '30_days',
      crossPartnerInsightSharing: 'anonymized',
      jointSessionParticipation: 'not_enrolled',
      therapistSummaryAccess: false,
    );

    final mockMemories = [
      MemoryModel(
        id: 'mem1',
        title: 'Communication pattern',
        whyStored: 'Identified recurring conflict loop',
        createdAt: DateTime.now(),
      ),
    ];

    registerFallbackValue(mockConsent);

    when(() => mockApiService.fetchConsent(userId)).thenAnswer((_) async => mockConsent);
    when(() => mockApiService.fetchMemories(userId)).thenAnswer((_) async => mockMemories.map((m) => m.toJson()).toList());
    when(() => mockApiService.updateConsent(any(), any())).thenAnswer((invocation) async {
      final fields = invocation.positionalArguments[1] as Map<String, dynamic>;
      return mockConsent.copyWith(
        sessionTranscriptRetention: fields['session_transcript_retention'] as String?,
        therapistSummaryAccess: fields['therapist_summary_access'] as bool?,
      );
    });
    when(() => mockApiService.deleteMemory(any(), any())).thenAnswer((_) async {});
    when(() => mockApiService.updateMemory(any(), any(), any())).thenAnswer((_) async {});
  });

  Widget createWidgetUnderTest() {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthViewModel>.value(value: mockAuthViewModel),
        ChangeNotifierProvider<ConsentViewModel>.value(value: consentViewModel),
      ],
      child: const MaterialApp(
        home: ConsentDashboardScreen(),
      ),
    );
  }

  testWidgets('Renders all 6 permission sections and mandatory banners', (WidgetTester tester) async {
    await tester.pumpWidget(createWidgetUnderTest());
    await tester.pump();
    await tester.pumpAndSettle();

    // Verify sections
    expect(find.text('Session history'), findsOneWidget);
    expect(find.text('Partner insights'), findsOneWidget);
    expect(find.text('Joint sessions'), findsOneWidget);
    expect(find.text('Therapist summaries'), findsOneWidget);
    expect(find.text('What we remember about you'), findsOneWidget);

    // Verify Mandatory AI Disclosure Banner
    expect(find.textContaining('interacting with an AI system'), findsOneWidget);

    // Verify "Get Help Now" Footer
    expect(find.textContaining('Get Help Now'), findsOneWidget);
  });

  testWidgets('Toggle Therapist Access calls API with correct parameters', (WidgetTester tester) async {
    await tester.pumpWidget(createWidgetUnderTest());
    await tester.pumpAndSettle();

    final switchFinder = find.byType(Switch);
    expect(switchFinder, findsOneWidget);

    // Toggle switch
    await tester.tap(switchFinder);
    await tester.pump();

    // Verify API called
    verify(() => mockApiService.updateConsent(userId, {'therapist_summary_access': true})).called(1);
  });

  testWidgets('Memory panel allows deletion of individual memories', (WidgetTester tester) async {
    await tester.pumpWidget(createWidgetUnderTest());
    await tester.pumpAndSettle();

    expect(find.text('Communication pattern'), findsOneWidget);
    
    // Find Delete button for the memory
    final deleteButton = find.text('Delete');
    await tester.tap(deleteButton);
    await tester.pumpAndSettle();

    // Confirm deletion in dialog
    await tester.tap(find.text('Delete').last);
    await tester.pumpAndSettle();

    // Verify API called
    verify(() => mockApiService.deleteMemory(userId, 'mem1')).called(1);
    
    // Verify UI updated (memory removed)
    expect(find.text('Communication pattern'), findsNothing);
  });

  testWidgets('Optimistic updates: UI changes immediately and reverts on failure', (WidgetTester tester) async {
    // Mock failure
    when(() => mockApiService.updateConsent(any(), any())).thenThrow(Exception('API Failure'));

    await tester.pumpWidget(createWidgetUnderTest());
    await tester.pumpAndSettle();

    // Find a radio option that is NOT selected (e.g., 'Not saved')
    final perSessionOption = find.textContaining('Not saved');
    
    // Tap it
    await tester.tap(perSessionOption);
    await tester.pump(); // Immediate UI change (optimistic)

    // Verify UI shows it as selected
    final radioGroup = tester.widget<RadioGroup<String>>(find.byType(RadioGroup<String>).first);
    expect(radioGroup.groupValue, equals('per_session'));

    await tester.pumpAndSettle(); // Wait for API "failure" to be processed

    // Verify UI reverts (should go back to '30_days')
    final radioGroupReverted = tester.widget<RadioGroup<String>>(find.byType(RadioGroup<String>).first);
    expect(radioGroupReverted.groupValue, equals('30_days'));
    
    // Verify error message shown
    expect(find.textContaining('API Failure'), findsOneWidget);
  });
}
