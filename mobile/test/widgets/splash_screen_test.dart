import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/auth/views/splash_screen.dart';
import 'package:mobile/features/auth/viewmodels/splash_viewmodel.dart';
import 'package:provider/provider.dart';
import 'package:mobile/features/auth/models/splash_config.dart';
import 'package:mocktail/mocktail.dart';

class MockSplashViewModel extends Mock implements SplashViewModel {}

void main() {
  late MockSplashViewModel mockViewModel;

  setUp(() {
    mockViewModel = MockSplashViewModel();
    when(() => mockViewModel.isInitialized).thenReturn(true);
    when(() => mockViewModel.getTextFadeAnimation()).thenReturn(const AlwaysStoppedAnimation(1.0));
    when(() => mockViewModel.orb1).thenReturn(null);
    when(() => mockViewModel.orb2).thenReturn(null);
  });

  testWidgets('SplashScreen renders gracefully', (WidgetTester tester) async {
    await tester.pumpWidget(MaterialApp(
      home: ChangeNotifierProvider<SplashViewModel>.value(
        value: mockViewModel,
        child: const SplashScreen(),
      ),
    ));

    await tester.pump();
    
    expect(find.text(SplashConfig.mainText), findsWidgets);
  });
}
