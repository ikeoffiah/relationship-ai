import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:provider/provider.dart';

import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/features/auth/models/user_profile.dart';
import 'package:mobile/features/auth/views/login_screen.dart';
import 'package:mobile/features/home/views/main_navigation_screen.dart';
import 'package:mobile/features/relationship/relationship_viewmodel.dart';
import 'package:mobile/features/notifications/viewmodels/notification_viewmodel.dart';
import 'package:mobile/features/history/viewmodels/session_history_viewmodel.dart';
import 'package:mobile/features/settings/viewmodels/settings_viewmodel.dart';

import 'package:mobile/features/consent/viewmodels/consent_viewmodel.dart';
import 'package:mobile/features/onboarding/onboarding_viewmodel.dart';
import 'package:mobile/features/consent/models/consent_model.dart';

class MockAuthViewModel extends Mock implements AuthViewModel {}

class MockRelationshipViewModel extends Mock implements RelationshipViewModel {}

class MockConsentViewModel extends Mock implements ConsentViewModel {}

class MockNotificationViewModel extends Mock
    implements NotificationViewModel {}

class MockSessionHistoryViewModel extends Mock
    implements SessionHistoryViewModel {}

class MockSettingsViewModel extends Mock implements SettingsViewModel {}

class MockOnboardingViewModel extends Mock implements OnboardingViewModel {}

/// Auth flow testx
void main() {
  late MockAuthViewModel mockAuthViewModel;
  late MockRelationshipViewModel mockRelationshipViewModel;
  late MockConsentViewModel mockConsentViewModel;
  late MockNotificationViewModel mockNotificationViewModel;
  late MockSessionHistoryViewModel mockSessionHistoryViewModel;
  late MockSettingsViewModel mockSettingsViewModel;
  late MockOnboardingViewModel mockOnboardingViewModel;

  setUp(() {
    mockAuthViewModel = MockAuthViewModel();
    mockRelationshipViewModel = MockRelationshipViewModel();
    mockConsentViewModel = MockConsentViewModel();
    mockNotificationViewModel = MockNotificationViewModel();
    mockSessionHistoryViewModel = MockSessionHistoryViewModel();
    mockSettingsViewModel = MockSettingsViewModel();
    mockOnboardingViewModel = MockOnboardingViewModel();
    when(() => mockOnboardingViewModel.loadProfile()).thenAnswer((_) async => true);
    when(() => mockOnboardingViewModel.onboardingCompleted).thenReturn(true);

    when(() => mockNotificationViewModel.unreadCount).thenReturn(0);
    when(
      () => mockNotificationViewModel.fetchUnreadCount(any()),
    ).thenAnswer((_) async {});

    when(() => mockSessionHistoryViewModel.sessions).thenReturn(const []);
    when(() => mockSessionHistoryViewModel.isLoading).thenReturn(false);
    when(() => mockSessionHistoryViewModel.isLoadingMore).thenReturn(false);
    when(() => mockSessionHistoryViewModel.hasMore).thenReturn(false);
    when(() => mockSessionHistoryViewModel.isEmpty).thenReturn(true);
    when(() => mockSessionHistoryViewModel.filter).thenReturn('all');
    when(() => mockSessionHistoryViewModel.error).thenReturn(null);
    when(() => mockSessionHistoryViewModel.loadSessions()).thenAnswer((_) async {});
    when(() => mockSessionHistoryViewModel.loadMore()).thenAnswer((_) async {});

    when(() => mockSettingsViewModel.isLoading).thenReturn(false);
    when(() => mockSettingsViewModel.errorMessage).thenReturn(null);
    when(() => mockSettingsViewModel.successMessage).thenReturn(null);
    when(() => mockSettingsViewModel.displayName).thenReturn('Test User');
    when(() => mockSettingsViewModel.email).thenReturn('test@example.com');
    when(() => mockSettingsViewModel.appLockTimeoutMinutes).thenReturn(5);
    when(
      () => mockSettingsViewModel.notificationPrefs,
    ).thenReturn(const NotificationPreferences());
    when(() => mockSettingsViewModel.loadProfile(any())).thenAnswer((_) async {});
    when(
      () => mockSettingsViewModel.loadNotificationPreferences(any()),
    ).thenAnswer((_) async {});

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
        ChangeNotifierProvider<NotificationViewModel>.value(
          value: mockNotificationViewModel,
        ),
        ChangeNotifierProvider<SessionHistoryViewModel>.value(
          value: mockSessionHistoryViewModel,
        ),
        ChangeNotifierProvider<SettingsViewModel>.value(
          value: mockSettingsViewModel,
        ),
        ChangeNotifierProvider<OnboardingViewModel>.value(
          value: mockOnboardingViewModel,
        ),
      ],
      child: const ProviderScope(child: MaterialApp(home: LoginScreen())),
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
