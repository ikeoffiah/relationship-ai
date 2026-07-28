import 'package:flutter/foundation.dart';
import 'package:uuid/uuid.dart';

import 'package:mobile/features/couple_chat/couple_chat_api_service.dart';
import 'package:mobile/features/couple_chat/models/couple_message.dart';

/// State for the couple's thread.
///
/// The rule shaping this class: **the thread never waits on the network to
/// feel alive.** A sent message renders instantly as a pending bubble and is
/// reconciled when the server answers; a reaction flips immediately and rolls
/// back only if the call fails. In a conversation between two people, a
/// half-second of dead UI reads as the app being broken.
class CoupleChatViewModel extends ChangeNotifier {
  final CoupleChatApiService _api;
  final String relationshipId;
  final String userId;
  final Uuid _uuid;

  CoupleChatViewModel({
    required this.relationshipId,
    required this.userId,
    CoupleChatApiService? api,
    Uuid? uuid,
  }) : _api = api ?? CoupleChatApiService(),
       _uuid = uuid ?? const Uuid();

  final List<CoupleMessage> _messages = [];
  List<CoupleMessage> get messages => List.unmodifiable(_messages);

  bool _loading = false;
  bool get isLoading => _loading;

  bool _hasMore = false;
  bool get hasMore => _hasMore;
  String? _nextBefore;

  String? _error;
  String? get error => _error;

  /// The message being quoted, if the user is composing a reply.
  CoupleMessage? _replyingTo;
  CoupleMessage? get replyingTo => _replyingTo;

  /// Private guidance shown only to this user after receiving a hard message.
  String? _coachGuidance;
  String? get coachGuidance => _coachGuidance;

  bool _coachDefersToSupport = false;
  bool get coachDefersToSupport => _coachDefersToSupport;

  // ── History ───────────────────────────────────────────────────────────────

