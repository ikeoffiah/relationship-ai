/// Google Analytics — which, on a Flutter app, means Firebase Analytics (GA4).
///
/// There is no separate "Google Analytics SDK" for mobile; GA4 property data
/// arrives via Firebase. That is convenient here because Firebase is already
/// wired for push (project `bliss-d7721`), so this adds a dependency rather
/// than a vendor relationship.
///
/// One thing worth knowing rather than discovering: GA4's legal position for EU
/// users has been repeatedly contested since Schrems II, and unlike PostHog it
/// offers no EU-hosted or self-hosted option. For a product carrying
/// relationship and mental-health signal that is a real consideration, and it
/// is why `PostHogSink` is treated as the primary of the two. Nothing here
/// sends content — see `analytics_event.dart` — which limits the exposure, but
/// it does not remove the question.
library;

import 'package:firebase_analytics/firebase_analytics.dart';

import 'package:mobile/core/analytics/analytics_event.dart';
import 'package:mobile/core/analytics/analytics_sink.dart';

class FirebaseAnalyticsSink implements AnalyticsSink {
  FirebaseAnalyticsSink({FirebaseAnalytics? analytics, bool enabled = true})
    : _analytics = analytics,
      _enabled = enabled;

  final FirebaseAnalytics? _analytics;
  final bool _enabled;

  FirebaseAnalytics get _instance => _analytics ?? FirebaseAnalytics.instance;

  @override
  String get id => 'firebase';

  /// Gated by a dart-define so a build can ship with PostHog only. Given the
  /// jurisdictional note above, being able to turn this one off without a code
  /// change is worth the flag.
  @override
  bool get isReady =>
      _enabled && const bool.fromEnvironment('GA_ENABLED', defaultValue: false);

  @override
  Future<void> send(AnalyticsEvent event) => _instance.logEvent(
    name: event.name,
    parameters: event.properties,
  );

  @override
  Future<void> identify(String pseudonymousId) =>
      _instance.setUserId(id: pseudonymousId);

  @override
  Future<void> reset() => _instance.resetAnalyticsData();
}
