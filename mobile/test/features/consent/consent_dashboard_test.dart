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
    when(() => mockAuthViewModel.isMinor).thenReturn(false);

    const mockConsent = ConsentModel(
      id: '1',
      userId: userId,
      sessionTranscriptRetention: '30_days',
      crossPartnerInsightSharing: 'anonymized',
      jointSessionParticipation: 'not_enrolled',
      sharedRelationshipContext: 'not_participating',
      therapistSummaryAccess: false,
    );

    final mockMemories = [
      MemoryModel(
        id: 'mem1',
        title: 'Communication pattern',
        whyStored: 'Identified recurring conflict loop',
        zone: MemoryZone.private,
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

  testWidgets('Renders all permission sections and memory zones', (WidgetTester tester) async {
    await tester.pumpWidget(createWidgetUnderTest());
    await tester.pump();
    await tester.pumpAndSettle();

    // Verify memory zones
    expect(find.text('Private Profile'), findsOneWidget);
    expect(find.text('Shared Context'), findsOneWidget);

    // Verify permission cards
    expect(find.text('Session transcript retention'), findsOneWidget);
    expect(find.text('Partner insight sharing'), findsOneWidget);
    expect(find.text('Shared context access'), findsOneWidget);
    expect(find.text('Therapist access'), findsOneWidget);
    expect(find.text('Model improvement data'), findsOneWidget);

    // Verify "Get Help Now" Header
    expect(find.textContaining('Get Help Now'), findsOneWidget);
  });

  testWidgets('Toggle Therapist Access calls API with correct parameters', (WidgetTester tester) async {
    await tester.pumpWidget(createWidgetUnderTest());
    await tester.pumpAndSettle();

    final switchFinder = find.descendant(
      of: find.widgetWithText(ListTile, 'Therapist access'),
      matching: find.byType(Switch),
    );
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

    // Tap the Private Profile zone card to open MemoryTransparencyPanel
    await tester.tap(find.text('Private Profile'));
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

    // Verify initial retention description
    expect(find.text('Saved for 30 days'), findsOneWidget);

    // Tap Session transcript retention card to open sheet picker
    await tester.tap(find.text('Session transcript retention'));
    await tester.pumpAndSettle();

    // Tap 'Not saved' option
    await tester.tap(find.text('Not saved'));
    await tester.pump(); // Immediate UI change (optimistic)

    // Verify UI immediately updates (optimistically showing 'Not saved')
    expect(find.text('Not saved'), findsOneWidget);

    await tester.pumpAndSettle(); // Wait for API "failure" to be processed

    // Verify UI reverts (should go back to 'Saved for 30 days')
    expect(find.text('Saved for 30 days'), findsOneWidget);
  });
}
