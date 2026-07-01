import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/auth/views/welcome_screen.dart';
import 'package:mobile/features/auth/viewmodels/welcome_viewmodel.dart';
import 'package:provider/provider.dart';
import 'package:mobile/features/auth/models/welcome_config.dart';
import 'package:mocktail/mocktail.dart';

class MockWelcomeViewModel extends Mock implements WelcomeViewModel {}
class MockBuildContext extends Mock implements BuildContext {}

void main() {
  late MockWelcomeViewModel mockViewModel;

  setUpAll(() {
    registerFallbackValue(MockBuildContext());
  });

  setUp(() {
    mockViewModel = MockWelcomeViewModel();
    when(() => mockViewModel.isInitialized).thenReturn(true);
    when(() => mockViewModel.currentIndex).thenReturn(0);
    when(() => mockViewModel.page).thenReturn(0.0);
    when(() => mockViewModel.pageController).thenReturn(PageController());
    when(() => mockViewModel.onPageChanged(any())).thenReturn(null);
    when(() => mockViewModel.getLogoFadeAnimation()).thenReturn(const AlwaysStoppedAnimation(1.0));
    when(() => mockViewModel.getLogoSlideAnimation()).thenReturn(const AlwaysStoppedAnimation(0.0));
    when(() => mockViewModel.getLogoFloatController()).thenReturn(AnimationController(vsync: const TestVSync()));
    when(() => mockViewModel.getTextBoxFadeAnimation()).thenReturn(const AlwaysStoppedAnimation(1.0));
    when(() => mockViewModel.getIndicatorPulseAnimation()).thenReturn(const AlwaysStoppedAnimation(1.0));
    when(() => mockViewModel.logoFloatProgress).thenReturn(0.0);
    when(() => mockViewModel.onStartTapped(any())).thenReturn(null);
  });

  testWidgets('WelcomeScreen renders UI elements', (WidgetTester tester) async {
    await tester.pumpWidget(
      ChangeNotifierProvider<WelcomeViewModel>.value(
        value: mockViewModel,
        child: const MaterialApp(
          home: WelcomeScreen(),
        ),
      ),
    );

    await tester.pump();
    
    expect(find.text(WelcomeConfig.startButtonLabel), findsWidgets);
    expect(find.text(WelcomeConfig.slides[0].heading), findsOneWidget);
  });
}
