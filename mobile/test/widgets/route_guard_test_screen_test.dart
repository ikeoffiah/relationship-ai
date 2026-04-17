import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/auth/views/route_guard_test_screen.dart';
import 'package:mobile/features/auth/views/login_screen.dart';

import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:provider/provider.dart';
import 'package:mocktail/mocktail.dart';

class MockAuthViewModel extends Mock implements AuthViewModel {}

void main() {
  late MockAuthViewModel mockAuthViewModel;
  
  setUp(() {
    mockAuthViewModel = MockAuthViewModel();
    when(() => mockAuthViewModel.email).thenReturn('test@example.com');
    when(() => mockAuthViewModel.isLoading).thenReturn(false);
    when(() => mockAuthViewModel.errorMessage).thenReturn(null);
    when(() => mockAuthViewModel.logout()).thenAnswer((_) async {});
  });

  testWidgets('RouteGuardTestScreen renders properly and allows back navigation', (WidgetTester tester) async {
    await tester.pumpWidget(
      ChangeNotifierProvider<AuthViewModel>.value(
        value: mockAuthViewModel,
        child: const MaterialApp(
          home: RouteGuardTestScreen(),
        ),
      ),
    );

    expect(find.text('Authenticated Route'), findsOneWidget);
    
    // Tap the Sign Out
    final signOutFinder = find.text('Sign Out');
    await tester.ensureVisible(signOutFinder);
    await tester.tap(signOutFinder);
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));
    
    // Check if LoginScreen is now present
    expect(find.byType(LoginScreen), findsOneWidget);
  });
}
