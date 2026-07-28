import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart' as provider;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/features/auth/models/user_profile.dart';
import 'package:mobile/features/relationship/relationship_viewmodel.dart';
import 'package:mobile/features/home/views/home_screen.dart';
import 'package:mobile/features/notifications/viewmodels/notification_viewmodel.dart';
import 'package:mobile/features/engagement/engagement_viewmodel.dart';
import 'package:mobile/features/home/views/today_hero.dart';

class MockAuthViewModel extends Mock implements AuthViewModel {}

class MockRelationshipViewModel extends Mock implements RelationshipViewModel {}

class MockNotificationViewModel extends Mock
    implements NotificationViewModel {}


/// Home calls loadRitual() in initState. Against no API that future never
/// completes, so pumpAndSettle hangs and nothing below it ever renders — which
/// looks exactly like a broken screen. Stubbing the load keeps the widget test
/// about the widget.
class _StubEngagementViewModel extends EngagementViewModel {
  @override
  Future<void> loadRitual() async {}
}

void main() {
  late MockAuthViewModel mockAuthViewModel;
  late MockRelationshipViewModel mockRelationshipViewModel;
  late MockNotificationViewModel mockNotificationViewModel;
  const userId = 'user123';

  setUp(() {
    mockAuthViewModel = MockAuthViewModel();
    mockRelationshipViewModel = MockRelationshipViewModel();
    mockNotificationViewModel = MockNotificationViewModel();

    when(() => mockNotificationViewModel.unreadCount).thenReturn(0);
    when(
      () => mockNotificationViewModel.fetchUnreadCount(any()),
    ).thenAnswer((_) async {});

    const mockUser = UserProfile(
      id: userId,
      email: 'test@example.com',
      name: 'John Doe',
    );
    when(() => mockAuthViewModel.user).thenReturn(mockUser);

    when(
      () => mockRelationshipViewModel.fetchRelationshipStatus(),
    ).thenAnswer((_) async {});
    when(
      () => mockRelationshipViewModel.status,
    ).thenReturn(RelationshipStatus.notConnected);
    when(() => mockRelationshipViewModel.currentRelationship).thenReturn(null);
  });

  Widget createWidgetUnderTest() {
    return provider.MultiProvider(
      providers: [
        provider.ChangeNotifierProvider<EngagementViewModel>(
          create: (_) => _StubEngagementViewModel(),
        ),
        provider.ChangeNotifierProvider<AuthViewModel>.value(
          value: mockAuthViewModel,
        ),
        provider.ChangeNotifierProvider<RelationshipViewModel>.value(
          value: mockRelationshipViewModel,
        ),
        provider.ChangeNotifierProvider<NotificationViewModel>.value(
          value: mockNotificationViewModel,
        ),
      ],
      child: const ProviderScope(child: MaterialApp(home: HomeScreen())),
    );
  }

  testWidgets(
    'HomeScreen shows the day\'s hero and the partner invite when not connected',
    (WidgetTester tester) async {
      await tester.pumpWidget(createWidgetUnderTest());
      await tester.pumpAndSettle();

      expect(find.text('Good day,'), findsOneWidget);
      expect(find.text('John'), findsOneWidget);
      // Phase 3 moved the session cards to the Talk hub; phase 4 replaced the
      // static card list with one state-aware hero. With no ritual loaded the
      // resolver lands on "done", which is the honest empty state.
      expect(find.byType(TodayHero), findsOneWidget);
      expect(find.textContaining('Connect with your partner'), findsOneWidget);
    },
  );
}
