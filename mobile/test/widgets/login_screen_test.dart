import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:mocktail/mocktail.dart';
import 'package:mobile/features/auth/views/login_screen.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';

class MockAuthViewModel extends Mock implements AuthViewModel {}

void main() {
  late MockAuthViewModel mockAuthViewModel;

  setUp(() {
    mockAuthViewModel = MockAuthViewModel();
    // Setup default mock returns
    when(() => mockAuthViewModel.isLoading).thenReturn(false);
    when(() => mockAuthViewModel.errorMessage).thenReturn(null);
    when(() => mockAuthViewModel.email).thenReturn('');
    when(() => mockAuthViewModel.password).thenReturn('');
  });

  Widget createWidgetUnderTest() {
    return MaterialApp(
      home: ChangeNotifierProvider<AuthViewModel>.value(
        value: mockAuthViewModel,
        child: const LoginScreen(),
      ),
    );
  }

  testWidgets('LoginScreen renders fields and buttons', (WidgetTester tester) async {
    await tester.pumpWidget(createWidgetUnderTest());

    expect(find.text('EMAIL'), findsOneWidget);
    expect(find.text('PASSWORD'), findsOneWidget);
    expect(find.text('Sign In'), findsOneWidget);
    expect(find.text('Sign in with Google'), findsOneWidget);
    expect(find.text('Face ID / Fingerprint'), findsOneWidget);
  });

  testWidgets('Input fields update ViewModel', (WidgetTester tester) async {
    await tester.pumpWidget(createWidgetUnderTest());

    when(() => mockAuthViewModel.setEmail(any())).thenAnswer((_) {});
    when(() => mockAuthViewModel.setPassword(any())).thenAnswer((_) {});

    await tester.enterText(find.byType(TextField).first, 'test@example.com');
    await tester.enterText(find.byType(TextField).last, 'password123');

    verify(() => mockAuthViewModel.setEmail('test@example.com')).called(1);
    verify(() => mockAuthViewModel.setPassword('password123')).called(1);
  });

  testWidgets('Sign In button calls loginWithEmail', (WidgetTester tester) async {
    when(() => mockAuthViewModel.loginWithEmail()).thenAnswer((_) async => false);
    
    await tester.pumpWidget(createWidgetUnderTest());
    await tester.tap(find.text('Sign In'));
    await tester.pump();

    verify(() => mockAuthViewModel.loginWithEmail()).called(1);
  });

  testWidgets('LoginScreen shows error message when viewModel has error', (WidgetTester tester) async {
    when(() => mockAuthViewModel.errorMessage).thenReturn('Invalid Email Address');
    
    await tester.pumpWidget(createWidgetUnderTest());
    await tester.pump();
    
    expect(find.text('Invalid Email Address'), findsOneWidget);
  });

  testWidgets('LoginScreen shows loading state', (WidgetTester tester) async {
    when(() => mockAuthViewModel.isLoading).thenReturn(true);
    
    await tester.pumpWidget(createWidgetUnderTest());
    await tester.pump();
    
    expect(find.text('Signing in...'), findsOneWidget);
  });
}
