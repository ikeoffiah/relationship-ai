import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/features/settings/about_screen.dart';
import 'package:mobile/features/settings/legal_document_screen.dart';
import 'package:mobile/features/settings/legal_documents.dart';

/// About, and the two documents behind it.
///
/// The assertions worth having here are not "the text exists". They are about
/// the claims: that the policy never says end-to-end encrypted, that it does
/// say Bliss can read the thread, and that no placeholder reaches a build that
/// is meant to be published. A privacy policy is code that makes promises, and
/// the promises are the part that can go wrong silently.
void main() {
  group('About screen', () {
    Future<void> pump(WidgetTester tester) async {
      // Tall enough that the whole screen is laid out at once. ListView builds
      // lazily, so at phone height the links below the fold do not exist yet
      // and a finder cannot see them — scrolling to each one in turn is a lot
      // of ceremony for an assertion about which links are offered.
      tester.view.physicalSize = const Size(600, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);

      await tester.pumpWidget(const MaterialApp(home: AboutScreen()));
      await tester.pump();
    }

    testWidgets('the placeholder acknowledgements are gone', (tester) async {
      // "• Flutter • Provider • Riverpod • Sentry • …" shipped as About's
      // largest section. Nobody opens About to learn the state-management
      // choice, and the trailing ellipsis gave away that it was never written.
      await pump(tester);
      expect(find.textContaining('Acknowledgement'), findsNothing);
      expect(find.textContaining('Riverpod'), findsNothing);
      expect(find.textContaining('Provider'), findsNothing);
    });

    testWidgets('it says Bliss is not a therapist', (tester) async {
      await pump(tester);
      expect(find.textContaining('not a therapist'), findsWidgets);
    });

    testWidgets('it says Bliss can read the conversation', (tester) async {
      // The thing people most often assume the other way about an app like
      // this. It belongs on the screen, not only in the policy.
      await pump(tester);
      expect(find.textContaining('can read your conversation'), findsWidgets);
    });

    testWidgets('it offers both documents and a route to support', (
      tester,
    ) async {
      await pump(tester);
      expect(find.text('Terms of Service'), findsOneWidget);
      expect(find.text('Privacy Policy'), findsOneWidget);
      expect(find.text('Get support now'), findsOneWidget);
    });

    testWidgets('tapping Privacy Policy opens it', (tester) async {
      await pump(tester);
      await tester.tap(find.text('Privacy Policy'));
      await tester.pumpAndSettle();
      expect(find.byType(LegalDocumentScreen), findsOneWidget);
      expect(find.textContaining('not end-to-end'), findsWidgets);
    });
  });

  group('the documents themselves', () {
    final documents = [termsOfService, privacyPolicy];

    test('neither is empty, and every section has a body', () {
      for (final doc in documents) {
        expect(doc.sections, isNotEmpty, reason: doc.title);
        for (final section in doc.sections) {
          expect(section.heading.trim(), isNotEmpty);
          // Contact is an address and an email; terseness is correct there.
          // Everywhere else, a section short enough to fit on one line is a
          // stub rather than a clause.
          final floor = section.heading == 'Contact' ? 20 : 80;
          expect(
            section.body.trim().length,
            greaterThan(floor),
            reason: '${doc.title} — "${section.heading}" is a stub',
          );
        }
      }
    });

    test('the privacy policy never claims end-to-end encryption', () {
      // It is not, and the whole assistance layer depends on it not being.
      // Claiming otherwise would be the single most consequential untrue
      // sentence this app could contain.
      final text = privacyPolicy.sections
          .map((s) => '${s.heading} ${s.body}')
          .join(' ')
          .toLowerCase();
      // A substring ban was wrong twice over: "it is not end-to-end
      // encrypted" contains the phrase, and so does the true general statement
      // that an end-to-end encrypted product cannot coach a conversation it
      // cannot see. What must never appear is the phrase used affirmatively
      // *about this app*, so those are what the test names.
      for (final claim in [
        'is end-to-end encrypted',
        'are end-to-end encrypted',
        'we use end-to-end',
        'fully end-to-end',
      ]) {
        expect(
          text.contains(claim),
          isFalse,
          reason: 'the policy must never claim "$claim"',
        );
      }
      expect(text.contains('not end-to-end'), isTrue);
    });

    test('the privacy policy states that Bliss can read messages', () {
      final text = privacyPolicy.sections
          .map((s) => s.body)
          .join(' ')
          .toLowerCase();
      expect(text.contains('bliss can read'), isTrue);
    });

    test('the terms lead with the safety limits', () {
      // Not buried at section nine. Someone who reads one heading should learn
      // that this is not therapy and cannot handle an emergency.
      expect(termsOfService.sections.first.heading.toLowerCase(),
          contains('not therapy'));
      expect(termsOfService.sections.first.body.toLowerCase(),
          contains('emergency'));
    });

    test('the terms say the crisis check is not a safety net', () {
      final text = termsOfService.sections
          .map((s) => s.body)
          .join(' ')
          .toLowerCase();
      expect(text.contains('does not contact emergency services'), isTrue);
      expect(text.contains('do not rely on bliss to raise an alarm'), isTrue);
    });

    test('nothing user-facing says relationshipai', () {
      // "relationshipai" is the project's code name. Bliss is a product of
      // owjar.co, and a contract naming the wrong party is not a cosmetic
      // problem.
      final text = [
        termsOfService.preamble,
        privacyPolicy.preamble,
        ...termsOfService.sections.map((s) => '${s.heading} ${s.body}'),
        ...privacyPolicy.sections.map((s) => '${s.heading} ${s.body}'),
      ].join(' ').toLowerCase();
      expect(text.contains('relationshipai'), isFalse);
      expect(text.contains('owjar'), isTrue);
    });

    test('the policy lists the processors that actually receive data', () {
      // If this list drifts from reality it stops being a disclosure and
      // becomes a misstatement.
      final text = privacyPolicy.sections.map((s) => s.body).join(' ');
      for (final processor in ['OpenAI', 'Firebase', 'Sentry', 'LiveKit']) {
        expect(text, contains(processor));
      }
    });

    test('unfilled placeholders are findable, and there are none unaccounted for', () {
      // Deliberately a census rather than a ban. These cannot be filled by me —
      // an invented legal entity in a contract is worse than a visible gap —
      // so the test records exactly which remain, and fails if a new one
      // appears or an expected one silently vanishes.
      final text = [
        termsOfService.preamble,
        privacyPolicy.preamble,
        ...termsOfService.sections.map((s) => s.body),
        ...privacyPolicy.sections.map((s) => s.body),
      ].join(' ');

      final found = RegExp(r'\[[A-Z ]+\]')
          .allMatches(text)
          .map((m) => m.group(0)!)
          .toSet();

      expect(
        found,
        {
          '[REGISTERED ENTITY NAME]',
          '[JURISDICTION]',
          '[GOVERNING LAW]',
          '[RETENTION PERIOD]',
          '[AUDIT LOG RETENTION PERIOD]',
        },
        reason:
            'These five need real values before publishing. If this failed, '
            'either a new placeholder was added or one was filled in — update '
            'this set either way.',
      );
    });
  });
}
