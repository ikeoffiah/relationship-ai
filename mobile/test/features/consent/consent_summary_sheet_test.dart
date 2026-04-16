import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';
import 'package:mobile/features/chat/chat_screen.dart';
import 'package:mobile/features/consent/viewmodels/consent_viewmodel.dart';
import 'package:mobile/features/consent/models/consent_model.dart';
import 'package:mobile/core/api_services/consent_api_service.dart';

class MockConsentApiService extends Mock implements ConsentApiService {}

void main() {
  late ConsentViewModel consentViewModel;
  late MockConsentApiService mockApiService;
  const userId = 'user123';

  setUp(() {
    mockApiService = MockConsentApiService();
    consentViewModel = ConsentViewModel(apiService: mockApiService);
    
    const mockConsent = ConsentModel(
      id: '1',
      userId: userId,
      sessionTranscriptRetention: 'per_session',
      crossPartnerInsightSharing: 'never',
      jointSessionParticipation: 'not_enrolled',
      sharedRelationshipContext: 'not_participating',
    );

    when(() => mockApiService.fetchConsent(any())).thenAnswer((_) async => mockConsent);
  });

  Widget createWidgetUnderTest() {
    return ChangeNotifierProvider<ConsentViewModel>.value(
      value: consentViewModel,
      child: const MaterialApp(
        home: ChatScreen(userId: userId),
      ),
    );
  }

  Future<void> setupViewport(WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 1920);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() => tester.view.resetPhysicalSize());
    addTearDown(() => tester.view.resetDevicePixelRatio());
  }

  testWidgets('ConsentSummarySheet appears automatically and gates content', (WidgetTester tester) async {
    await setupViewport(tester);
    await tester.pumpWidget(createWidgetUnderTest());
    await tester.pump(); 
    await tester.pumpAndSettle(const Duration(seconds: 1));

    // Verify sheet is visible
    expect(find.text('Your current privacy settings', skipOffstage: false), findsOneWidget);
    
    // Verify session content is NOT visible yet
    expect(find.byKey(const Key('chat_body')), findsNothing);

    // Verify "Start session" button exists
    expect(find.byKey(const Key('start_session_button'), skipOffstage: false), findsOneWidget);
  });

  testWidgets('ConsentSummarySheet cannot be dismissed by drag', (WidgetTester tester) async {
    await setupViewport(tester);
    await tester.pumpWidget(createWidgetUnderTest());
    await tester.pump(); 
    await tester.pumpAndSettle(const Duration(seconds: 1));

    // Verify sheet is there
    expect(find.text('Your current privacy settings', skipOffstage: false), findsOneWidget);

    // Attempt to drag down to dismiss
    await tester.drag(find.text('Your current privacy settings', skipOffstage: false), const Offset(0, 500));
    await tester.pumpAndSettle();

    // Verify sheet is STILL there
    expect(find.text('Your current privacy settings', skipOffstage: false), findsOneWidget);
  });

  testWidgets('Tapping Start session dismisses sheet and reveals content', (WidgetTester tester) async {
    await setupViewport(tester);
    await tester.pumpWidget(createWidgetUnderTest());
    await tester.pump(); 
    await tester.pumpAndSettle(const Duration(seconds: 1));

    // Tap Start session
    await tester.tap(find.byKey(const Key('start_session_button'), skipOffstage: false));
    await tester.pumpAndSettle();

    // Verify sheet is gone
    expect(find.text('Your current privacy settings'), findsNothing);

    // Verify session content IS visible
    expect(find.byKey(const Key('chat_body')), findsOneWidget);
    expect(find.text('Session started'), findsOneWidget);
  });
}
