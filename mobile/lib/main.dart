import 'package:flutter/material.dart';
import 'package:provider/provider.dart' as provider;
import 'package:flutter_riverpod/flutter_riverpod.dart' as riverpod hide Provider;
import 'package:sentry_flutter/sentry_flutter.dart';
import 'dart:async';
import 'package:app_links/app_links.dart';
import 'package:mobile/features/chat/chat_screen.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/features/auth/viewmodels/splash_viewmodel.dart';
import 'package:mobile/features/auth/viewmodels/welcome_viewmodel.dart';
import 'package:mobile/features/auth/views/splash_screen.dart';
import 'package:mobile/features/auth/views/age_verification_screen.dart';
import 'package:mobile/features/auth/views/signup_screen.dart';
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
import 'package:mobile/features/settings/settings_screen.dart';
import 'package:mobile/features/settings/email_change_screen.dart';
import 'package:mobile/features/settings/about_screen.dart';
import 'package:mobile/features/onboarding/onboarding_viewmodel.dart';
import 'package:mobile/features/onboarding/onboarding_flow_screen.dart';
import 'package:mobile/features/onboarding/screens/onboarding_complete_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await SentryFlutter.init(
    (options) {
      options.dsn =
          'https://04ae4d1e86508070b37d43e4ad62141d@o4511191944593408.ingest.us.sentry.io/4511191967072256';
      options.tracesSampleRate = 1.0;
      // ignore: experimental_member_use
      options.profilesSampleRate = 1.0;
    },
    appRunner: () => runApp(
      provider.MultiProvider(
        providers: [
          provider.ChangeNotifierProvider(create: (_) => AuthViewModel()),
          provider.ChangeNotifierProvider(create: (_) => SplashViewModel()),
          provider.ChangeNotifierProvider(create: (_) => WelcomeViewModel()),
          provider.ChangeNotifierProvider(create: (_) => ConsentViewModel()),
          provider.ChangeNotifierProvider(
            create: (context) => RelationshipViewModel(
              RelationshipApiService(),
            ),
          ),
          provider.ChangeNotifierProvider(create: (_) => SessionHistoryViewModel()),
          provider.ChangeNotifierProvider(create: (_) => OnboardingViewModel()),
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

class _MyAppState extends State<MyApp> {
  final _navigatorKey = GlobalKey<NavigatorState>();
  late AppLinks _appLinks;
  StreamSubscription<Uri>? _linkSubscription;

  @override
  void initState() {
    super.initState();
    _initDeepLinks();
  }

  @override
  void dispose() {
    _linkSubscription?.cancel();
    super.dispose();
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
    if (uri.scheme == 'relationshipai' && uri.host == 'accept-invite') {
      final token = uri.queryParameters['token'];
      if (token != null) {
        _navigatorKey.currentState?.pushNamed(
          '/relationship/accept',
          arguments: token,
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      navigatorKey: _navigatorKey,
      title: 'RelationshipAI',
      theme: AppTheme.lightTheme,
      home: const SplashScreen(),
      debugShowCheckedModeBanner: false,
      routes: {
        '/consent': (context) => const ConsentDashboardScreen(),
        '/verify-age': (context) => const AgeVerificationScreen(),
        '/signup': (context) => const SignupScreen(),
        '/relationship/invite': (context) => const InvitePartnerScreen(),
        '/relationship/settings': (context) => const DissolveRelationshipScreen(),
        '/our-story': (context) => const OurStoryScreen(),
        '/safety': (context) => const SafetyResourcesScreen(),
        '/history': (context) => const SessionHistoryScreen(),
        '/onboarding': (context) => const OnboardingFlowScreen(),
        '/onboarding/complete': (context) => const OnboardingCompleteScreen(),
        '/chat': (context) {
          final authVM = provider.Provider.of<AuthViewModel>(context, listen: false);
          final args = ModalRoute.of(context)?.settings.arguments as Map<String, dynamic>?;
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
