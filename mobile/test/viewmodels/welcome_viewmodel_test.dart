import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/auth/viewmodels/welcome_viewmodel.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:provider/provider.dart';
import 'package:mocktail/mocktail.dart';

class MockAuthViewModel extends Mock implements AuthViewModel {}

class MockNavigatorObserver extends Mock implements NavigatorObserver {}

class FakeRoute extends Fake implements Route<dynamic> {}

void main() {
  late MockAuthViewModel mockAuthViewModel;
  late MockNavigatorObserver mockObserver;

  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    registerFallbackValue(FakeRoute());
  });

  setUp(() {
    mockAuthViewModel = MockAuthViewModel();
    mockObserver = MockNavigatorObserver();

    when(() => mockAuthViewModel.isLoading).thenReturn(false);
    when(() => mockAuthViewModel.errorMessage).thenReturn(null);
    when(() => mockAuthViewModel.email).thenReturn('');
    when(() => mockAuthViewModel.password).thenReturn('');
  });

  group('WelcomeViewModel Unit Tests', () {
    testWidgets('Initializes correctly and handles auto-slide timer', (
      WidgetTester tester,
    ) async {
      final vm = WelcomeViewModel();
      vm.initialize(const TestVSync());

      expect(vm.isInitialized, true);

      // Need to wait for the auto-slide timer or it will leak
      await tester.pump(const Duration(seconds: 10));
      vm.dispose();
    });

    testWidgets('onPageChanged updates index', (WidgetTester tester) async {
      final vm = WelcomeViewModel();
      vm.initialize(const TestVSync());

      vm.onPageChanged(1);
      expect(vm.currentIndex, 1);

      await tester.pump(const Duration(seconds: 10));
      vm.dispose();
    });
  });

  group('WelcomeViewModel Navigation Tests', () {
    testWidgets('onStartTapped navigates to LoginScreen', (
      WidgetTester tester,
    ) async {
      final vm = WelcomeViewModel();
      vm.initialize(const TestVSync());

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<WelcomeViewModel>.value(value: vm),
            ChangeNotifierProvider<AuthViewModel>.value(
              value: mockAuthViewModel,
            ),
          ],
          child: MaterialApp(
            navigatorObservers: [mockObserver],
            home: Builder(
              builder: (context) {
                return ElevatedButton(
                  onPressed: () => vm.onStartTapped(context),
                  child: const Text('Tap'),
                );
              },
            ),
          ),
        ),
      );

      await tester.tap(find.text('Tap'));
      await tester.pump(); // Start navigation
      await tester.pump(
        const Duration(milliseconds: 100),
      ); // Complete navigation

      // Verify didPush was called (1 for initial route, 1 for LoginScreen)
      verify(() => mockObserver.didPush(any(), any())).called(2);

      await tester.pump(const Duration(seconds: 10));
      vm.dispose();
    });

    testWidgets('onLearnMoreTapped navigates to SignupScreen', (
      WidgetTester tester,
    ) async {
      final vm = WelcomeViewModel();
      vm.initialize(const TestVSync());

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<WelcomeViewModel>.value(value: vm),
            ChangeNotifierProvider<AuthViewModel>.value(
              value: mockAuthViewModel,
            ),
          ],
          child: MaterialApp(
            navigatorObservers: [mockObserver],
            home: Builder(
              builder: (context) {
                return ElevatedButton(
                  onPressed: () => vm.onLearnMoreTapped(context),
                  child: const Text('Tap'),
                );
              },
            ),
          ),
        ),
      );

      await tester.tap(find.text('Tap'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      verify(() => mockObserver.didPush(any(), any())).called(2);

      await tester.pump(const Duration(seconds: 10));
      vm.dispose();
    });
  });
}
