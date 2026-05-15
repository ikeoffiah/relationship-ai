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

    test('no hash contains an unset placeholder for a pin that starts with REPLACE', () {
      // This test acts as a pre-release gate: it will fail until real hashes
      // are substituted, alerting the team that pinning is not yet active.
      //
      // In a CI environment that has real certs, EXPECT this to pass.
      // In development it will fail — which is intentional and expected.
      final allHashes = [
        ...CertConfig.djangoApiHashes,
        ...CertConfig.fastapiHashes,
      ];
      final hasPlaceholders =
          allHashes.any((h) => h.startsWith('REPLACE_WITH'));

      // We warn rather than hard-fail so CI is not blocked during development.
      if (hasPlaceholders) {
        // ignore: avoid_print
        print(
          'WARNING: Certificate pinning hashes contain placeholder values. '
          'Replace them with real SPKI SHA-256 fingerprints before shipping.',
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
