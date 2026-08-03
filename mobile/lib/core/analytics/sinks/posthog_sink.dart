/// PostHog.
///
/// Preferred of the two destinations for this product, for a reason that is
/// about jurisdiction rather than features: PostHog can be pointed at EU
/// hosting or self-hosted entirely, and this app carries relationship and
/// mental-health signal from users who may be in the EU. `POSTHOG_HOST` is a
/// required dart-define rather than defaulting to US cloud, so choosing a
/// region is a deliberate act at build time and not something that happens by
/// forgetting.
library;

import 'package:posthog_flutter/posthog_flutter.dart';

import 'package:mobile/core/analytics/analytics_event.dart';
import 'package:mobile/core/analytics/analytics_sink.dart';

class PostHogSink implements AnalyticsSink {
  static const _apiKey = String.fromEnvironment('POSTHOG_API_KEY');
  static const _host = String.fromEnvironment('POSTHOG_HOST');

  @override
  String get id => 'posthog';

  /// Both, not either. A key with no host would silently fall back to the
  /// vendor's default region, which is the decision this sink exists to make
  /// explicit.
  @override
  bool get isReady => _apiKey.isNotEmpty && _host.isNotEmpty;

  @override
  Future<void> send(AnalyticsEvent event) =>
      Posthog().capture(eventName: event.name, properties: event.properties);

  @override
  Future<void> identify(String pseudonymousId) =>
      Posthog().identify(userId: pseudonymousId);

  @override
  Future<void> reset() => Posthog().reset();
}
