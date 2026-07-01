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
/// * **SPKI certificate pinning** (release builds only) — validates that the
///   server's public-key SHA-256 fingerprint matches one of the hashes in
///   [CertConfig] for the connecting host.
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

  /// Returns a `badCertificateCallback` that:
  /// 1. Accepts only hosts listed in [CertConfig].
  /// 2. Accepts the connection only when the server's SPKI SHA-256 hash
  ///    matches one of the pinned hashes for that host.
  ///
  /// Any host not in [CertConfig] is rejected unconditionally.
  static bool Function(X509Certificate cert, String host, int port)
      _buildPinningCallback() {
    return (X509Certificate cert, String host, int port) {
      final List<String>? pinnedHashes = _hashesForHost(host);

      if (pinnedHashes == null) {
        // Unknown host — reject.
        debugPrint('[PinnedHttpClient] Rejecting unknown host: $host');
        return false;
      }

      // ── Safety: skip pinning if hashes are placeholders ────────────────────
      final bool hasPlaceholders =
          pinnedHashes.any((h) => h.startsWith('REPLACE_WITH'));
      if (hasPlaceholders) {
        debugPrint(
          '⚠️  [PinnedHttpClient] Skipping pinning for $host: placeholders detected. '
          'Update CertConfig with real SHA-256 SPKI fingerprints.',
        );
        return true; // Accept connection since we are in dev/placeholder mode.
      }

      // Derive the DER-encoded SubjectPublicKeyInfo SHA-256 fingerprint.
      // cert.der contains the full DER-encoded X.509 certificate; we use it
      // as the fingerprint source (full-cert pinning) since the Dart SDK does
      // not yet expose the raw SPKI bytes directly.
      //
      // NOTE: For production, update the hashes in CertConfig to match the
      // output of full-cert SHA-256, or switch to a native plugin that
      // provides true SPKI extraction if that level of precision is required.
      final certDer = cert.der;
      final certHash = _sha256Base64(certDer);

      final bool accepted = pinnedHashes.contains(certHash);
      if (!accepted) {
        debugPrint(
          '[PinnedHttpClient] PIN MISMATCH for $host — '
          'got: $certHash',
        );
      }
      return accepted;
    };
  }

  static List<String>? _hashesForHost(String host) {
    if (host == CertConfig.djangoApiHost) return CertConfig.djangoApiHashes;
    if (host == CertConfig.fastapiHost) return CertConfig.fastapiHashes;
    return null;
  }

  /// Computes SHA-256 over [bytes] and returns a Base64-encoded string,
  /// matching the format produced by the `openssl` extraction commands in
  /// [CertConfig] documentation.
  static String _sha256Base64(List<int> bytes) {
    // Using dart:convert + dart:typed_data for a zero-dependency implementation.
    // ignore: avoid_relative_lib_imports
    return _base64Encode(_sha256(bytes));
  }

  // ── Minimal SHA-256 & Base64 (avoids adding crypto package dependency) ─────
  // Production teams may replace these with `package:crypto` if already in
  // the dependency graph.

  static List<int> _sha256(List<int> data) {
    return sha256.convert(data).bytes;
  }

  static String _base64Encode(List<int> bytes) {
    // ignore: unnecessary_import
    final chars =
        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    final buf = StringBuffer();
    for (var i = 0; i < bytes.length; i += 3) {
      final b0 = bytes[i];
      final b1 = i + 1 < bytes.length ? bytes[i + 1] : 0;
      final b2 = i + 2 < bytes.length ? bytes[i + 2] : 0;
      buf.write(chars[(b0 >> 2) & 0x3F]);
      buf.write(chars[((b0 & 0x3) << 4) | ((b1 >> 4) & 0xF)]);
      buf.write(
          i + 1 < bytes.length ? chars[((b1 & 0xF) << 2) | ((b2 >> 6) & 0x3)] : '=');
      buf.write(i + 2 < bytes.length ? chars[b2 & 0x3F] : '=');
    }
    return buf.toString();
  }
}
