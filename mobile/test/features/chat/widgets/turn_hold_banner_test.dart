import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart' as provider;
import 'package:mobile/features/chat/chat_screen.dart';
import 'package:mobile/features/chat/providers/chat_provider.dart';
import 'package:mobile/features/chat/models/chat_state.dart';
import 'package:mobile/features/consent/viewmodels/consent_viewmodel.dart';
import 'package:mobile/features/consent/models/consent_model.dart';
import 'package:mobile/core/api_services/consent_api_service.dart';
import '../../../helpers/mock_services.dart';

class MockConsentApiService extends Mock implements ConsentApiService {}

void main() {
  late ConsentViewModel consentViewModel;
  late MockConsentApiService mockApiService;
  const userId = 'user123';

  setUp(() {
    setupMockSecureStorage(userId: userId);
    mockApiService = MockConsentApiService();
    consentViewModel = ConsentViewModel(apiService: mockApiService);

    const mockConsent = ConsentModel(
      id: '1',
      userId: userId,
      sessionTranscriptRetention: '30_days',
      crossPartnerInsightSharing: 'anonymized',
      jointSessionParticipation: 'not_enrolled',
      therapistSummaryAccess: false,
    );

    when(() => mockApiService.fetchConsent(any())).thenAnswer((_) async => mockConsent);
  });

  testWidgets('ChatScreen displays TurnHoldBanner when countdown is active', (WidgetTester tester) async {
    // 1. Prepare chat state with active turn hold countdown of 5 seconds
    final chatState = ChatState.initial().copyWith(
      turnHoldCountdown: 5,
    );

    // 2. Render ChatScreen inside ProviderScope (Riverpod) and provider.ChangeNotifierProvider (Provider)
    await tester.pumpWidget(
      provider.ChangeNotifierProvider<ConsentViewModel>.value(
        value: consentViewModel,
        child: ProviderScope(
          overrides: [
            chatProvider('test-session-id').overrideWithValue(chatState),
          ],
          child: const MaterialApp(
            home: ChatScreen(userId: userId, jointSessionId: 'test-session-id'),
          ),
        ),
      ),
    );

    await tester.pump();
    await tester.pumpAndSettle(const Duration(seconds: 1));

    // Consent sheet is displayed first. Tap "Start session" to reveal chat body.
    final startButton = find.text('Start session');
    expect(startButton, findsOneWidget);
    await tester.tap(startButton);
    await tester.pumpAndSettle();

    // Verify turn hold banner is visible and showing correct countdown
    expect(find.textContaining('Take a moment to reflect before responding... (5)'), findsOneWidget);
  });
}
