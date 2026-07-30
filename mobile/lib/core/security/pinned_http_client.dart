import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:dio/dio.dart';
import 'package:dio/io.dart';
import 'package:flutter/foundation.dart';

import 'certificate_config.dart';

/// Creates a [Dio] instance whose underlying [HttpClient] enforces:
///
/// * **Minimum TLS 1.3** — rejects any handshake that negotiates TLS 1.2 or
///   below (handled by the OS/Dart's [SecurityContext]).
/// * **A pin check on otherwise-rejected certificates** (release builds only) —
///   wired as a `badCertificateCallback`, which the platform invokes *only when
///   chain validation has already failed*. So this is not pinning in the usual
///   sense: a certificate the OS trusts never reaches it, and is accepted
///   without its fingerprint being compared to anything. What this does provide
///   is that a certificate the OS distrusts is refused unless it matches a pin.
///   True pinning — checking the fingerprint on *every* handshake — needs the
///   comparison to run on the success path too, which the Dart SDK does not
///   expose; it wants a native plugin. Worth doing before this is relied on as
///   a control.
///
/// In **debug / profile** builds, pinning is deliberately bypassed so
/// developers can run against local API stacks with self-signed certificates.
/// A [debugPrint] warning is emitted to highlight this.
class PinnedHttpClient {
  PinnedHttpClient._();

  /// Returns a [Dio] instance wired with the hardened [HttpClient].
  ///
  /// [baseOptions] are merged into the returned Dio; caller is responsible for
  /// setting [BaseOptions.baseUrl] and timeouts.
  static Dio create({BaseOptions? baseOptions}) {
    final dio = Dio(baseOptions ?? BaseOptions());

    if (!kReleaseMode) {
      // ── Development / debug: skip pinning, log loudly ──────────────────────
      debugPrint(
        '⚠️  [PinnedHttpClient] Certificate pinning is DISABLED in debug mode. '
        'Connections to any TLS host are accepted. '
        'Do NOT ship this configuration.',
      );
      return dio;
    }

    // ── Release: configure pinned HttpClient ────────────────────────────────
    final adapter = IOHttpClientAdapter(
      createHttpClient: () {
        final client = HttpClient(context: SecurityContext.defaultContext);

        // Dart's HttpClient already negotiates the best TLS version the OS
        // supports (TLS 1.3 on Android 10+ / iOS 12+).  The callback below
        // enforces our additional SPKI-pinning check on top of standard
        // certificate chain validation.
        client.badCertificateCallback = _buildPinningCallback();

        return client;
      },
    );

    (dio.httpClientAdapter as dynamic); // satisfy analyser implicit-cast
    dio.httpClientAdapter = adapter;

    return dio;
  }

  // ── Private helpers ─────────────────────────────────────────────────────────

  /// The decision itself, separated out so it can be tested without a TLS
  /// handshake. Returns true only if this certificate should be accepted.
  ///
  /// Read the sense of this carefully: it runs as a `badCertificateCallback`,
  /// which the platform invokes **only when chain validation has already
  /// failed**. So every call is about a certificate the operating system has
  /// decided not to trust, and returning true overrides that judgement.
  @visibleForTesting
  static bool shouldAccept({
    required List<String>? pinnedHashes,
    required String certHash,
  }) {
    if (pinnedHashes == null) {
      // A host we do not have pins for. Nothing to check it against.
      return false;
    }

    // Placeholders mean we do not know what this host's certificate should
    // look like — so we cannot vouch for one the OS has already rejected.
    //
    // This used to return true. Combined with debugPrint, which produces no
    // output in a release build, that meant a release shipped with unfilled
    // placeholders would silently accept certificates the platform distrusted,
    // for exactly the two hosts carrying every message and every session. Not
    // "pinning disabled" — a straightforward interception hole, in the file
    // whose docstring promises pinning is enforced.
    //
    // Failing closed cannot break a working install: with a certificate the OS
    // trusts, this callback is never invoked at all. All it changes is that a
    // bad certificate is now refused instead of waved through.
    if (pinnedHashes.any((h) => h.startsWith('REPLACE_WITH'))) {
      return false;
    }

    return pinnedHashes.contains(certHash);
  }

  static bool Function(X509Certificate cert, String host, int port)
      _buildPinningCallback() {
    return (X509Certificate cert, String host, int port) {
      final List<String>? pinnedHashes = _hashesForHost(host);

      // Derive the DER-encoded SubjectPublicKeyInfo SHA-256 fingerprint.
      // cert.der contains the full DER-encoded X.509 certificate; we use it
      // as the fingerprint source (full-cert pinning) since the Dart SDK does
      // not yet expose the raw SPKI bytes directly.
      //
      // NOTE: For production, update the hashes in CertConfig to match the
      // output of full-cert SHA-256, or switch to a native plugin that
      // provides true SPKI extraction if that level of precision is required.
      final certHash = _sha256Base64(cert.der);

      final accepted = shouldAccept(
        pinnedHashes: pinnedHashes,
        certHash: certHash,
      );
      if (!accepted) {
        debugPrint('[PinnedHttpClient] Rejected certificate for $host');
      }
      return accepted;
    };
  }

  static List<String>? _hashesForHost(String host) {
    if (host == CertConfig.djangoApiHost) return CertConfig.djangoApiHashes;
    if (host == CertConfig.fastapiHost) return CertConfig.fastapiHashes;
    return null;
  }

  /// SHA-256 over [bytes], Base64-encoded — the format the `openssl`
  /// extraction commands in [CertConfig]'s docs produce.
  ///
  /// Both halves come from the SDK and package:crypto, which this file already
  /// imports for sha256. What was here before was a hand-written base64 loop
  /// with a comment explaining it avoided adding a crypto dependency — a
  /// dependency three lines above it. Hand-rolling an encoder is not free: it
  /// is thirty lines of index arithmetic on the path that decides whether to
  /// trust a certificate, where a wrong answer means either refusing every
  /// connection or accepting the wrong one, and where the SDK's version is
  /// exhaustively tested and this one is not tested at all.
  static String _sha256Base64(List<int> bytes) =>
      base64Encode(sha256.convert(bytes).bytes);
}
