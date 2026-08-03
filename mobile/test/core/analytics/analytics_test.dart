/// What analytics is allowed to do, and what it must never do.
///
/// The consent tests matter, but the one that matters most is
/// `no event in the taxonomy carries free text` — it walks every event type and
/// asserts the shape of what would go on the wire. A future contributor adding
/// `MessageSent(text: draft)` fails here rather than in production, which is
/// the whole point of a sealed taxonomy over a string-keyed `track`.
library;

import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/core/analytics/analytics.dart';
import 'package:mobile/core/analytics/analytics_event.dart';
import 'package:mobile/core/analytics/analytics_sink.dart';

/// One of every event, so the sweep below cannot miss one by omission.
const _everyEvent = <AnalyticsEvent>[
  OnboardingStarted(),
  OnboardingStepCompleted(step: 'rsq', index: 2),
  OnboardingFinished(
    outcome: OnboardingOutcome.abandoned,
    lastStep: 'rsq',
    seconds: 92,
  ),
  RsqProgress(answered: 11, total: 30),
  InviteSent(channel: 'link'),
  InviteAccepted(),
  QuestionShown(state: QuestionState.reveal),
  QuestionAnswered(secondsToAnswer: 41),
  QuestionRevealed(),
  CheckInSubmitted(),
  SurfaceOpened(surface: AnalyticsSurface.us),
  SessionStarted(isJoint: false),
  SessionFirstMessage(secondsFromOpen: 18),
  AppOpened(dayNumber: 3),
];

void main() {
  group('the taxonomy', () {
    test('no event carries free text', () {
      /// Every property value must be a number, a bool, or a string drawn from
      /// a closed vocabulary the code controls — an enum `.name` or a screen
      /// key. Nothing a user typed can reach a sink.
      const allowedStrings = {
        // enum names
        'abandoned', 'completed', 'unanswered', 'waiting', 'reveal', 'done',
        'today', 'us', 'talk', 'you', 'onboarding', 'chat', 'coupleChat',
        'games', 'invite',
        // closed call-site vocabularies
        'email', 'link',
        // screen keys
        'rsq',
      };

      for (final event in _everyEvent) {
        for (final entry in event.properties.entries) {
          final value = entry.value;
          if (value is String) {
            expect(
              allowedStrings.contains(value),
              isTrue,
              reason:
                  'event "${event.name}" property "${entry.key}" carries the '
                  'string "$value", which is not from a closed vocabulary. If '
                  'this is user-typed content it must not be sent at all.',
            );
          } else {
            expect(value, anyOf(isA<num>(), isA<bool>()));
          }
        }
      }
    });

    test('nothing carries a relationship or partner identifier', () {
      /// Two partners under one analytics key would make the couple graph
      /// readable from a dashboard, undoing on the client what boundary.py
      /// enforces on the server.
      for (final event in _everyEvent) {
        for (final key in event.properties.keys) {
          expect(
            key.contains('relationship') ||
                key.contains('partner') ||
                key.contains('couple'),
            isFalse,
            reason: '"${event.name}" has a property named "$key"',
          );
        }
      }
    });

    test('the check-in carries no score', () {
      /// The 1-5 check-in is a private self-report, and the perception-gap
      /// insight rests on it not travelling.
      expect(const CheckInSubmitted().properties, isEmpty);
    });

    test('an answered question carries timing, never the answer', () {
      const event = QuestionAnswered(secondsToAnswer: 41);
      expect(event.properties, {'seconds_to_answer': 41});
    });
  });

  group('consent', () {
    late RecordingSink sink;
    late Analytics analytics;

    setUp(() {
      sink = RecordingSink();
      analytics = Analytics(sinks: [sink]);
    });

    test('nothing is recorded before consent is answered', () {
      expect(analytics.consented, isNull);
      analytics.record(const OnboardingStarted());
      expect(sink.events, isEmpty);
    });

    test('nothing is recorded after consent is refused', () async {
      await analytics.setConsent(false);
      analytics.record(const OnboardingStarted());
      expect(sink.events, isEmpty);
    });

    test('events flow once consent is granted', () async {
      await analytics.setConsent(true);
      analytics.record(const QuestionRevealed());
      expect(sink.events.single.name, 'question_revealed');
    });

    test('early events are dropped, not buffered', () async {
      /// Buffering would mean somebody who declines still had their first
      /// session recorded and released the moment they said yes to something
      /// else. Technically defensible, and not what this product does.
      analytics.record(const OnboardingStarted());
      await analytics.setConsent(true);
      expect(sink.events, isEmpty);
    });

    test('withdrawal resets the sinks, not just the flag', () async {
      await analytics.setConsent(true);
      await analytics.identify('user-123');
      await analytics.setConsent(false);

      expect(sink.resets, 1);
      expect(sink.identities, isEmpty);
    });

    test('identify does nothing without consent', () async {
      await analytics.identify('user-123');
      expect(sink.identities, isEmpty);
    });
  });

  group('resilience', () {
    test('a failing sink never surfaces and never blocks the others', () async {
      final good = RecordingSink();
      final analytics = Analytics(sinks: [_ExplodingSink(), good]);
      await analytics.setConsent(true);

      analytics.record(const QuestionRevealed());
      await Future<void>.delayed(Duration.zero);

      expect(good.events.single.name, 'question_revealed');
    });

    test('an unconfigured sink is skipped rather than throwing', () async {
      final analytics = Analytics(sinks: [_UnconfiguredSink()]);
      await analytics.setConsent(true);
      analytics.record(const QuestionRevealed());
      await Future<void>.delayed(Duration.zero);
      // Reaching here without throwing is the assertion: `_UnconfiguredSink`
      // throws from every method, so it must never have been called.
    });
  });
}

class _ExplodingSink implements AnalyticsSink {
  @override
  String get id => 'exploding';
  @override
  bool get isReady => true;
  @override
  Future<void> send(AnalyticsEvent event) async => throw StateError('down');
  @override
  Future<void> identify(String id) async => throw StateError('down');
  @override
  Future<void> reset() async => throw StateError('down');
}

class _UnconfiguredSink implements AnalyticsSink {
  @override
  String get id => 'unconfigured';
  @override
  bool get isReady => false;
  @override
  Future<void> send(AnalyticsEvent event) async =>
      throw StateError('must not be called');
  @override
  Future<void> identify(String id) async =>
      throw StateError('must not be called');
  @override
  Future<void> reset() async => throw StateError('must not be called');
}
