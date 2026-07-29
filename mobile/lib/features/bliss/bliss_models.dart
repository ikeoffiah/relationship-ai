/// Models for the @bliss assistant (talks to the Django engagement API).
library;

/// A parsed-but-unsaved draft returned by POST bliss/interpret.
class BlissDraft {
  final String kind; // 'reminder' | 'event'
  final String title;
  final DateTime? dueAt;
  final bool hasTime;

  const BlissDraft({
    required this.kind,
    required this.title,
    this.dueAt,
    this.hasTime = false,
  });

  factory BlissDraft.fromJson(Map<String, dynamic> j) => BlissDraft(
        kind: j['kind'] as String? ?? 'reminder',
        title: j['title'] as String? ?? '',
        dueAt: j['due_at'] != null ? DateTime.tryParse(j['due_at'] as String) : null,
        hasTime: j['has_time'] as bool? ?? false,
      );

  BlissDraft copyWith({String? kind, String? title, DateTime? dueAt, bool? hasTime}) => BlissDraft(
        kind: kind ?? this.kind,
        title: title ?? this.title,
        dueAt: dueAt ?? this.dueAt,
        hasTime: hasTime ?? this.hasTime,
      );
}

/// Where a tagged partner has got to on an item.
///
/// [none] is not a missing answer — it means nobody was asked. An item with no
/// invite is a shared plan and still reminds both people; only an explicit
/// invite gates that.
enum PartnerInvite { none, pending, accepted, declined }

PartnerInvite _inviteFromName(String? name) => switch (name) {
  'pending' => PartnerInvite.pending,
  'accepted' => PartnerInvite.accepted,
  'declined' => PartnerInvite.declined,
  _ => PartnerInvite.none,
};

/// A persisted reminder or calendar event shared by the couple.
class BlissItem {
  final String id;
  final String kind;
  final String title;
  final DateTime? dueAt;
  final String status; // 'pending' | 'done' | 'cancelled'
  final String source;

  final PartnerInvite partnerInvite;
  final DateTime? partnerRespondedAt;
  final bool createdByMe;

  /// Whether *this reader* is the one being asked.
  ///
  /// Comes from the server rather than being derived here from the invite state
  /// plus who created it. Getting it backwards would show the person who sent
  /// an invitation an Accept button for their own request.
  final bool awaitingMyAnswer;

  const BlissItem({
    required this.id,
    this.kind = 'reminder',
    this.title = '',
    this.dueAt,
    this.status = 'pending',
    this.source = 'bliss',
    this.partnerInvite = PartnerInvite.none,
    this.partnerRespondedAt,
    this.createdByMe = false,
    this.awaitingMyAnswer = false,
  });

  bool get isEvent => kind == 'event';

  /// Shown to the person who sent the invitation, never to the one being asked
  /// — they get buttons instead of a status line.
  String? get inviteStatusLabel {
    if (!createdByMe || partnerInvite == PartnerInvite.none) return null;
    return switch (partnerInvite) {
      PartnerInvite.pending => 'Waiting for them',
      PartnerInvite.accepted => "They're in",
      PartnerInvite.declined => 'They said no',
      PartnerInvite.none => null,
    };
  }

  factory BlissItem.fromJson(Map<String, dynamic> j) => BlissItem(
        id: j['id'] as String,
        kind: j['kind'] as String? ?? 'reminder',
        title: j['title'] as String? ?? '',
        dueAt: j['due_at'] != null ? DateTime.tryParse(j['due_at'] as String) : null,
        status: j['status'] as String? ?? 'pending',
        source: j['source'] as String? ?? 'bliss',
        partnerInvite: _inviteFromName(j['partner_invite'] as String?),
        partnerRespondedAt: j['partner_responded_at'] != null
            ? DateTime.tryParse(j['partner_responded_at'] as String)
            : null,
        createdByMe: j['created_by_me'] as bool? ?? false,
        awaitingMyAnswer: j['awaiting_my_answer'] as bool? ?? false,
      );
}
