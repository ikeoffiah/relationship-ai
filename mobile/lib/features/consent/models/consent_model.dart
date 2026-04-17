/// Represents the full consent state for a user, per REL-20 / Section 4.2.
class ConsentModel {
  final String id;
  final String userId;
  final String? relationshipId;
  final String sessionTranscriptRetention;
  final String crossPartnerInsightSharing;
  final String jointSessionParticipation;
  final String sharedRelationshipContext;
  final bool therapistSummaryAccess;
  final bool modelImprovementData;

  const ConsentModel({
    required this.id,
    required this.userId,
    this.relationshipId,
    this.sessionTranscriptRetention = 'per_session',
    this.crossPartnerInsightSharing = 'never',
    this.jointSessionParticipation = 'not_enrolled',
    this.sharedRelationshipContext = 'not_participating',
    this.therapistSummaryAccess = false,
    this.modelImprovementData = false,
  });

  factory ConsentModel.fromJson(Map<String, dynamic> json) {
    return ConsentModel(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      relationshipId: json['relationship_id'] as String?,
      sessionTranscriptRetention:
          json['session_transcript_retention'] as String? ?? 'per_session',
      crossPartnerInsightSharing:
          json['cross_partner_insight_sharing'] as String? ?? 'never',
      jointSessionParticipation:
          json['joint_session_participation'] as String? ?? 'not_enrolled',
      sharedRelationshipContext:
          json['shared_relationship_context'] as String? ?? 'not_participating',
      therapistSummaryAccess:
          json['therapist_summary_access'] as bool? ?? false,
      modelImprovementData: json['model_improvement_data'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'user_id': userId,
        'relationship_id': relationshipId,
        'session_transcript_retention': sessionTranscriptRetention,
        'cross_partner_insight_sharing': crossPartnerInsightSharing,
        'joint_session_participation': jointSessionParticipation,
        'shared_relationship_context': sharedRelationshipContext,
        'therapist_summary_access': therapistSummaryAccess,
        'model_improvement_data': modelImprovementData,
      };

  ConsentModel copyWith({
    String? sessionTranscriptRetention,
    String? crossPartnerInsightSharing,
    String? jointSessionParticipation,
    String? sharedRelationshipContext,
    bool? therapistSummaryAccess,
    bool? modelImprovementData,
  }) {
    return ConsentModel(
      id: id,
      userId: userId,
      relationshipId: relationshipId,
      sessionTranscriptRetention:
          sessionTranscriptRetention ?? this.sessionTranscriptRetention,
      crossPartnerInsightSharing:
          crossPartnerInsightSharing ?? this.crossPartnerInsightSharing,
      jointSessionParticipation:
          jointSessionParticipation ?? this.jointSessionParticipation,
      sharedRelationshipContext:
          sharedRelationshipContext ?? this.sharedRelationshipContext,
      therapistSummaryAccess:
          therapistSummaryAccess ?? this.therapistSummaryAccess,
      modelImprovementData: modelImprovementData ?? this.modelImprovementData,
    );
  }

  /// Human-readable display labels for all consent state values.
  /// Per REL-XX specification.
  static const Map<String, String> displayLabels = {
    'per_session': 'Not saved after session ends',
    '30_days': 'Saved for 30 days',
    '1_year': 'Saved for 1 year',
    'indefinite': 'Saved indefinitely',
    'never': 'Not shared with partner',
    'anonymized': 'Shared anonymously',
    'named': 'Shared with your name',
    'not_enrolled': 'Joint sessions off',
    'enrolled': 'Joint sessions on',
    'not_participating': 'No shared context',
    'read_only': 'Partner can see summary',
    'read_write': 'Both partners share context',
  };

  /// Returns the human-readable label for a given consent value.
  static String labelFor(String value) {
    return displayLabels[value] ?? value;
  }

  /// Fallback model — most restrictive defaults used on API failure.
  static ConsentModel defaultRestrictive(String userId) => ConsentModel(
        id: '',
        userId: userId,
      );
}
