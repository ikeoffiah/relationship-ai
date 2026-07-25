/// The relationship portrait shown right after onboarding — the "this app gets
/// me" reveal. Mirrors GET /api/v1/personalization/portrait.
library;

class RelationshipPortrait {
  final bool ready;
  final String? message;
  final String? attachmentStyle;
  final String? archetype;
  final String? headline;
  final String? summary;
  final String? whatHelps;
  final String? whatTripsYouUp;
  final String? growthEdge;
  final List<String> likelyFriction;
  final String? communicationNote;
  final String? contextNote;

  const RelationshipPortrait({
    this.ready = false,
    this.message,
    this.attachmentStyle,
    this.archetype,
    this.headline,
    this.summary,
    this.whatHelps,
    this.whatTripsYouUp,
    this.growthEdge,
    this.likelyFriction = const [],
    this.communicationNote,
    this.contextNote,
  });

  factory RelationshipPortrait.fromJson(Map<String, dynamic> json) {
    return RelationshipPortrait(
      ready: json['ready'] as bool? ?? false,
      message: json['message'] as String?,
      attachmentStyle: json['attachment_style'] as String?,
      archetype: json['archetype'] as String?,
      headline: json['headline'] as String?,
      summary: json['summary'] as String?,
      whatHelps: json['what_helps'] as String?,
      whatTripsYouUp: json['what_trips_you_up'] as String?,
      growthEdge: json['growth_edge'] as String?,
      likelyFriction:
          (json['likely_friction'] as List?)?.map((e) => e as String).toList() ?? const [],
      communicationNote: json['communication_note'] as String?,
      contextNote: json['context_note'] as String?,
    );
  }
}
