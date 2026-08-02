/// Something Bliss noticed about the pair, in words true of both of them.
///
/// Mirrors `apps/insights/serializers.py`, which exposes five fields and
/// deliberately no more. The narrative halves and the synthesis exist on the
/// server model and are **not** in the payload: they are built from what one
/// partner said alone, and they stay behind the consent flow in
/// `docs/relationship-insights.md` §5. If a field ever appears here that names
/// one partner, something has gone wrong upstream — not in this file.
///
/// Everything that does arrive is *shape*: that a pattern exists, never its
/// content. "How plans get decided has come back a few times" — not "you keep
/// cancelling on her". That is why an insight can be shown to both partners
/// without either approving it first: there is nothing in it to approve.
library;

enum InsightKind {
  /// The same disagreement returning. Read from the couple's shared thread,
  /// which both of them watched happen.
  recurringTheme,

  /// The two of them have been experiencing recent weeks differently. Note
  /// that the direction is deliberately absent from the payload and must never
  /// be inferred or displayed — see the class docstring on the server
  /// detector. Each partner knows their own check-in scores, so naming who felt
  /// better would hand them the other's private answer by subtraction.
  perceptionGap,

  /// Anything the server adds later. Rendered generically rather than dropped,
  /// but never with invented framing.
  other;

  static InsightKind parse(String? raw) => switch (raw) {
    'recurring_theme' => InsightKind.recurringTheme,
    'perception_gap' => InsightKind.perceptionGap,
    _ => InsightKind.other,
  };
}

class RelationshipInsight {
  final String id;
  final InsightKind kind;

  /// The shape, as the server worded it. Displayed verbatim — this is not a
  /// string to interpolate a partner's name into or to sharpen.
  final String theme;

  final double confidence;
  final DateTime? createdAt;

  const RelationshipInsight({
    required this.id,
    required this.kind,
    required this.theme,
    this.confidence = 0,
    this.createdAt,
  });

  factory RelationshipInsight.fromJson(Map<String, dynamic> json) {
    return RelationshipInsight(
      id: json['id'] as String? ?? '',
      kind: InsightKind.parse(json['type'] as String?),
      theme: json['theme'] as String? ?? '',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? ''),
    );
  }

  /// An insight with no shape to show is not worth a card. The server already
  /// drops anything under its confidence floor, so this is a guard against an
  /// empty string rather than a second opinion about whether the finding holds.
  bool get isPresentable => theme.trim().isNotEmpty;
}
