import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';

import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/features/auth/views/login_screen.dart';
import 'package:mobile/features/home/views/main_navigation_screen.dart';
import 'package:mobile/features/relationship/relationship_viewmodel.dart';

class MockAuthViewModel extends Mock implements AuthViewModel {}
class MockRelationshipViewModel extends Mock implements RelationshipViewModel {}

void main() {
  late MockAuthViewModel mockAuthViewModel;
  late MockRelationshipViewModel mockRelationshipViewModel;

  setUp(() {
    mockAuthViewModel = MockAuthViewModel();
    mockRelationshipViewModel = MockRelationshipViewModel();
    
    when(() => mockAuthViewModel.isLoading).thenReturn(false);
    when(() => mockAuthViewModel.errorMessage).thenReturn(null);
    when(() => mockAuthViewModel.email).thenReturn('test@example.com');
    when(() => mockAuthViewModel.password).thenReturn('password123');
    when(() => mockAuthViewModel.setEmail(any())).thenReturn(null);
    when(() => mockAuthViewModel.setPassword(any())).thenReturn(null);
    when(() => mockAuthViewModel.user).thenReturn(null);

    when(() => mockRelationshipViewModel.status).thenReturn(RelationshipStatus.active);
    when(() => mockRelationshipViewModel.currentRelationship).thenReturn(null);
  });

  Widget createWidgetUnderTest() {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthViewModel>.value(value: mockAuthViewModel),
        ChangeNotifierProvider<RelationshipViewModel>.value(value: mockRelationshipViewModel),
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
      await tester.pumpAndSettle();

      // Verify navigation occurred
      expect(find.byType(MainNavigationScreen), findsOneWidget);
      expect(find.byType(LoginScreen), findsNothing);
    },
  );
}
