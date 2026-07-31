/// Models for the couple's own conversation.
///
/// Distinct from the counseling session models: this is the thread the two of
/// them talk in, so a message belongs to a relationship rather than a session.
library;

import 'package:mobile/features/couple_chat/models/message_media.dart';

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

  /// 'text', 'sticker', 'image' or 'voice' — the quote renders a label for
  /// media rather than an empty line.
  final String kind;

  /// Thumbnail of the quoted photo, if it still exists. Goes null the moment
  /// the media is destroyed, so a quote never points at bytes that are gone.
  final String? thumbUrl;

  const ReplyPreview({
    required this.id,
    required this.senderId,
    required this.body,
    required this.isDeleted,
    this.kind = 'text',
    this.thumbUrl,
  });

  factory ReplyPreview.fromJson(Map<String, dynamic> json) {
    return ReplyPreview(
      id: json['id'] as String,
      senderId: json['sender_id'] as String?,
      body: json['body'] as String? ?? '',
      isDeleted: json['is_deleted'] as bool? ?? false,
      kind: json['kind'] as String? ?? 'text',
      thumbUrl: json['thumb_url'] as String?,
    );
  }

  /// What to show when there is no text — a caption-less photo or any voice
  /// note. Deliberately the same vocabulary people already read in other
  /// messengers.
  String get label => switch (kind) {
    'image' => '📷 Photo',
    'voice' => '🎤 Voice message',
    'sticker' => 'Sticker',
    _ => '',
  };
}

/// How far a message you sent has got.
///
/// Deliberately the WhatsApp vocabulary, because it is the vocabulary people
/// already read fluently: a clock while it is in flight, one tick when we hold
/// it, two when their phone holds it, two in colour when they opened the
/// thread. The states are ordered, and the UI relies on that order — nothing
/// may ever move a message backwards down this list.
enum MessageStatus {
  /// In flight. Ours alone; the server never reports this.
  sending,

  /// The send failed. Also ours alone — the server, by definition, never
  /// hears about a request that did not arrive.
  failed,

  /// We have it. Whether their phone does is genuinely unknown.
  sent,

  /// Their device acknowledged it. Says nothing about whether they looked.
  delivered,

  /// They opened the thread past this message.
  seen,
}

MessageStatus? _statusFromName(String? name) => switch (name) {
  'sent' => MessageStatus.sent,
  'delivered' => MessageStatus.delivered,
  'seen' => MessageStatus.seen,
  _ => null,
};

class CoupleMessage {
  final String id;
  final String? senderId;
  final String kind;
  final String body;
  final String sticker;

  /// The photo or voice note, when [kind] is 'image' or 'voice'. Null once the
  /// bytes have been destroyed, even though the bubble survives as a tombstone.
  final MessageMedia? media;

  final ReplyPreview? replyTo;
  final List<MessageReactionGroup> reactions;
  final String clientId;
  final bool isDeleted;
  final DateTime createdAt;

  /// Upload progress, 0..1, while an optimistic media bubble is in flight.
  /// Null for anything that is not currently uploading.
  final double? uploadProgress;

  /// True while an optimistically-rendered message is still in flight. The
  /// bubble shows immediately and marks itself pending, so the thread never
  /// waits on the network to feel responsive.
  final bool isPending;

  /// Set when a send failed, so the bubble can offer a retry rather than
  /// silently vanishing.
  final bool failed;

