/// The one way to record anything about how this product is used.
///
/// The assessment's finding was that Sentry catches crashes and *nothing*
/// catches behaviour — so activation, retention and the invite-acceptance rate
/// are all unknowable, and there is no way to tell which of twenty-one feature
/// areas anyone opens. This is the fix, built to the same standard as the rest
/// of the privacy machinery rather than bolted on beside it.
///
/// Three properties, in order of how much they matter:
///
/// **It cannot carry content.** See `analytics_event.dart`: the taxonomy is a
/// sealed set of typed constructors and there is no string-keyed `track`. This
/// is the guarantee that survives contact with a hurried afternoon.
///
/// **It is off until consent is known.** `_consented` starts null, meaning
/// *not yet answered*, and events emitted before that are dropped rather than
/// buffered. Buffering would mean a user who declines still had their first
/// session recorded, which is the kind of technically-defensible behaviour this
/// product has consistently refused elsewhere.
///
/// **It cannot break a screen.** Every send is fire-and-forget and every sink
/// failure is swallowed. An analytics outage that takes down onboarding would
/// be a strictly worse outcome than having no analytics, which is the state we
/// are coming from.
library;

import 'dart:async';

import 'package:flutter/foundation.dart';

import 'package:mobile/core/analytics/analytics_event.dart';
import 'package:mobile/core/analytics/analytics_sink.dart';

class Analytics {
  Analytics({List<AnalyticsSink>? sinks}) : _sinks = sinks ?? const [];

  final List<AnalyticsSink> _sinks;

  /// null = the user has not been asked yet. Deliberately tri-state: "not
  /// asked" and "said no" must not collapse into one value, because they call
  /// for different behaviour the moment consent *is* granted.
  bool? _consented;

  bool? get consented => _consented;

  /// True only when someone has actively agreed. `null` is not consent.
  bool get isRecording => _consented == true;

  /// Record the user's decision.
  ///
  /// Withdrawal resets every sink, which is the difference between "stop
  /// collecting" and "forget the person" — the second is what someone who
  /// turns this off is actually asking for.
  Future<void> setConsent(bool granted) async {
    final withdrawing = _consented == true && !granted;
    _consented = granted;
    if (withdrawing) {
      await _forEachSink((sink) => sink.reset());
    }
  }

  /// Attach a pseudonymous id to subsequent events.
  ///
  /// The caller is responsible for this being pseudonymous — an opaque user id,
  /// never an email and never a relationship id. Passing a relationship id
  /// would put both partners under one analytics key and make the couple graph
  /// readable from a dashboard, undoing on the client what `boundary.py`
  /// enforces on the server.
  Future<void> identify(String pseudonymousId) async {
    if (!isRecording) return;
    await _forEachSink((sink) => sink.identify(pseudonymousId));
  }

  /// Drop the current identity. Sign-out.
  Future<void> reset() async => _forEachSink((sink) => sink.reset());

  /// Record an event. Never throws, never awaits the network on a UI path.
  void record(AnalyticsEvent event) {
    if (!isRecording) return;
    unawaited(_forEachSink((sink) => sink.send(event)));
  }

  Future<void> _forEachSink(Future<void> Function(AnalyticsSink) action) async {
    for (final sink in _sinks) {
      if (!sink.isReady) continue;
      try {
        await action(sink);
      } catch (error) {
        // Swallowed on purpose, and logged only in debug. A sink that is down,
        // rate-limited or misconfigured must not surface to the person using
        // the app, and must not stop the other sinks from receiving the event.
        if (kDebugMode) {
          debugPrint('analytics sink ${sink.id} failed: $error');
        }
      }
    }
  }
}
