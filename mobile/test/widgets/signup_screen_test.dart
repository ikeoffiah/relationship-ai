import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:mocktail/mocktail.dart';
import 'package:mobile/features/auth/views/signup_screen.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/features/auth/views/email_verification_screen.dart';

class MockAuthViewModel extends Mock implements AuthViewModel {}

void main() {
  late MockAuthViewModel mockAuthViewModel;

  setUp(() {
    mockAuthViewModel = MockAuthViewModel();
    when(() => mockAuthViewModel.isLoading).thenReturn(false);
    when(() => mockAuthViewModel.errorMessage).thenReturn(null);
    when(() => mockAuthViewModel.email).thenReturn('test@example.com');
    // Ensure all setters work silently
    when(() => mockAuthViewModel.setFullName(any())).thenAnswer((_) {});
    when(() => mockAuthViewModel.setEmail(any())).thenAnswer((_) {});
    when(() => mockAuthViewModel.setPassword(any())).thenAnswer((_) {});
    when(() => mockAuthViewModel.setConfirmPassword(any())).thenAnswer((_) {});
  });

  Widget createWidgetUnderTest() {
    return MaterialApp(
      home: ChangeNotifierProvider<AuthViewModel>.value(
        value: mockAuthViewModel,
        child: const SignupScreen(),
      ),
    );
  }

  group('SignupScreen Widget Tests', () {
    testWidgets('SignupScreen renders fields and buttons', (WidgetTester tester) async {
      await tester.pumpWidget(createWidgetUnderTest());

      expect(find.text('FULL NAME'), findsOneWidget);
      expect(find.text('EMAIL'), findsOneWidget);
      expect(find.text('PASSWORD'), findsOneWidget);
      expect(find.text('CONFIRM PASSWORD'), findsOneWidget);
      expect(find.text('Create Account'), findsOneWidget);
      expect(find.text('Sign up with Google'), findsOneWidget);
    });

    testWidgets('Tapping Terms Checkbox accepts Terms', (WidgetTester tester) async {
      await tester.pumpWidget(createWidgetUnderTest());
      
      // Tap the terms checkbox (represented by the text 'Terms of Service')
      final termsFinder = find.textContaining('Terms of Service');
      await tester.ensureVisible(termsFinder);
      await tester.tap(termsFinder);
      await tester.pump();
      
      // We know it accepted terms because signup should now trigger
      when(() => mockAuthViewModel.signupWithEmail()).thenAnswer((_) async => false);
      
      final createFinder = find.text('Create Account');
      await tester.ensureVisible(createFinder);
      await tester.tap(createFinder);
      await tester.pump();
      
      verify(() => mockAuthViewModel.signupWithEmail()).called(1);
    });

    testWidgets('Signup routes to EmailVerificationScreen on success', (WidgetTester tester) async {
      await tester.pumpWidget(createWidgetUnderTest());
      
      // Agree to terms
      final termsFinder = find.textContaining('Terms of Service');
      await tester.ensureVisible(termsFinder);
      await tester.tap(termsFinder);
      await tester.pump();
      
      when(() => mockAuthViewModel.signupWithEmail()).thenAnswer((_) async => true);
      
      final createFinder = find.text('Create Account');
      await tester.ensureVisible(createFinder);
      await tester.tap(createFinder);
      await tester.pump();
      await tester.pump(const Duration(seconds: 1));

      expect(find.byType(EmailVerificationScreen), findsOneWidget);
    });

    testWidgets('SignupScreen shows error message when viewModel has error', (WidgetTester tester) async {
      when(() => mockAuthViewModel.errorMessage).thenReturn('Signup Failed');
      
      await tester.pumpWidget(createWidgetUnderTest());
      await tester.pump();
      
      expect(find.text('Signup Failed'), findsOneWidget);
    });

    testWidgets('SignupScreen shows loading state', (WidgetTester tester) async {
      when(() => mockAuthViewModel.isLoading).thenReturn(true);
      
      await tester.pumpWidget(createWidgetUnderTest());
      await tester.pump();
      
      expect(find.text('Creating account...'), findsOneWidget);
    });
  });
}
