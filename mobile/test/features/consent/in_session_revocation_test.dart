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
      sessionTranscriptRetention: '30_days', // Revocable state
    );

    registerFallbackValue(mockConsent);

    when(() => mockApiService.fetchConsent(any())).thenAnswer((_) async => mockConsent);
    when(() => mockApiService.updateConsent(any(), any())).thenAnswer((invocation) async {
      final fields = invocation.positionalArguments[1] as Map<String, dynamic>;
      return mockConsent.copyWith(
        sessionTranscriptRetention: fields['session_transcript_retention'] as String?,
      );
    });
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

  testWidgets('Tapping lock icon badge opens inline panel', (WidgetTester tester) async {
    await setupViewport(tester);
    await tester.pumpWidget(createWidgetUnderTest());
    await tester.pump();
    await tester.pumpAndSettle(const Duration(seconds: 1));

    // Must start session first to see the badge
    await tester.tap(find.byKey(const Key('start_session_button'), skipOffstage: false));
    await tester.pumpAndSettle();

    // Verify badge exists
    expect(find.byKey(const Key('consent_badge')), findsOneWidget);
    
    // Tap badge
    await tester.tap(find.byKey(const Key('consent_badge')));
    await tester.pumpAndSettle();

    // Verify inline panel is open
    expect(find.text('Privacy settings'), findsOneWidget);
  });

  testWidgets('Single-tap revocation triggers updateConsent on API immediately', (WidgetTester tester) async {
    await setupViewport(tester);
    await tester.pumpWidget(createWidgetUnderTest());
    await tester.pump();
    await tester.pumpAndSettle(const Duration(seconds: 1));

    // Must start session first
    await tester.tap(find.byKey(const Key('start_session_button'), skipOffstage: false));
    await tester.pumpAndSettle();

    // Open panel
    await tester.tap(find.byKey(const Key('consent_badge')));
    await tester.pumpAndSettle();

    // Find "Revoke" button for Session history
    final revokeButton = find.byKey(const Key('revoke_session_history'));
    expect(revokeButton, findsOneWidget);

    // Tap Revoke
    await tester.tap(revokeButton);
    await tester.pumpAndSettle();

    // Verify API called with most restrictive default
    verify(() => mockApiService.updateConsent(userId, {'session_transcript_retention': 'per_session'})).called(1);
  });
}