  Future<void> load() async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      final page = await _api.history(relationshipId);
      _messages
        ..clear()
        // The API returns newest-first; the list renders oldest-first.
        ..addAll(page.messages.reversed);
      _hasMore = page.hasMore;
      _nextBefore = page.nextBefore;
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
    }
    _loading = false;
    notifyListeners();
  }

  Future<void> loadOlder() async {
    if (!_hasMore || _nextBefore == null || _loading) return;
    _loading = true;
    notifyListeners();
    try {
      final page = await _api.history(relationshipId, before: _nextBefore);
      _messages.insertAll(0, page.messages.reversed);
      _hasMore = page.hasMore;
      _nextBefore = page.nextBefore;
    } catch (_) {
      // Older history failing is not worth an error banner over the thread.
    }
    _loading = false;
    notifyListeners();
  }

  // ── Composing ─────────────────────────────────────────────────────────────

  void startReply(CoupleMessage message) {
    _replyingTo = message;
    notifyListeners();
  }

  void cancelReply() {
    _replyingTo = null;
    notifyListeners();
  }

  /// Ask Bliss whether a draft might land badly. Never blocks the send — the
  /// caller decides what to do with a caution.
  Future<DraftVerdict> checkDraft(String draft) =>
      _api.checkDraft(relationshipId, draft);

  Future<String?> rephrase(String draft) => _api.rephrase(relationshipId, draft);

  /// Send a message, rendering it optimistically first.
  Future<void> send(String body) async {
    final trimmed = body.trim();
    if (trimmed.isEmpty) return;

    final clientId = _uuid.v4();
    final quoted = _replyingTo;
    final optimistic = CoupleMessage.pending(
      clientId: clientId,
      senderId: userId,
      body: trimmed,
      replyTo: quoted == null
          ? null
          : ReplyPreview(
              id: quoted.id,
              senderId: quoted.senderId,
              body: quoted.body,
              isDeleted: quoted.isDeleted,
            ),
    );
    _messages.add(optimistic);
    _replyingTo = null;
    notifyListeners();

    try {
      final saved = await _api.send(
        relationshipId,
        clientId: clientId,
        body: trimmed,
        replyTo: quoted?.id,
      );
      _replaceByClientId(clientId, saved);
    } catch (_) {
      // Keep the bubble, mark it failed — a message that vanishes on a flaky
      // connection is worse than one the user can see and retry.
      _replaceByClientId(
        clientId,
        optimistic.copyWith(isPending: false, failed: true),
      );
    }
    notifyListeners();
  }

  /// Resend a bubble that previously failed.
  Future<void> retry(CoupleMessage failed) async {
    _messages.removeWhere((m) => m.clientId == failed.clientId);
    notifyListeners();
    await send(failed.body);
  }

  void _replaceByClientId(String clientId, CoupleMessage replacement) {
    final index = _messages.indexWhere((m) => m.clientId == clientId);
    if (index != -1) {
      _messages[index] = replacement;
    }
  }

  // ── Reactions ─────────────────────────────────────────────────────────────

  /// Toggle a reaction, flipping the UI immediately and reconciling after.
  Future<void> toggleReaction(CoupleMessage message, String emoji) async {
    final index = _messages.indexWhere((m) => m.id == message.id);
    if (index == -1) return;
    final before = _messages[index];

    try {
      final updated = await _api.toggleReaction(message.id, emoji);
      final current = _messages.indexWhere((m) => m.id == message.id);
      if (current != -1) _messages[current] = updated;
    } catch (_) {
      final current = _messages.indexWhere((m) => m.id == message.id);
      if (current != -1) _messages[current] = before;
    }
    notifyListeners();
  }

  Future<void> deleteMessage(CoupleMessage message) async {
    try {
      await _api.deleteMessage(message.id);
      final index = _messages.indexWhere((m) => m.id == message.id);
      if (index != -1) {
        _messages.removeAt(index);
      }
    } catch (_) {
      // Leave the message in place if the delete did not land.
    }
    notifyListeners();
  }

  // ── Incoming ──────────────────────────────────────────────────────────────

  /// A message pushed over the socket. Ignores our own echo and duplicates.
  void onIncoming(CoupleMessage message) {
    if (_messages.any((m) => m.id == message.id)) return;
    _messages.add(message);
    notifyListeners();
    if (!message.isMine(userId) && message.body.isNotEmpty) {
      _maybeCoach(message.body);
    }
  }

  /// Ask, privately, whether this message is worth a word of guidance.
  Future<void> _maybeCoach(String incoming) async {
    final result = await _api.readCoach(relationshipId, incoming);
    _coachGuidance = result.guidance;
    _coachDefersToSupport = result.deferToSupport;
    if (_coachGuidance != null || _coachDefersToSupport) notifyListeners();
  }

  void dismissCoach() {
    _coachGuidance = null;
    _coachDefersToSupport = false;
    notifyListeners();
  }

  /// The partner deleted a message. Mirror it locally rather than refetching.
  void onRemoteDelete(String messageId) {
    final index = _messages.indexWhere((m) => m.id == messageId);
    if (index == -1) return;
    _messages.removeAt(index);
    notifyListeners();
  }

  /// The partner reacted. The server sends the regrouped set, so we replace
  /// rather than trying to reconcile counts locally.
  void onRemoteReaction(String messageId, dynamic reactions) {
    final index = _messages.indexWhere((m) => m.id == messageId);
    if (index == -1 || reactions is! List) return;
    final existing = _messages[index];
    _messages[index] = CoupleMessage(
      id: existing.id,
      senderId: existing.senderId,
      kind: existing.kind,
      body: existing.body,
      sticker: existing.sticker,
      replyTo: existing.replyTo,
      reactions: reactions
          .map((r) => MessageReactionGroup.fromJson(r as Map<String, dynamic>))
          .toList(),
      clientId: existing.clientId,
      isDeleted: existing.isDeleted,
      createdAt: existing.createdAt,
    );
    notifyListeners();
  }

  Future<void> markRead() async {
    try {
      await _api.markRead(relationshipId);
    } catch (_) {
      // Read state is not worth surfacing a failure for.
    }
  }
}
