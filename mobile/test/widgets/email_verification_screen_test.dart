import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/auth/views/email_verification_screen.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/features/auth/views/login_screen.dart';
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
  });

  testWidgets('EmailVerificationScreen renders perfectly and navigates back to login', (WidgetTester tester) async {
    await tester.pumpWidget(
      ChangeNotifierProvider<AuthViewModel>.value(
        value: mockAuthViewModel,
        child: const MaterialApp(
          home: EmailVerificationScreen(email: 'test@example.com'),
        ),
      ),
    );

    expect(find.text('Verify Email'), findsWidgets);
    expect(find.text('Check your email'), findsOneWidget);
    expect(find.textContaining('test@example.com'), findsOneWidget);
    
    // Tap Return to Login button
    await tester.tap(find.text('Back to Login'));
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));
    
    // As LoginScreen isn't injected, pushing a generic MaterialPageRoute for LoginScreen occurs.
    expect(find.byType(LoginScreen), findsOneWidget);
  });
}
