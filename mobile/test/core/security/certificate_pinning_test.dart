import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/security/certificate_config.dart';
import 'package:mobile/core/security/pinned_http_client.dart';
import 'package:dio/dio.dart';

void main() {
  group('CertConfig', () {
    test('djangoApiHashes list is non-empty', () {
      expect(CertConfig.djangoApiHashes, isNotEmpty);
    });

    test('fastapiHashes list is non-empty', () {
      expect(CertConfig.fastapiHashes, isNotEmpty);
    });

    test('djangoApiHashes has at least 2 entries (leaf + backup)', () {
      expect(
        CertConfig.djangoApiHashes.length,
        greaterThanOrEqualTo(2),
        reason: 'Must have a primary and at least one backup pin for rotation safety.',
      );
    });

    test('fastapiHashes has at least 2 entries (leaf + backup)', () {
      expect(
        CertConfig.fastapiHashes.length,
        greaterThanOrEqualTo(2),
        reason: 'Must have a primary and at least one backup pin for rotation safety.',
      );
    });

    test('djangoApiHost is a valid non-empty hostname', () {
      expect(CertConfig.djangoApiHost, isNotEmpty);
      expect(CertConfig.djangoApiHost, isNot(contains('localhost')));
    });

    test('fastapiHost is a valid non-empty hostname', () {
      expect(CertConfig.fastapiHost, isNotEmpty);
      expect(CertConfig.fastapiHost, isNot(contains('localhost')));
    });

    test('placeholder pins cause a certificate to be REJECTED', () {
      // The behaviour, not the config value. This used to be a test that
      // printed a warning and passed — so the one thing standing between an
      // unfilled placeholder and a shipped build was a line of stdout inside a
      // 300-test run. It gated nothing.
      //
      // What matters is the direction of the failure. shouldAccept runs as a
      // badCertificateCallback, which fires only for certificates the OS has
      // already refused; returning true overrides that. With placeholders we
      // have no idea what the real certificate looks like, so the only safe
      // answer is no.
      expect(
        PinnedHttpClient.shouldAccept(
          pinnedHashes: const ['REPLACE_WITH_API_PRIMARY_CERT_SPKI_SHA256_BASE64=='],
          certHash: 'anything-at-all',
        ),
        isFalse,
        reason: 'placeholders must fail closed, never open',
      );
    });

    test('a single placeholder among real pins still fails closed', () {
      // Half-finished rotation is the likeliest way this state occurs.
      expect(
        PinnedHttpClient.shouldAccept(
          pinnedHashes: const ['a-real-looking-hash=', 'REPLACE_WITH_BACKUP=='],
          certHash: 'a-real-looking-hash=',
        ),
        isFalse,
      );
    });

    test('an unknown host is rejected', () {
      expect(
        PinnedHttpClient.shouldAccept(pinnedHashes: null, certHash: 'x'),
        isFalse,
      );
    });

    test('a matching pin is accepted and a mismatch is not', () {
      const pins = ['aaa=', 'bbb='];
      expect(
        PinnedHttpClient.shouldAccept(pinnedHashes: pins, certHash: 'bbb='),
        isTrue,
      );
      expect(
        PinnedHttpClient.shouldAccept(pinnedHashes: pins, certHash: 'ccc='),
        isFalse,
      );
    });

    test('an empty pin list is rejected, not treated as "no constraint"', () {
      expect(
        PinnedHttpClient.shouldAccept(pinnedHashes: const [], certHash: 'x'),
        isFalse,
      );
    });

    test('the config still carries placeholders — a release blocker', () {
      // Deliberately informational rather than a hard failure: the code now
      // fails closed, so shipping with placeholders degrades security rather
      // than breaking the app, and blocking every local run on it would just
      // get the test deleted. Recorded here so the state is visible.
      final placeholders = [
        ...CertConfig.djangoApiHashes,
        ...CertConfig.fastapiHashes,
      ].where((h) => h.startsWith('REPLACE_WITH')).length;
      if (placeholders > 0) {
        // ignore: avoid_print
        print(
          'RELEASE BLOCKER: $placeholders of 4 certificate pins are still '
          'placeholders. Certificates the OS rejects will now be refused '
          '(correct), but no pin is actually being enforced. Fill these in '
          'before shipping.',
        );
      }
    });
  });

  group('PinnedHttpClient', () {
    test('create() returns a Dio instance', () {
      // kReleaseMode is false in tests, so we get the plain Dio path.
      final dio = PinnedHttpClient.create();
      expect(dio, isA<Dio>());
    });

    test('debug build does NOT throw on construction', () {
      // In debug mode pinning is skipped — Dio should be created without error.
      expect(() => PinnedHttpClient.create(), returnsNormally);
    });

    test('created Dio respects injected BaseOptions baseUrl', () {
      final options = BaseOptions(baseUrl: 'https://example.com');
      final dio = PinnedHttpClient.create(baseOptions: options);
      expect(dio.options.baseUrl, 'https://example.com');
    });

    test('kReleaseMode flag is false in test environment', () {
      // Asserts the test environment is a debug/profile build so pinning
      // bypass logic above is exercised correctly.
      expect(kReleaseMode, isFalse);
    });
  });
}
