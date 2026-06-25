import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart' as provider;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/features/auth/models/user_profile.dart';
import 'package:mobile/features/relationship/relationship_viewmodel.dart';
import 'package:mobile/features/home/views/home_screen.dart';
import 'package:mobile/features/home/home_notifier.dart';

class MockAuthViewModel extends Mock implements AuthViewModel {}
class MockRelationshipViewModel extends Mock implements RelationshipViewModel {}

void main() {
  late MockAuthViewModel mockAuthViewModel;
  late MockRelationshipViewModel mockRelationshipViewModel;
  const userId = 'user123';

  setUp(() {
    mockAuthViewModel = MockAuthViewModel();
    mockRelationshipViewModel = MockRelationshipViewModel();

    const mockUser = UserProfile(id: userId, email: 'test@example.com', name: 'John Doe');
    when(() => mockAuthViewModel.user).thenReturn(mockUser);

    when(() => mockRelationshipViewModel.fetchRelationshipStatus()).thenAnswer((_) async {});
    when(() => mockRelationshipViewModel.status).thenReturn(RelationshipStatus.notConnected);
    when(() => mockRelationshipViewModel.currentRelationship).thenReturn(null);
  });

  Widget createWidgetUnderTest() {
    return provider.MultiProvider(
      providers: [
        provider.ChangeNotifierProvider<AuthViewModel>.value(value: mockAuthViewModel),
        provider.ChangeNotifierProvider<RelationshipViewModel>.value(value: mockRelationshipViewModel),
      ],
      child: const ProviderScope(
        child: MaterialApp(
          home: HomeScreen(),
        ),
      ),
    );
  }

  testWidgets('HomeScreen renders private session card and partner invite banner when not connected', (WidgetTester tester) async {
    await tester.pumpWidget(createWidgetUnderTest());
    await tester.pumpAndSettle();

    expect(find.text('Good day,'), findsOneWidget);
    expect(find.text('John'), findsOneWidget);
    expect(find.textContaining('Individual session'), findsOneWidget);
    expect(find.textContaining('Connect with your partner'), findsOneWidget);
    expect(find.text('Begin session'), findsOneWidget);
  });
}
