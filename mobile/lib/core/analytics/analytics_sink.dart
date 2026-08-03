/// Where events go. One interface, so the facade does not know or care how
/// many destinations exist, and so tests can assert on a list instead of a
/// network.
library;

import 'package:mobile/core/analytics/analytics_event.dart';

abstract class AnalyticsSink {
  /// A short name for logs and tests.
  String get id;

  /// Whether this sink is configured. An unconfigured sink is skipped rather
  /// than throwing: a missing key is a deployment state, not a crash, and an
  /// analytics failure must never be able to take a screen down.
  bool get isReady;

  Future<void> send(AnalyticsEvent event);

  /// Associate subsequent events with a pseudonymous id.
  ///
  /// Never an email, never a name, never a relationship id — see the header of
  /// `analytics_event.dart` on why the couple graph must not be reconstructable
  /// from an analytics account.
  Future<void> identify(String pseudonymousId);

  /// Forget the current person. Called on sign-out and on consent withdrawal.
  Future<void> reset();
}

/// Collects events in memory. Used by tests, and as the default so that a build
/// with no keys configured still exercises every call site.
class RecordingSink implements AnalyticsSink {
  final List<AnalyticsEvent> events = [];
  final List<String> identities = [];
  int resets = 0;

  @override
  String get id => 'recording';

  @override
  bool get isReady => true;

  @override
  Future<void> send(AnalyticsEvent event) async => events.add(event);

  @override
  Future<void> identify(String pseudonymousId) async =>
      identities.add(pseudonymousId);

  @override
  Future<void> reset() async {
    resets++;
    identities.clear();
  }
}
