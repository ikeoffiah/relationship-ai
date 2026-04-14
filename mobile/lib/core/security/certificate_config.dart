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

  /// Primary REST / Django API host.
  static const String djangoApiHost = 'api.relationshipai.com';

  /// WebSocket / FastAPI host.
  static const String fastapiHost = 'ws.relationshipai.com';

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
