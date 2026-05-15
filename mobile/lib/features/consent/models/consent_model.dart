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
  final String? updatedAt;
  final Map<String, String> plainLanguageSummary;

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
    this.updatedAt,
    this.plainLanguageSummary = const {},
  });

  factory ConsentModel.fromJson(Map<String, dynamic> json) {
    final data = json.containsKey('data') ? json['data'] : json;
    
    return ConsentModel(
      id: data['id'] as String? ?? '',
      userId: data['user_id'] as String,
      relationshipId: data['relationship_id'] as String?,
      sessionTranscriptRetention:
          data['session_transcript_retention'] as String? ?? 'per_session',
      crossPartnerInsightSharing:
          data['cross_partner_insight_sharing'] as String? ?? 'never',
      jointSessionParticipation:
          data['joint_session_participation'] as String? ?? 'not_enrolled',
      sharedRelationshipContext:
          data['shared_relationship_context'] as String? ?? 'not_participating',
      therapistSummaryAccess:
          data['therapist_summary_access'] as bool? ?? false,
      modelImprovementData: data['model_improvement_data'] as bool? ?? false,
      updatedAt: data['updated_at'] as String?,
      plainLanguageSummary: Map<String, String>.from(data['plain_language_summary'] ?? {}),
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
        'updated_at': updatedAt,
        'plain_language_summary': plainLanguageSummary,
      };

  ConsentModel copyWith({
    String? sessionTranscriptRetention,
    String? crossPartnerInsightSharing,
    String? jointSessionParticipation,
    String? sharedRelationshipContext,
    bool? therapistSummaryAccess,
    bool? modelImprovementData,
    Map<String, String>? plainLanguageSummary,
    String? updatedAt,
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
      updatedAt: updatedAt ?? this.updatedAt,
      plainLanguageSummary: plainLanguageSummary ?? this.plainLanguageSummary,
    );
  }

  /// Human-readable display labels for all consent state values.
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
        updatedAt: null,
        plainLanguageSummary: {
          'session_transcript_retention': 'Your session conversations are deleted when the session ends.',
          'cross_partner_insight_sharing': 'Nothing from your sessions is shared with your partner.',
          'joint_session_participation': 'You are not enrolled in joint sessions with your partner.',
          'shared_relationship_context': 'You are not participating in shared context.',
          'therapist_summary_access': 'Your therapist cannot see summaries.',
          'model_improvement_data': 'Your data is not used for improvement.',
        }
      );
}
