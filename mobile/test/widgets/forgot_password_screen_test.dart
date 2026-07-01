import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:mocktail/mocktail.dart';
import 'package:mobile/features/auth/views/forgot_password_screen.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/features/auth/views/new_password_screen.dart';

class MockAuthViewModel extends Mock implements AuthViewModel {}

void main() {
  late MockAuthViewModel mockAuthViewModel;

  setUp(() {
    mockAuthViewModel = MockAuthViewModel();
    when(() => mockAuthViewModel.isLoading).thenReturn(false);
    when(() => mockAuthViewModel.errorMessage).thenReturn(null);
    when(() => mockAuthViewModel.email).thenReturn('test@example.com');
    when(() => mockAuthViewModel.setEmail(any())).thenAnswer((_) {});
  });

  Widget createWidgetUnderTest() {
    return ChangeNotifierProvider<AuthViewModel>.value(
      value: mockAuthViewModel,
      child: const MaterialApp(
        home: ForgotPasswordScreen(),
      ),
    );
  }

  group('ForgotPasswordScreen Tests', () {
    testWidgets('renders properly', (WidgetTester tester) async {
      await tester.pumpWidget(createWidgetUnderTest());

      expect(find.text('Forgot Password?'), findsOneWidget);
      expect(find.text('EMAIL ADDRESS'), findsOneWidget);
      expect(find.text('Send Code'), findsOneWidget);
    });

    testWidgets('triggers sendPasswordResetEmail', (WidgetTester tester) async {
      when(() => mockAuthViewModel.sendPasswordResetEmail()).thenAnswer((_) async => false);
      
      await tester.pumpWidget(createWidgetUnderTest());
      
      final sendCodeFinder = find.text('Send Code');
      await tester.ensureVisible(sendCodeFinder);
      await tester.tap(sendCodeFinder);
      await tester.pump();
      
      verify(() => mockAuthViewModel.sendPasswordResetEmail()).called(1);
    });

    testWidgets('routes to NewPasswordScreen on success', (WidgetTester tester) async {
      when(() => mockAuthViewModel.sendPasswordResetEmail()).thenAnswer((_) async => true);
      
      await tester.pumpWidget(createWidgetUnderTest());
      
      final sendCodeFinder = find.text('Send Code');
      await tester.ensureVisible(sendCodeFinder);
      await tester.tap(sendCodeFinder);
      await tester.pump();
      await tester.pump(const Duration(seconds: 1));
      
      expect(find.byType(NewPasswordScreen), findsOneWidget);
    });

    testWidgets('ForgotPasswordScreen shows error message when viewModel has error', (WidgetTester tester) async {
      when(() => mockAuthViewModel.errorMessage).thenReturn('Email not found');
      
      await tester.pumpWidget(createWidgetUnderTest());
      await tester.pump();
      
      expect(find.text('Email not found'), findsOneWidget);
    });

    testWidgets('ForgotPasswordScreen shows loading state', (WidgetTester tester) async {
      when(() => mockAuthViewModel.isLoading).thenReturn(true);
      
      await tester.pumpWidget(createWidgetUnderTest());
      await tester.pump();
      
      expect(find.text('Sending...'), findsOneWidget);
    });
  });
}
