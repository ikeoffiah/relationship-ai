import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';

import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/features/auth/models/user_profile.dart';
import 'package:mobile/features/auth/views/login_screen.dart';
import 'package:mobile/features/home/views/main_navigation_screen.dart';
import 'package:mobile/features/relationship/relationship_viewmodel.dart';

import 'package:mobile/features/consent/viewmodels/consent_viewmodel.dart';
import 'package:mobile/features/consent/models/consent_model.dart';

class MockAuthViewModel extends Mock implements AuthViewModel {}

class MockRelationshipViewModel extends Mock implements RelationshipViewModel {}

class MockConsentViewModel extends Mock implements ConsentViewModel {}

/// Auth flow testx
void main() {
  late MockAuthViewModel mockAuthViewModel;
  late MockRelationshipViewModel mockRelationshipViewModel;
  late MockConsentViewModel mockConsentViewModel;

  setUp(() {
    mockAuthViewModel = MockAuthViewModel();
    mockRelationshipViewModel = MockRelationshipViewModel();
    mockConsentViewModel = MockConsentViewModel();

    when(() => mockAuthViewModel.isLoading).thenReturn(false);
    when(() => mockAuthViewModel.errorMessage).thenReturn(null);
    when(() => mockAuthViewModel.email).thenReturn('test@example.com');
    when(() => mockAuthViewModel.password).thenReturn('password123');
    when(() => mockAuthViewModel.setEmail(any())).thenReturn(null);
    when(() => mockAuthViewModel.setPassword(any())).thenReturn(null);
    const mockUser = UserProfile(
      id: 'test',
      email: 'test@example.com',
      name: 'Test User',
    );
    when(() => mockAuthViewModel.user).thenReturn(mockUser);
    when(() => mockAuthViewModel.isMinor).thenReturn(false);

    when(
      () => mockRelationshipViewModel.status,
    ).thenReturn(RelationshipStatus.active);
    when(() => mockRelationshipViewModel.currentRelationship).thenReturn(null);
    when(
      () => mockRelationshipViewModel.fetchSharedContext(),
    ).thenAnswer((_) async {});
    when(() => mockRelationshipViewModel.sharedContext).thenReturn(null);

    when(() => mockConsentViewModel.fetchConsent()).thenAnswer((_) async {});
    when(() => mockConsentViewModel.fetchMemories()).thenAnswer((_) async {});
    when(() => mockConsentViewModel.logSummaryShown()).thenAnswer((_) async {});
    when(() => mockConsentViewModel.isLoading).thenReturn(false);
    when(() => mockConsentViewModel.consent).thenReturn(
      const ConsentModel(
        id: '1',
        userId: 'test',
        sessionTranscriptRetention: '30_days',
        crossPartnerInsightSharing: 'anonymized',
        jointSessionParticipation: 'not_enrolled',
        sharedRelationshipContext: 'not_participating',
        therapistSummaryAccess: false,
      ),
    );
    when(() => mockConsentViewModel.privateMemoryCount).thenReturn(0);
    when(() => mockConsentViewModel.sharedMemoryCount).thenReturn(0);
  });

  Widget createWidgetUnderTest() {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthViewModel>.value(value: mockAuthViewModel),
        ChangeNotifierProvider<RelationshipViewModel>.value(
          value: mockRelationshipViewModel,
        ),
        ChangeNotifierProvider<ConsentViewModel>.value(
          value: mockConsentViewModel,
        ),
      ],
      child: const MaterialApp(home: LoginScreen()),
    );
  }

  testWidgets(
    'Integration: Successful login navigates to MainNavigationScreen',
    (WidgetTester tester) async {
      // Return true for success
      when(
        () => mockAuthViewModel.loginWithEmail(),
      ).thenAnswer((_) async => true);

      await tester.pumpWidget(createWidgetUnderTest());

      // Tap login button
      await tester.tap(find.text('Sign In'));

      // Pump frames for animation and navigation
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump(const Duration(seconds: 1));
      await tester.pump(const Duration(seconds: 2));

      // Verify navigation occurred
      expect(find.byType(MainNavigationScreen), findsOneWidget);
      expect(find.byType(LoginScreen), findsNothing);
    },
  );
}
