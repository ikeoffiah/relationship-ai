/// Certificate pinning configuration for RelationshipAI API hosts.
///
/// IMPORTANT: Replace the placeholder hashes before a production release.
///
/// To generate the SHA-256 SPKI hash for a certificate, run:
/// ```sh
/// openssl x509 -in cert.pem -pubkey -noout \
///   | openssl pkey -pubin -outform DER \
///   | openssl dgst -sha256 -binary \
///   | base64
/// ```
///
/// Or against a live host:
/// ```sh
/// openssl s_client -connect api.relationshipai.com:443 2>/dev/null \
///   | openssl x509 -pubkey -noout \
///   | openssl pkey -pubin -outform DER \
///   | openssl dgst -sha256 -binary \
///   | base64
/// ```
///
/// Always maintain at least ONE backup hash (e.g., your CA's public key)
/// so that certificate rotation does not cause a production outage.
class CertConfig {
  CertConfig._();

  // ── Host names ──────────────────────────────────────────────────────────────
  //
  // Production hosts are the defaults. For local development, override them at
  // build time with --dart-define (no code change, production unaffected):
  //
  //   flutter run \
  //     --dart-define=API_HOST=10.0.2.2:8000 \   # Django  (Android emulator → host)
  //     --dart-define=WS_HOST=10.0.2.2:8001 \     # FastAPI
  //     --dart-define=API_SCHEME=http             # local backend is plain HTTP
  //
  // (iOS simulator uses localhost:8000/8001; a physical device uses your Mac's
  // LAN IP.) Certificate pinning is already disabled in debug builds.

  static const String _envApiHost = String.fromEnvironment('API_HOST');
  static const String _envWsHost = String.fromEnvironment('WS_HOST');
  static const String _envScheme =
      String.fromEnvironment('API_SCHEME', defaultValue: 'https');

  /// Primary REST / Django API host.
  static String get djangoApiHost =>
      _envApiHost.isEmpty ? 'api.relationshipai.com' : _envApiHost;

  /// WebSocket / FastAPI host.
  static String get fastapiHost =>
      _envWsHost.isEmpty ? 'ws.relationshipai.com' : _envWsHost;

  /// URL scheme (https in production, http for a local backend).
  static String get scheme => _envScheme;

  /// Fully-qualified base URLs, scheme included.
  static String get djangoBaseUrl => '$scheme://$djangoApiHost';
  static String get fastapiBaseUrl => '$scheme://$fastapiHost';

  // ── Pinned SPKI SHA-256 fingerprints ────────────────────────────────────────
  //
  // List must include both the leaf certificate hash AND at least one
  // intermediate / root CA hash as a backup to survive certificate rotation.
  //
  // TODO(security): Replace these placeholders with real values before release.
  // See the docstring above for the extraction command.

  /// Pinned hashes for [djangoApiHost].
  static const List<String> djangoApiHashes = [
    'REPLACE_WITH_API_PRIMARY_CERT_SPKI_SHA256_BASE64==',
    'REPLACE_WITH_API_BACKUP_CA_SPKI_SHA256_BASE64==',
  ];

  /// Pinned hashes for [fastapiHost].
  static const List<String> fastapiHashes = [
    'REPLACE_WITH_WS_PRIMARY_CERT_SPKI_SHA256_BASE64==',
    'REPLACE_WITH_WS_BACKUP_CA_SPKI_SHA256_BASE64==',
  ];
}