  /// What the server said about this message when we last fetched it. Null on
  /// the partner's messages — you get ticks on what you sent, not on what you
  /// received. Live updates arrive as cursor moves rather than as per-message
  /// pushes, so this is a seed for [CoupleChatViewModel]'s cursors and not the
  /// value the bubble reads.
  final MessageStatus? serverStatus;

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
    this.media,
    this.isPending = false,
    this.failed = false,
    this.serverStatus,
    this.uploadProgress,
  });

  factory CoupleMessage.fromJson(Map<String, dynamic> json) {
    return CoupleMessage(
      id: json['id'] as String,
      senderId: json['sender_id'] as String?,
      kind: json['kind'] as String? ?? 'text',
      body: json['body'] as String? ?? '',
      sticker: json['sticker'] as String? ?? '',
      media: json['media'] == null
          ? null
          : MessageMedia.fromJson(json['media'] as Map<String, dynamic>),
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
      serverStatus: _statusFromName(json['status'] as String?),
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

  /// An optimistic sticker bubble.
  factory CoupleMessage.pendingSticker({
    required String clientId,
    required String senderId,
    required String sticker,
  }) {
    return CoupleMessage(
      id: clientId,
      senderId: senderId,
      kind: 'sticker',
      body: '',
      sticker: sticker,
      replyTo: null,
      reactions: const [],
      clientId: clientId,
      isDeleted: false,
      createdAt: DateTime.now(),
      isPending: true,
    );
  }

  /// An optimistic photo or voice bubble, rendered straight from the file on
  /// this device.
  ///
  /// This is the whole reason upload and send are two steps: the bubble is on
  /// screen the instant the photo is picked or the finger lifts off the mic,
  /// with a progress ring over it, rather than after a round trip.
  factory CoupleMessage.pendingMedia({
    required String clientId,
    required String senderId,
    required String kind,
    required String localPath,
    String body = '',
    int? durationMs,
    List<int> waveform = const [],
    ReplyPreview? replyTo,
  }) {
    return CoupleMessage(
      id: clientId,
      senderId: senderId,
      kind: kind,
      body: body,
      sticker: '',
      media: MessageMedia.local(
        kind: kind,
        localPath: localPath,
        durationMs: durationMs,
        waveform: waveform,
      ),
      replyTo: replyTo,
      reactions: const [],
      clientId: clientId,
      isDeleted: false,
      createdAt: DateTime.now(),
      isPending: true,
      uploadProgress: 0,
    );
  }

  CoupleMessage copyWith({
    bool? isPending,
    bool? failed,
    MessageStatus? serverStatus,
    MessageMedia? media,
    double? uploadProgress,
  }) {
    return CoupleMessage(
      id: id,
      senderId: senderId,
      kind: kind,
      body: body,
      sticker: sticker,
      media: media ?? this.media,
      replyTo: replyTo,
      reactions: reactions,
      clientId: clientId,
      isDeleted: isDeleted,
      createdAt: createdAt,
      isPending: isPending ?? this.isPending,
      failed: failed ?? this.failed,
      serverStatus: serverStatus ?? this.serverStatus,
      uploadProgress: uploadProgress ?? this.uploadProgress,
    );
  }

  bool isMine(String userId) => senderId == userId;

  bool get isMedia => kind == 'image' || kind == 'voice';

  /// True for a media bubble whose bytes were destroyed — the row survives so
  /// replies still render, but there is nothing left to show.
  bool get isMediaTombstone => isMedia && media == null;
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

/// Which way a pre-send caution went.
///
/// The best supervised signal in the product: the person was shown help at the
/// decisive moment, holding a finished message, and chose. Until this was
/// reported the check ran, the sheet appeared, someone decided — and nothing
/// was written down, so a caution that was overridden every single time went
/// on interrupting forever.
///
/// The wire values are fixed by `CAUTION_CHOICES` in the server's chat views;
/// anything else is rejected with a 400.
enum CautionOutcome {
  usedSuggestion('used_suggestion'),
  edited('edited'),
  sentAnyway('sent_anyway');

  const CautionOutcome(this.wire);

  final String wire;
}

/// The emoji offered on long-press. Deliberately weighted to affection rather
/// than the generic thumbs-up set — this is a thread between partners, not a
/// team channel.
const List<String> kCoupleReactions = ['❤️', '😍', '🔥', '😘', '🥰', '😂'];
