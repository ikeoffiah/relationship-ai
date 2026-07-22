// Client models for the async partner relay, matching the FastAPI relay API
// (backend-fastapi/app/api/relay_router.py:RelayDetail / RelayResponse).

/// A relay message as returned by the backend.
class RelayDetail {
  final String relayId;
  final String fromUserId;
  final String toUserId;
  final String relationshipId;
  final String originalContent;
  final String? translatedContent;
  final double translationQualityScore;
  final String status; // ready | quality_review | delivered | withdrawn | expired
  final DateTime createdAt;
  final DateTime? deliveredAt;
  final String? recipientChoseVersion;
  final DateTime expiresAt;

  const RelayDetail({
    required this.relayId,
    required this.fromUserId,
    required this.toUserId,
    required this.relationshipId,
    required this.originalContent,
    required this.translatedContent,
    required this.translationQualityScore,
    required this.status,
    required this.createdAt,
    required this.deliveredAt,
    required this.recipientChoseVersion,
    required this.expiresAt,
  });

  factory RelayDetail.fromJson(Map<String, dynamic> json) {
    DateTime? parse(dynamic v) =>
        v == null ? null : DateTime.tryParse(v as String);
    return RelayDetail(
      relayId: json['relay_id'] as String,
      fromUserId: json['from_user_id'] as String? ?? '',
      toUserId: json['to_user_id'] as String? ?? '',
      relationshipId: json['relationship_id'] as String? ?? '',
      originalContent: json['original_content'] as String? ?? '',
      translatedContent: json['translated_content'] as String?,
      translationQualityScore:
          (json['translation_quality_score'] as num?)?.toDouble() ?? 0.0,
      status: json['status'] as String? ?? 'ready',
      createdAt: parse(json['created_at']) ?? DateTime.now(),
      deliveredAt: parse(json['delivered_at']),
      recipientChoseVersion: json['recipient_chose_version'] as String?,
      expiresAt: parse(json['expires_at']) ?? DateTime.now(),
    );
  }
}

/// Which version the recipient chose to read.
class RelayVersion {
  static const aiTranslated = 'ai_translated';
  static const original = 'original';
}
