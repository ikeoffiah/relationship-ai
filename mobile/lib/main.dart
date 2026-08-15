import 'package:flutter/material.dart';
import 'package:provider/provider.dart' as provider;
import 'package:flutter_riverpod/flutter_riverpod.dart'
    as riverpod
    hide Provider;
import 'package:sentry_flutter/sentry_flutter.dart';
import 'package:firebase_core/firebase_core.dart';
import 'dart:async';
import 'package:app_links/app_links.dart';
import 'package:mobile/features/chat/chat_screen.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/core/analytics/analytics.dart';
import 'package:mobile/core/analytics/sinks/firebase_analytics_sink.dart';
import 'package:mobile/core/analytics/sinks/posthog_sink.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/features/auth/viewmodels/splash_viewmodel.dart';
import 'package:mobile/features/auth/viewmodels/welcome_viewmodel.dart';
import 'package:mobile/features/auth/views/splash_screen.dart';
import 'package:mobile/features/auth/views/age_verification_screen.dart';
import 'package:mobile/features/auth/views/signup_screen.dart';
import 'package:mobile/features/auth/views/new_password_screen.dart';
import 'package:mobile/features/consent/viewmodels/consent_viewmodel.dart';
import 'package:mobile/features/consent/consent_dashboard_screen.dart';
import 'package:mobile/features/relationship/relationship_viewmodel.dart';
import 'package:mobile/core/api_services/relationship_api_service.dart';
import 'package:mobile/features/relationship/invite_partner_screen.dart';
import 'package:mobile/features/relationship/accept_invite_screen.dart';
import 'package:mobile/features/relationship/dissolve_relationship_screen.dart';
import 'package:mobile/features/relationship/our_story_screen.dart';
import 'package:mobile/features/safety/safety_resources_screen.dart';
import 'package:mobile/features/history/viewmodels/session_history_viewmodel.dart';
import 'package:mobile/features/history/session_history_screen.dart';
import 'package:mobile/features/onboarding/onboarding_viewmodel.dart';
import 'package:mobile/features/onboarding/onboarding_flow_screen.dart';
import 'package:mobile/features/onboarding/screens/onboarding_complete_screen.dart';
import 'package:mobile/features/onboarding/screens/relationship_portrait_screen.dart';
import 'package:mobile/features/notifications/notification_center_screen.dart';
import 'package:mobile/features/notifications/viewmodels/notification_viewmodel.dart';
import 'package:mobile/features/settings/viewmodels/settings_viewmodel.dart';
import 'package:mobile/features/settings/email_change_screen.dart';
import 'package:mobile/features/settings/settings_screen.dart';
import 'package:mobile/features/relay/relay_inbox_screen.dart';
import 'package:mobile/features/relay/relay_viewmodel.dart';
import 'package:mobile/features/engagement/engagement_viewmodel.dart';
import 'package:mobile/features/engagement/views/daily_ritual_screen.dart';
import 'package:mobile/features/engagement/views/shared_goals_screen.dart';
import 'package:mobile/features/games/games_viewmodel.dart';
import 'package:mobile/features/games/views/games_list_screen.dart';
import 'package:mobile/features/faith/faith_viewmodel.dart';
import 'package:mobile/features/faith/views/faith_screen.dart';
import 'package:mobile/features/bliss/bliss_viewmodel.dart';
import 'package:mobile/features/bliss/calendar_viewmodel.dart';
import 'package:mobile/features/bliss/views/calendar_screen.dart';
import 'package:mobile/features/bliss/views/bliss_plan_screen.dart';
import 'package:mobile/features/two_truths/two_truths_viewmodel.dart';
import 'package:mobile/features/two_truths/views/two_truths_screen.dart';
import 'package:mobile/features/commitments/commitment_viewmodel.dart';
import 'package:mobile/features/commitments/views/commitments_screen.dart';
import 'package:mobile/features/focus/focus_viewmodel.dart';
import 'package:mobile/features/focus/views/focus_screen.dart';
import 'package:mobile/core/api_services/notification_api_service.dart';
import 'package:mobile/features/couple_chat/media_cache.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Best-effort Firebase init for push. No explicit options — Firebase reads the
  // per-platform native config (android/app/google-services.json,
  // ios/Runner/GoogleService-Info.plist), which are provided per-environment and
  // NOT committed (they hold client API keys). Guarded so a missing config never
  // blocks startup — push simply stays inert in that case.
  try {
    await Firebase.initializeApp();
  } catch (e) {
    debugPrint('Firebase init skipped: $e');
  }
  await SentryFlutter.init(
    (options) {
      options.dsn =
          'https://04ae4d1e86508070b37d43e4ad62141d@o4511191944593408.ingest.us.sentry.io/4511191967072256';
      options.tracesSampleRate = 1.0;
      // ignore: experimental_member_use
      options.profilesSampleRate = 1.0;
      // This app carries counselling conversations. sendDefaultPii attaches
      // user identifiers and IP; print breadcrumbs sweep up whatever any
      // widget happened to log, which is not a list anyone audits. Both off.
      options.sendDefaultPii = false;
      options.enablePrintBreadcrumbs = false;
    },
    appRunner: () => runApp(
      provider.MultiProvider(
        providers: [
          // One Analytics for the app. Both sinks are constructed but
          // neither reports `isReady` without its dart-defines, so a build
          // with no keys still exercises every call site and sends nothing.
          provider.Provider<Analytics>(
            create: (_) =>
                Analytics(sinks: [PostHogSink(), FirebaseAnalyticsSink()]),
          ),
          provider.ChangeNotifierProvider(create: (_) => AuthViewModel()),
          provider.ChangeNotifierProvider(create: (_) => SplashViewModel()),
          provider.ChangeNotifierProvider(create: (_) => WelcomeViewModel()),
          provider.ChangeNotifierProvider(create: (_) => ConsentViewModel()),
          provider.ChangeNotifierProvider(
            create: (context) =>
                RelationshipViewModel(RelationshipApiService()),
          ),
          provider.ChangeNotifierProvider(
            create: (_) => SessionHistoryViewModel(),
          ),
          provider.ChangeNotifierProvider(create: (_) => OnboardingViewModel()),
          provider.ChangeNotifierProvider(
            create: (_) =>
                NotificationViewModel(apiService: NotificationApiService()),
          ),
          provider.ChangeNotifierProvider(create: (_) => SettingsViewModel()),
          provider.ChangeNotifierProvider(create: (_) => RelayViewModel()),
          provider.ChangeNotifierProvider(create: (_) => EngagementViewModel()),
          provider.ChangeNotifierProvider(create: (_) => GamesViewModel()),
          provider.ChangeNotifierProvider(create: (_) => FaithViewModel()),
          provider.ChangeNotifierProvider(create: (_) => BlissViewModel()),
          provider.ChangeNotifierProvider(create: (_) => TwoTruthsViewModel()),
          provider.ChangeNotifierProvider(create: (_) => CommitmentViewModel()),
          provider.ChangeNotifierProvider(create: (_) => FocusViewModel()),
        ],
        child: const riverpod.ProviderScope(child: MyApp()),
      ),
    ),
  );
}

