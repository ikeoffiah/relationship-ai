import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/api_services/personalization_api_service.dart';
import 'package:mobile/features/auth/views/auth_landing_screen.dart';
import 'package:mobile/features/onboarding/onboarding_viewmodel.dart';

class MockPersonalizationApi extends Mock implements PersonalizationApiService {}

void main() {
  late MockPersonalizationApi api;

  setUp(() {
    api = MockPersonalizationApi();
  });

  OnboardingViewModel vm() => OnboardingViewModel(api: api);

  group('decidePostAuthDestination', () {
    test('new user (profile not completed) → onboarding', () async {
      when(() => api.fetchProfile())
          .thenAnswer((_) async => {'onboarding_completed': false});

      expect(
        await decidePostAuthDestination(vm()),
        PostAuthDestination.onboarding,
      );
    });

    test('completed user → app', () async {
      when(() => api.fetchProfile())
          .thenAnswer((_) async => {'onboarding_completed': true});

      expect(await decidePostAuthDestination(vm()), PostAuthDestination.app);
    });

    test('failed lookup fails open to the app, not onboarding', () async {
      // A returning user must not be trapped in onboarding by a transient error.
      when(() => api.fetchProfile()).thenThrow(Exception('network down'));

      expect(await decidePostAuthDestination(vm()), PostAuthDestination.app);
    });

    test('missing onboarding_completed key is treated as not completed',
        () async {
      when(() => api.fetchProfile()).thenAnswer((_) async => {});

      expect(
        await decidePostAuthDestination(vm()),
        PostAuthDestination.onboarding,
      );
    });
  });

  testWidgets('the gate shows a loader while deciding', (tester) async {
    // Never completes: the gate stays on the loader and never navigates to the
    // (provider-heavy) destination, and there is no timer to leak at teardown.
    final pending = Completer<Map<String, dynamic>>();
    when(() => api.fetchProfile()).thenAnswer((_) => pending.future);

    await tester.pumpWidget(
      ChangeNotifierProvider<OnboardingViewModel>(
        create: (_) => vm(),
        child: const MaterialApp(home: AuthLandingScreen()),
      ),
    );
    await tester.pump(); // decision still pending

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });
}
