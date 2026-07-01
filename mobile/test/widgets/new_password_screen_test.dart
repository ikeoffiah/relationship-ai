import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:mocktail/mocktail.dart';
import 'package:mobile/features/auth/views/new_password_screen.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/features/auth/views/login_screen.dart';

class MockAuthViewModel extends Mock implements AuthViewModel {}

void main() {
  late MockAuthViewModel mockAuthViewModel;

  setUp(() {
    mockAuthViewModel = MockAuthViewModel();
    when(() => mockAuthViewModel.isLoading).thenReturn(false);
    when(() => mockAuthViewModel.errorMessage).thenReturn(null);
    when(() => mockAuthViewModel.password).thenReturn('password123');
    when(() => mockAuthViewModel.setPassword(any())).thenAnswer((_) {});
    when(() => mockAuthViewModel.setConfirmPassword(any())).thenAnswer((_) {});
  });

  Widget createWidgetUnderTest() {
    return ChangeNotifierProvider<AuthViewModel>.value(
      value: mockAuthViewModel,
      child: const MaterialApp(
        home: NewPasswordScreen(),
      ),
    );
  }

  group('NewPasswordScreen Tests', () {
    testWidgets('renders properly', (WidgetTester tester) async {
      await tester.pumpWidget(createWidgetUnderTest());

      expect(find.text('Reset Password'), findsWidgets);
      expect(find.text('NEW PASSWORD'), findsOneWidget);
    });

    testWidgets('triggers resetPassword', (WidgetTester tester) async {
      when(() => mockAuthViewModel.resetPassword()).thenAnswer((_) async => false);
      
      await tester.pumpWidget(createWidgetUnderTest());
      
      final resetFinder = find.text('Reset Password');
      await tester.ensureVisible(resetFinder.last);
      await tester.tap(resetFinder.last);
      await tester.pump();
      
      verify(() => mockAuthViewModel.resetPassword()).called(1);
    });

    testWidgets('routes to LoginScreen on success', (WidgetTester tester) async {
      when(() => mockAuthViewModel.resetPassword()).thenAnswer((_) async => true);
      
      await tester.pumpWidget(createWidgetUnderTest());
      
      final resetFinder = find.text('Reset Password');
      await tester.ensureVisible(resetFinder.last);
      await tester.tap(resetFinder.last);
      await tester.pump();
      await tester.pump(const Duration(seconds: 1));
      
      expect(find.byType(LoginScreen), findsOneWidget);
    });

    testWidgets('NewPasswordScreen shows error message when viewModel has error', (WidgetTester tester) async {
      when(() => mockAuthViewModel.errorMessage).thenReturn('Invalid Token');
      
      await tester.pumpWidget(createWidgetUnderTest());
      await tester.pump();
      
      expect(find.text('Invalid Token'), findsOneWidget);
    });

    testWidgets('NewPasswordScreen shows loading state', (WidgetTester tester) async {
      when(() => mockAuthViewModel.isLoading).thenReturn(true);
      
      await tester.pumpWidget(createWidgetUnderTest());
      await tester.pump();
      
      expect(find.text('Resetting...'), findsOneWidget);
    });
  });
}
