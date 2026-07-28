/// Models for the couple's own conversation.
///
/// Distinct from the counseling session models: this is the thread the two of
/// them talk in, so a message belongs to a relationship rather than a session.
library;

/// Reactions grouped by emoji, matching how the API returns them — the UI
/// renders "😍 2" chips, so grouping server-side keeps this from being a
/// counting loop in the widget tree.
class MessageReactionGroup {
  final String emoji;
  final int count;
  final List<String> userIds;

  const MessageReactionGroup({
    required this.emoji,
    required this.count,
    required this.userIds,
  });

  factory MessageReactionGroup.fromJson(Map<String, dynamic> json) {
    return MessageReactionGroup(
      emoji: json['emoji'] as String? ?? '',
      count: json['count'] as int? ?? 0,
      userIds: List<String>.from(json['user_ids'] as List? ?? const []),
    );
  }

  bool reactedBy(String userId) => userIds.contains(userId);
}

/// The quoted stub shown above a reply — never the full nested chain, so a
/// long reply thread cannot blow up a single bubble.
class ReplyPreview {
  final String id;
  final String? senderId;
  final String body;
  final bool isDeleted;

  const ReplyPreview({
    required this.id,
    required this.senderId,
    required this.body,
    required this.isDeleted,
  });

  factory ReplyPreview.fromJson(Map<String, dynamic> json) {
    return ReplyPreview(
      id: json['id'] as String,
      senderId: json['sender_id'] as String?,
      body: json['body'] as String? ?? '',
      isDeleted: json['is_deleted'] as bool? ?? false,
    );
  }
}

class CoupleMessage {
  final String id;
  final String? senderId;
  final String kind;
  final String body;
  final String sticker;
  final ReplyPreview? replyTo;
  final List<MessageReactionGroup> reactions;
  final String clientId;
  final bool isDeleted;
  final DateTime createdAt;

  /// True while an optimistically-rendered message is still in flight. The
  /// bubble shows immediately and marks itself pending, so the thread never
  /// waits on the network to feel responsive.
  final bool isPending;

  /// Set when a send failed, so the bubble can offer a retry rather than
  /// silently vanishing.
  final bool failed;

  const CoupleMessage({
    required this.id,
    required this.senderId,
    required this.kind,
    required this.body,
    required this.sticker,
    required this.replyTo,
    required this.reactions,
    required this.clientId,
    required this.isDeleted,
    required this.createdAt,
    this.isPending = false,
    this.failed = false,
  });

  factory CoupleMessage.fromJson(Map<String, dynamic> json) {
    return CoupleMessage(
      id: json['id'] as String,
      senderId: json['sender_id'] as String?,
      kind: json['kind'] as String? ?? 'text',
      body: json['body'] as String? ?? '',
      sticker: json['sticker'] as String? ?? '',
      replyTo: json['reply_to'] == null
          ? null
          : ReplyPreview.fromJson(json['reply_to'] as Map<String, dynamic>),
      reactions: (json['reactions'] as List? ?? const [])
          .map((r) => MessageReactionGroup.fromJson(r as Map<String, dynamic>))
          .toList(),
      clientId: json['client_id'] as String? ?? '',
      isDeleted: json['is_deleted'] as bool? ?? false,
      createdAt:
          DateTime.tryParse(json['created_at'] as String? ?? '')?.toLocal() ??
          DateTime.now(),
    );
  }

  /// An optimistic bubble, rendered before the server has confirmed anything.
  factory CoupleMessage.pending({
    required String clientId,
    required String senderId,
    required String body,
    ReplyPreview? replyTo,
  }) {
    return CoupleMessage(
      id: clientId,
      senderId: senderId,
      kind: 'text',
      body: body,
      sticker: '',
      replyTo: replyTo,
      reactions: const [],
      clientId: clientId,
      isDeleted: false,
      createdAt: DateTime.now(),
      isPending: true,
    );
  }

  CoupleMessage copyWith({bool? isPending, bool? failed}) {
    return CoupleMessage(
      id: id,
      senderId: senderId,
      kind: kind,
      body: body,
      sticker: sticker,
      replyTo: replyTo,
      reactions: reactions,
      clientId: clientId,
      isDeleted: isDeleted,
      createdAt: createdAt,
      isPending: isPending ?? this.isPending,
      failed: failed ?? this.failed,
    );
  }

  bool isMine(String userId) => senderId == userId;
}

/// Bliss's verdict on a draft, returned as the user hits send.
class DraftVerdict {
  final bool caution;
  final String reason;
  final String suggestion;

  const DraftVerdict({
    required this.caution,
    required this.reason,
    required this.suggestion,
  });

  static const ok = DraftVerdict(caution: false, reason: '', suggestion: '');

  factory DraftVerdict.fromJson(Map<String, dynamic> json) {
    return DraftVerdict(
      caution: (json['verdict'] as String? ?? 'ok') == 'caution',
      reason: json['reason'] as String? ?? '',
      suggestion: json['suggestion'] as String? ?? '',
    );
  }
}

/// The emoji offered on long-press. Deliberately weighted to affection rather
/// than the generic thumbs-up set — this is a thread between partners, not a
/// team channel.
const List<String> kCoupleReactions = ['❤️', '😍', '🔥', '😘', '🥰', '😂'];