class MyApp extends StatefulWidget {
  const MyApp({super.key});

  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> with WidgetsBindingObserver {
  final _navigatorKey = GlobalKey<NavigatorState>();
  late AppLinks _appLinks;
  StreamSubscription<Uri>? _linkSubscription;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initDeepLinks();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _linkSubscription?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // Chat media is decrypted by the server and cached in the clear on this
    // device. Leaving the foreground is the moment that stops being covered by
    // the app being open, so the plaintext goes with it — anything still
    // wanted is one fetch away.
    if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.detached) {
      MediaCache.instance.clear();
    }
  }

  Future<void> _initDeepLinks() async {
    _appLinks = AppLinks();

    // Handle incoming links while app is running
    _linkSubscription = _appLinks.uriLinkStream.listen((uri) {
      _handleDeepLink(uri);
    });

    // Handle initial link if app is started from link
    try {
      final initialUri = await _appLinks.getInitialLink();
      if (initialUri != null) {
        _handleDeepLink(initialUri);
      }
    } catch (e) {
      debugPrint('Failed to get initial deep link: $e');
    }
  }

  void _handleDeepLink(Uri uri) {
    if (uri.scheme != 'bliss') return;
    if (uri.host == 'accept-invite') {
      final token = uri.queryParameters['token'];
      if (token != null) {
        _navigatorKey.currentState?.pushNamed(
          '/relationship/accept',
          arguments: token,
        );
      }
    } else if (uri.host == 'reset-password') {
      final token = uri.queryParameters['token'];
      final email = uri.queryParameters['email'];
      if (token != null && email != null) {
        _navigatorKey.currentState?.pushNamed(
          '/reset-password',
          arguments: {'email': email, 'token': token},
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      navigatorKey: _navigatorKey,
      title: 'Bliss',
      theme: AppTheme.lightTheme,
      home: const SplashScreen(),
      debugShowCheckedModeBanner: false,
      // Tapping outside a text field (on empty space) dismisses the keyboard.
      // Interactive widgets consume their own taps, so this only fires when the
      // tap isn't handled elsewhere.
      builder: (context, child) {
        return GestureDetector(
          behavior: HitTestBehavior.translucent,
          onTap: () => FocusManager.instance.primaryFocus?.unfocus(),
          child: child,
        );
      },
      routes: {
        '/consent': (context) => const ConsentDashboardScreen(),
        '/settings': (context) => const SettingsScreen(),
        '/verify-age': (context) => const AgeVerificationScreen(),
        '/signup': (context) => const SignupScreen(),
        '/reset-password': (context) => const NewPasswordScreen(),
        '/relationship/invite': (context) => const InvitePartnerScreen(),
        '/relationship/settings': (context) =>
            const DissolveRelationshipScreen(),
        '/our-story': (context) => const OurStoryScreen(),
        '/safety': (context) => const SafetyResourcesScreen(),
        '/history': (context) => const SessionHistoryScreen(),
        '/notifications': (context) => const NotificationCenterScreen(),
        '/settings/email': (context) => const EmailChangeScreen(),
        '/relay/inbox': (context) => const RelayInboxScreen(),
        '/engagement/daily': (context) => const DailyRitualScreen(),
        '/engagement/goals': (context) => const SharedGoalsScreen(),
        '/engagement/games': (context) => const GamesListScreen(),
        '/engagement/faith': (context) => const FaithScreen(),
        '/engagement/bliss': (context) => const BlissPlanScreen(),
        // The invite notification deep-links here, so this route has to exist
        // before the first invitation is ever sent.
        '/engagement/calendar': (context) => provider.ChangeNotifierProvider(
          create: (_) => CalendarViewModel(),
          child: const CalendarScreen(),
        ),
        '/engagement/two-truths': (context) => const TwoTruthsScreen(),
        '/engagement/commitments': (context) => const CommitmentsScreen(),
        '/engagement/focus': (context) => const FocusScreen(),
        '/onboarding': (context) => const OnboardingFlowScreen(),
        '/onboarding/portrait': (context) => const RelationshipPortraitScreen(),
        '/onboarding/complete': (context) => const OnboardingCompleteScreen(),
        '/chat': (context) {
          final authVM = provider.Provider.of<AuthViewModel>(
            context,
            listen: false,
          );
          final args =
              ModalRoute.of(context)?.settings.arguments
                  as Map<String, dynamic>?;
          return ChatScreen(
            userId: authVM.user?.id ?? 'guest',
            isJointSession: args?['isJoint'] ?? false,
          );
        },
      },
      onGenerateRoute: (settings) {
        if (settings.name == '/relationship/accept') {
          final token = settings.arguments as String?;
          if (token != null) {
            return MaterialPageRoute(
              builder: (context) => AcceptInviteScreen(token: token),
            );
          }
        }
        return null;
      },
    );
  }
}
