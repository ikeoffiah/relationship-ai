import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_dimens.dart';
import 'package:mobile/features/couple_chat/couple_chat_socket.dart';
import 'package:mobile/features/couple_chat/couple_chat_viewmodel.dart';
import 'package:mobile/features/bliss/bliss_viewmodel.dart';
import 'package:mobile/features/bliss/widgets/bliss_confirm_sheet.dart';
import 'package:mobile/features/couple_chat/models/couple_message.dart';
import 'package:mobile/features/couple_chat/models/sticker_catalogue.dart';
import 'package:mobile/features/couple_chat/views/media_bubbles.dart';
import 'package:mobile/features/couple_chat/views/sticker_picker_sheet.dart';
import 'package:mobile/features/couple_chat/views/voice_recorder.dart';
import 'package:mobile/shared/widgets/support_action.dart';

/// The couple's conversation.
///
/// Bliss lives here as a chip above the composer and a sheet on send — never
/// as a blocking gate. Every path through this screen ends with the message
/// going if the user wants it to go.
class CoupleChatScreen extends StatefulWidget {
  final String relationshipId;
  final String userId;
  final String partnerName;

  const CoupleChatScreen({
    required this.relationshipId,
    required this.userId,
    this.partnerName = 'your partner',
    super.key,
  });

  @override
  State<CoupleChatScreen> createState() => _CoupleChatScreenState();
}

class _CoupleChatScreenState extends State<CoupleChatScreen> {
  final _composer = TextEditingController();
  final _scroll = ScrollController();
  final _recorder = GlobalKey<VoiceRecorderBarState>();
  final _picker = ImagePicker();
  bool _sending = false;
  bool _recording = false;

  /// Drives the mic⇄send swap. Held in state rather than read from the
  /// controller at build time so the swap animates on the first character.
  bool _hasText = false;

  CoupleChatSocket? _socket;

  @override
  void initState() {
    super.initState();
    _composer.addListener(_onComposerChanged);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final vm = context.read<CoupleChatViewModel>();
      vm.load().then((_) {
        vm.markRead();
        _jumpToLatest();
      });

      // Live delivery. The thread still works without it — history is fetched
      // over HTTP — so a failed socket degrades to "not instant", never to
      // "broken".
      _socket = CoupleChatSocket(
        relationshipId: widget.relationshipId,
        onEvent: (event) => _handleSocketEvent(vm, event),
        onConnectionLost: vm.onSocketLost,
      )..connect();
    });
  }

  void _handleSocketEvent(CoupleChatViewModel vm, Map<String, dynamic> event) {
    switch (event['type']) {
      case 'couple_message':
        final raw = event['message'];
        if (raw is Map<String, dynamic>) {
          vm.onIncoming(CoupleMessage.fromJson(raw));
          _jumpToLatest();
          vm.markRead();
        }
      case 'couple_message_deleted':
        vm.onRemoteDelete(event['message_id'] as String? ?? '');
      case 'couple_message_reaction':
        vm.onRemoteReaction(
          event['message_id'] as String? ?? '',
          event['reactions'],
        );
      case 'thread_ready':
        vm.onPartnerPresence(event['partner_online'] as bool? ?? false);
      case 'presence':
        vm.onPartnerPresence(event['online'] as bool? ?? false);
      case 'couple_receipt':
        // Their cursor moved, so our ticks do too — without this the sender
        // only ever sees ticks advance on a refetch, which in practice means
        // "never, while I am looking at the thread".
        vm.onPartnerReceipt(
          deliveredAt: DateTime.tryParse(
            event['last_delivered_at'] as String? ?? '',
          )?.toLocal(),
          readAt: DateTime.tryParse(
            event['last_read_at'] as String? ?? '',
          )?.toLocal(),
        );
    }
  }

  /// Index of the last message this user sent, or -1 if they have not sent one.
  int _lastOwnIndex(CoupleChatViewModel vm, String userId) {
    for (var i = vm.messages.length - 1; i >= 0; i--) {
      if (vm.messages[i].isMine(userId)) return i;
    }
    return -1;
  }

  @override
  void dispose() {
    _socket?.dispose();
    _composer.removeListener(_onComposerChanged);
    _composer.dispose();
    _scroll.dispose();
    super.dispose();
  }

  void _onComposerChanged() {
    final hasText = _composer.text.trim().isNotEmpty;
    if (hasText != _hasText) setState(() => _hasText = hasText);
  }

  // ── Media ─────────────────────────────────────────────────────────────────

  /// Camera or library. Two options, deliberately — a file browser in a
  /// couple's thread is a way to send the wrong thing by accident.
  Future<void> _showAttachSheet() async {
    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      backgroundColor: AppColors.creamWhite,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadii.lg)),
      ),
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              key: const Key('attach_camera'),
              leading: const Icon(Icons.photo_camera_outlined),
              title: const Text('Take a photo'),
              onTap: () => Navigator.pop(context, ImageSource.camera),
            ),
            ListTile(
              key: const Key('attach_library'),
              leading: const Icon(Icons.photo_library_outlined),
              title: const Text('Photo library'),
              onTap: () => Navigator.pop(context, ImageSource.gallery),
            ),
            const SizedBox(height: AppSpacing.sm),
          ],
        ),
      ),
    );
    if (source == null || !mounted) return;
    await _pickAndSendPhoto(source);
  }

  Future<void> _pickAndSendPhoto(ImageSource source) async {
    final vm = context.read<CoupleChatViewModel>();
    try {
      // Downscaled on the device before it ever leaves: the server re-encodes
      // anyway, and uploading a 12MP original over a phone connection is a
      // slow progress ring for no gain. The server still strips metadata —
      // this is a bandwidth measure, not the privacy one.
      final picked = await _picker.pickImage(
        source: source,
        maxWidth: 2048,
        maxHeight: 2048,
        imageQuality: 88,
      );
      if (picked == null || !mounted) return;

      final caption = _composer.text.trim();
      _composer.clear();
      await vm.sendMedia(
        localPath: picked.path,
        kind: 'image',
        caption: caption,
      );
      _jumpToLatest();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Could not open that photo.')),
      );
    }
  }

  Future<void> _sendRecording(VoiceRecording recording) async {
    final vm = context.read<CoupleChatViewModel>();
    await vm.sendMedia(
      localPath: recording.path,
      kind: 'voice',
      durationMs: recording.durationMs,
      waveform: recording.waveform,
    );
    _jumpToLatest();
  }

  void _jumpToLatest() {
    if (!_scroll.hasClients) return;
    _scroll.animateTo(
      _scroll.position.maxScrollExtent + 120,
      duration: const Duration(milliseconds: 250),
      curve: Curves.easeOut,
    );
  }

  Future<void> _handleSend() async {
    final draft = _composer.text.trim();
    if (draft.isEmpty || _sending) return;
    final vm = context.read<CoupleChatViewModel>();

    if (await _maybeHandleBliss(vm, draft)) return;

    setState(() => _sending = true);
    final verdict = await vm.checkDraft(draft);
    if (!mounted) return;
    setState(() => _sending = false);

    if (verdict.caution) {
      final choice = await _showCautionSheet(verdict);
      if (!mounted) return;
      switch (choice) {
        case _CautionChoice.sendAnyway:
          break;
        case _CautionChoice.sendSuggestion:
          _composer.text = verdict.suggestion;
        case _CautionChoice.edit:
        case null:
          return; // stay in the composer
      }
    }

    final toSend = _composer.text.trim();
    _composer.clear();
    await vm.send(toSend);
    _jumpToLatest();
  }

  /// "@bliss remind us to call the venue tomorrow at 5pm".
  ///
  /// The important difference from the counseling chat, where a @bliss line is
  /// consumed instead of sent: here the message goes to the partner *as well*.
  /// This is a conversation between two people, and quietly swallowing what one
  /// of them typed — so the other never sees that anything was asked — would be
  /// the wrong trade for a tidier thread. Bliss then replies in the thread
  /// itself (a system line written server-side on confirm), so both of them see
  /// the same record of what was scheduled.
  ///
  /// Returns true if this was a Bliss command, so the caller does not also run
  /// the normal draft check on it.
  Future<bool> _maybeHandleBliss(CoupleChatViewModel vm, String text) async {
    if (!isBlissCommand(text)) return false;

    final bliss = context.read<BlissViewModel>();
    final messenger = ScaffoldMessenger.of(context);

    _composer.clear();
    await vm.send(text);
    _jumpToLatest();

    final draft = await bliss.interpret(text);
    if (!mounted) return true;
    if (draft == null) {
      // The message still went. Only the scheduling failed, and saying so
      // beats silently doing nothing with the tag.
      messenger.showSnackBar(
        const SnackBar(
          content: Text(
            "I couldn't find a time in that. Try “@bliss remind us to call "
            'the venue tomorrow at 5pm”.',
          ),
        ),
      );
      return true;
    }

    final confirmed = await BlissConfirmSheet.open(context, draft);
    if (confirmed == null || !mounted) return true;

    // source: couple_chat is what tells the server to post the system line
    // into this thread. Anywhere else, it stays private.
    final item = await bliss.create(confirmed, source: 'couple_chat');
    if (!mounted) return true;
    if (item == null) {
      messenger.showSnackBar(
        const SnackBar(content: Text("Couldn't save that — try again.")),
      );
    }
    return true;
  }

  void _showStickers(CoupleChatViewModel vm) {
    StickerPickerSheet.show(
      context,
      intimateUnlocked: vm.intimateUnlocked,
      onPick: (id) {
        vm.sendSticker(id);
        _jumpToLatest();
      },
    );
  }

  /// Three ways out, and none of them is "you may not send this."
  Future<_CautionChoice?> _showCautionSheet(DraftVerdict verdict) {
    return showModalBottomSheet<_CautionChoice>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (sheetContext) => Container(
        padding: const EdgeInsets.all(AppSpacing.xxl),
        decoration: const BoxDecoration(
          color: AppColors.creamWhite,
          borderRadius: BorderRadius.vertical(
            top: Radius.circular(AppRadii.lg),
          ),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.favorite_border_rounded,
                  size: 18,
                  color: AppColors.warmCoral,
                ),
                const SizedBox(width: AppSpacing.sm),
                Text(
                  verdict.reason.isEmpty
                      ? 'This might land harder than you mean'
                      : verdict.reason,
                  style: Theme.of(context).textTheme.titleSmall,
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.lg),
            Container(
              padding: const EdgeInsets.all(AppSpacing.lg),
              decoration: BoxDecoration(
                color: AppColors.calmSurface,
                borderRadius: BorderRadius.circular(AppRadii.md),
              ),
              child: Text(
                verdict.suggestion,
                style: Theme.of(context).textTheme.bodyLarge,
              ),
            ),
            const SizedBox(height: AppSpacing.xl),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () => Navigator.pop(
                  sheetContext,
                  _CautionChoice.sendSuggestion,
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.warmCoral,
                  foregroundColor: Colors.white,
                  elevation: 0,
                  padding: const EdgeInsets.symmetric(vertical: AppSpacing.lg),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(AppRadii.lg),
                  ),
                ),
                child: const Text('Send this instead'),
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            Row(
              children: [
                Expanded(
                  child: TextButton(
                    onPressed: () =>
                        Navigator.pop(sheetContext, _CautionChoice.edit),
                    child: const Text('Let me edit'),
                  ),
                ),
                Expanded(
                  child: TextButton(
                    onPressed: () =>
                        Navigator.pop(sheetContext, _CautionChoice.sendAnyway),
                    style: TextButton.styleFrom(
                      foregroundColor: AppColors.softCharcoal.withValues(
                        alpha: 0.7,
                      ),
                    ),
                    child: const Text('Send as written'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _showReactions(CoupleMessage message) async {
    final vm = context.read<CoupleChatViewModel>();
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (sheetContext) => Container(
        padding: const EdgeInsets.all(AppSpacing.xl),
        decoration: const BoxDecoration(
          color: AppColors.creamWhite,
          borderRadius: BorderRadius.vertical(
            top: Radius.circular(AppRadii.lg),
          ),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Wrap(
              spacing: AppSpacing.md,
              children: [
                for (final emoji in kCoupleReactions)
                  InkWell(
                    key: Key('reaction_$emoji'),
                    borderRadius: BorderRadius.circular(AppRadii.pill),
                    onTap: () {
                      Navigator.pop(sheetContext);
                      vm.toggleReaction(message, emoji);
                    },
                    child: Padding(
                      padding: const EdgeInsets.all(AppSpacing.sm),
                      child: Text(
                        emoji,
                        style: const TextStyle(fontSize: 30),
                      ),
                    ),
                  ),
              ],
            ),
            const Divider(height: AppSpacing.xxl),
            ListTile(
              leading: const Icon(Icons.reply_rounded, size: 20),
              title: const Text('Reply'),
              onTap: () {
                Navigator.pop(sheetContext);
                vm.startReply(message);
              },
            ),
            if (message.isMine(widget.userId))
              ListTile(
                leading: const Icon(Icons.delete_outline_rounded, size: 20),
                title: const Text('Delete'),
                onTap: () {
                  Navigator.pop(sheetContext);
                  vm.deleteMessage(message);
                },
              ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<CoupleChatViewModel>(
      builder: (context, vm, _) {
        return Scaffold(
          backgroundColor: AppColors.creamWhite,
          appBar: AppBar(
            backgroundColor: Colors.transparent,
            elevation: 0,
            title: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  widget.partnerName,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                // Shown only while they are here. The absence of a line is the
                // offline state — an explicit "Offline", or worse a last-seen
                // time, turns the header into a status board for one partner
                // to watch the other on.
                if (vm.partnerOnline)
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 7,
                        height: 7,
                        decoration: const BoxDecoration(
                          color: AppColors.seenTick,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: AppSpacing.xs),
                      Text(
                        'Online',
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: AppColors.seenTick,
                        ),
                      ),
                    ],
                  ),
              ],
            ),
            actions: const [SupportAction()],
          ),
          body: Column(
            children: [
              Expanded(
                child: vm.isLoading && vm.messages.isEmpty
                    ? const Center(
                        child: CircularProgressIndicator(
                          color: AppColors.warmCoral,
                        ),
                      )
                    : ListView.builder(
                        controller: _scroll,
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.lg,
                          vertical: AppSpacing.md,
                        ),
                        itemCount: vm.messages.length,
                        itemBuilder: (context, i) {
                          final message = vm.messages[i];
                          return _Bubble(
                            key: Key('bubble_${message.id}'),
                            message: message,
                            userId: widget.userId,
                            status: vm.statusFor(message),
                            // Only the newest message of mine spells the state
                            // out in words. Repeating "Delivered" down the whole
                            // thread is noise; the one at the bottom is the one
                            // anyone is actually asking about.
                            showStatusLabel: i == _lastOwnIndex(vm, widget.userId),
                            onLongPress: () => _showReactions(message),
                            onRetry: () => vm.retry(message),
                            onRequestTranscript: () => vm.loadTranscript(message),
                          );
                        },
                      ),
              ),
              if (vm.coachGuidance != null || vm.coachDefersToSupport)
                _CoachStrip(
                  guidance: vm.coachGuidance,
                  defersToSupport: vm.coachDefersToSupport,
                  onDismiss: vm.dismissCoach,
                ),
              if (vm.replyingTo != null)
                _ReplyPreviewStrip(
                  message: vm.replyingTo!,
                  onCancel: vm.cancelReply,
                ),
              _Composer(
                controller: _composer,
                sending: _sending,
                hasText: _hasText,
                onSend: _handleSend,
                onStickers: () => _showStickers(vm),
                onAttach: _showAttachSheet,
                onStartRecording: () => _recorder.currentState?.start(),
                onRecordDrag: (offset) => _recorder.currentState?.onDrag(offset),
                onRecordRelease: () => _recorder.currentState?.onRelease(),
                recording: _recording,
                recorderBar: VoiceRecorderBar(
                  key: _recorder,
                  onComplete: _sendRecording,
                  onActiveChanged: (active) {
                    if (mounted) setState(() => _recording = active);
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

enum _CautionChoice { sendAnyway, sendSuggestion, edit }

class _Bubble extends StatelessWidget {
  final CoupleMessage message;
  final String userId;

  /// Null on the partner's messages — ticks belong to the sender.
  final MessageStatus? status;

  /// Whether to spell the state out in words as well as ticks.
  final bool showStatusLabel;
  final VoidCallback onLongPress;
  final VoidCallback onRetry;

  /// Asks for a voice note's transcript, which arrives after the message does.
  final Future<void> Function()? onRequestTranscript;

  const _Bubble({
    required this.message,
    required this.userId,
    required this.status,
    required this.showStatusLabel,
    required this.onLongPress,
    required this.onRetry,
    this.onRequestTranscript,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    // A system line is authored by nobody. Rendering it as a left-hand bubble
    // would attribute it to the partner, which is exactly the confusion the
    // separate kind exists to prevent.
    if (message.kind == 'system') return _systemLine(context);

    final mine = message.isMine(userId);
    final bubble = GestureDetector(
        onLongPress: message.isDeleted ? null : onLongPress,
        child: Container(
          margin: const EdgeInsets.only(bottom: AppSpacing.sm),
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.lg,
            vertical: AppSpacing.md,
          ),
          constraints: BoxConstraints(
            maxWidth: MediaQuery.of(context).size.width * 0.76,
          ),
          decoration: BoxDecoration(
            color: mine ? AppColors.warmCoral : Colors.white,
            borderRadius: BorderRadius.only(
              topLeft: const Radius.circular(AppRadii.md),
              topRight: const Radius.circular(AppRadii.md),
              bottomLeft: Radius.circular(mine ? AppRadii.md : AppSpacing.xs),
              bottomRight: Radius.circular(mine ? AppSpacing.xs : AppRadii.md),
            ),
            border: mine
                ? null
                : Border.all(
                    color: AppColors.softCharcoal.withValues(alpha: 0.08),
                  ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (message.replyTo != null) _quote(context, mine),
              if (message.kind == 'sticker' && !message.isDeleted)
                _sticker()
              else if (message.isMedia && !message.isDeleted)
                _media(mine)
              else
                Text(
                  message.isDeleted ? 'This message was deleted' : message.body,
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: mine ? Colors.white : AppColors.softCharcoal,
                    fontStyle: message.isDeleted
                        ? FontStyle.italic
                        : FontStyle.normal,
                  ),
                ),
              if (message.reactions.isNotEmpty) _reactions(mine),
            ],
          ),
        ),
      );

    // The footer sits outside the bubble on purpose. Inside, the ticks would be
    // sitting on saturated coral, where the "seen" tint manages about 1.1:1
    // against the background — invisible at glyph size. On the page ground it
    // has room to actually carry meaning.
    return Column(
      crossAxisAlignment: mine
          ? CrossAxisAlignment.end
          : CrossAxisAlignment.start,
      children: [
        bubble,
        if (mine && status != null)
          Padding(
            padding: const EdgeInsets.only(
              right: AppSpacing.xs,
              bottom: AppSpacing.sm,
            ),
            child: _StatusFooter(
              status: status!,
              showLabel: showStatusLabel,
              onRetry: onRetry,
            ),
          ),
      ],
    );
  }

  /// A photo or voice note. A media message whose bytes are gone renders the
  /// same tombstone a deleted text message does, rather than a broken image.
  Widget _media(bool mine) {
    if (message.isMediaTombstone) {
      return Builder(
        builder: (context) => Text(
          'This message was deleted',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            color: mine ? Colors.white : AppColors.softCharcoal,
            fontStyle: FontStyle.italic,
          ),
        ),
      );
    }
    if (message.kind == 'voice') {
      return VoiceBubble(
        message: message,
        mine: mine,
        onRetry: message.failed ? onRetry : null,
        onRequestTranscript: onRequestTranscript,
      );
    }
    return ImageBubble(
      message: message,
      onRetry: message.failed ? onRetry : null,
    );
  }

  Widget _quote(BuildContext context, bool mine) {
    final quoted = message.replyTo!;
    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      padding: const EdgeInsets.only(left: AppSpacing.sm),
      decoration: BoxDecoration(
        border: Border(
          left: BorderSide(
            width: 2.5,
            color: mine
                ? Colors.white.withValues(alpha: 0.7)
                : AppColors.warmCoral,
          ),
        ),
      ),
      child: Text(
        quoted.isDeleted ? 'Deleted message' : quoted.body,
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
          color: mine
              ? Colors.white.withValues(alpha: 0.85)
              : AppColors.softCharcoal.withValues(alpha: 0.7),
          fontStyle: quoted.isDeleted ? FontStyle.italic : FontStyle.normal,
        ),
      ),
    );
  }

  Widget _systemLine(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.lg,
                vertical: AppSpacing.sm,
              ),
              decoration: BoxDecoration(
                color: AppColors.calmSurface,
                borderRadius: BorderRadius.circular(AppRadii.pill),
              ),
              child: Text(
                message.body,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _sticker() {
    final sticker = stickerById(message.sticker);
    // An id this build does not know — sent from a newer client, or a pack we
    // retired. Say so rather than rendering an empty bubble; a message that
    // silently disappears is worse than one that admits it cannot be shown.
    if (sticker == null) {
      return const Text('Sticker', style: TextStyle(fontSize: 14));
    }
    return Text(
      sticker.glyph,
      // Names the sticker for a screen reader in place of the glyph, which
      // would otherwise be announced by its Unicode name ("person in bed").
      semanticsLabel: sticker.label,
      style: const TextStyle(fontSize: 44),
    );
  }

  Widget _reactions(bool mine) {
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.sm),
      child: Wrap(
        spacing: AppSpacing.xs,
        children: [
          for (final group in message.reactions)
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.sm,
                vertical: 2,
              ),
              decoration: BoxDecoration(
                color: mine
                    ? Colors.white.withValues(alpha: 0.22)
                    : AppColors.softRose.withValues(alpha: 0.25),
                borderRadius: BorderRadius.circular(AppRadii.pill),
              ),
              child: Text(
                group.count > 1
                    ? '${group.emoji} ${group.count}'
                    : group.emoji,
                style: const TextStyle(fontSize: 12),
              ),
            ),
        ],
      ),
    );
  }

}

/// The tick line under a message you sent.
///
/// The glyph carries the state for anyone who already reads ticks fluently;
/// the word next to it carries the state for everyone else, and only on the
/// newest message, where it answers the question people are actually asking.
class _StatusFooter extends StatelessWidget {
  final MessageStatus status;
  final bool showLabel;
  final VoidCallback onRetry;

  const _StatusFooter({
    required this.status,
    required this.showLabel,
    required this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    // A failed send is the one state that is worth interrupting for, because
    // it is the only one the user can do something about.
    if (status == MessageStatus.failed) {
      return GestureDetector(
        onTap: onRetry,
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.error_outline_rounded,
              size: 14,
              color: AppColors.error,
            ),
            const SizedBox(width: AppSpacing.xs),
            Text(
              'Not delivered — tap to retry',
              style: Theme.of(
                context,
              ).textTheme.labelSmall?.copyWith(color: AppColors.error),
            ),
          ],
        ),
      );
    }

    final muted = AppColors.softCharcoal.withValues(alpha: 0.45);
    final (icon, color, label) = switch (status) {
      MessageStatus.sending => (
        Icons.schedule_rounded,
        muted,
        'Sending…',
      ),
      MessageStatus.sent => (Icons.check_rounded, muted, 'Sent'),
      MessageStatus.delivered => (Icons.done_all_rounded, muted, 'Delivered'),
      MessageStatus.seen => (
        Icons.done_all_rounded,
        AppColors.seenTick,
        'Seen',
      ),
      MessageStatus.failed => (Icons.error_outline_rounded, muted, ''),
    };

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (showLabel) ...[
          Text(
            label,
            style: Theme.of(
              context,
            ).textTheme.labelSmall?.copyWith(color: color),
          ),
          const SizedBox(width: AppSpacing.xs),
        ],
        Icon(
          icon,
          size: 14,
          color: color,
          // Ticks are decorative once the label is present; without it they
          // are the only signal, so they need a name a screen reader can say.
          semanticLabel: showLabel ? null : label,
        ),
      ],
    );
  }
}

/// Private guidance after receiving something hard. Only this user sees it.
class _CoachStrip extends StatelessWidget {
  final String? guidance;
  final bool defersToSupport;
  final VoidCallback onDismiss;

  const _CoachStrip({
    required this.guidance,
    required this.defersToSupport,
    required this.onDismiss,
  });

  @override
  Widget build(BuildContext context) {
    final supportMode = defersToSupport;
    return Container(
      margin: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        0,
        AppSpacing.lg,
        AppSpacing.sm,
      ),
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: BoxDecoration(
        color: supportMode ? AppColors.noticeSurface : AppColors.calmSurface,
        borderRadius: BorderRadius.circular(AppRadii.md),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            supportMode
                ? Icons.volunteer_activism_outlined
                : Icons.lightbulb_outline_rounded,
            size: 16,
            color: supportMode ? AppColors.noticeInk : AppColors.calmTeal,
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              supportMode
                  ? 'That sounded heavy. If it would help, support is a tap away.'
                  : guidance ?? '',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
          if (supportMode)
            TextButton(
              onPressed: () => Navigator.of(context).pushNamed('/safety'),
              child: const Text('Support'),
            ),
          IconButton(
            icon: const Icon(Icons.close_rounded, size: 16),
            color: AppColors.softCharcoal.withValues(alpha: 0.5),
            onPressed: onDismiss,
            tooltip: 'Dismiss',
          ),
        ],
      ),
    );
  }
}

class _ReplyPreviewStrip extends StatelessWidget {
  final CoupleMessage message;
  final VoidCallback onCancel;

  const _ReplyPreviewStrip({required this.message, required this.onCancel});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        AppSpacing.sm,
        AppSpacing.sm,
        AppSpacing.sm,
      ),
      color: AppColors.softRose.withValues(alpha: 0.15),
      child: Row(
        children: [
          Container(width: 2.5, height: 30, color: AppColors.warmCoral),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              message.body,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
          IconButton(
            icon: const Icon(Icons.close_rounded, size: 18),
            onPressed: onCancel,
            tooltip: 'Cancel reply',
          ),
        ],
      ),
    );
  }
}

class _Composer extends StatelessWidget {
  final TextEditingController controller;
  final bool sending;
  final VoidCallback onSend;
  final VoidCallback onStickers;
  final VoidCallback onAttach;

  /// Whether the composer has any text. Drives the mic⇄send swap, which is the
  /// single gesture that makes voice feel native rather than bolted on.
  final bool hasText;

  final VoidCallback onStartRecording;
  final void Function(Offset delta) onRecordDrag;
  final VoidCallback onRecordRelease;

  /// While true the input row is replaced by the recording bar.
  final bool recording;
  final Widget recorderBar;

  const _Composer({
    required this.controller,
    required this.sending,
    required this.onSend,
    required this.onStickers,
    required this.onAttach,
    required this.hasText,
    required this.onStartRecording,
    required this.onRecordDrag,
    required this.onRecordRelease,
    required this.recording,
    required this.recorderBar,
  });

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          AppSpacing.lg,
          AppSpacing.sm,
          AppSpacing.lg,
          AppSpacing.md,
        ),
        // The recorder bar stays in the tree even when idle, where it renders
        // nothing. Its GlobalKey is how the mic button starts a recording, and
        // a key pointing at an unmounted widget resolves to null — the press
        // would silently do nothing.
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            recorderBar,
            if (!recording)
              Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  IconButton(
                    key: const Key('sticker_button'),
                    onPressed: onStickers,
                    icon: const Icon(Icons.emoji_emotions_outlined),
                    color: AppColors.softCharcoal.withValues(alpha: 0.5),
                    tooltip: 'Stickers',
                  ),
                  IconButton(
                    key: const Key('attach_button'),
                    onPressed: onAttach,
                    icon: const Icon(Icons.add_photo_alternate_outlined),
                    color: AppColors.softCharcoal.withValues(alpha: 0.5),
                    tooltip: 'Photo',
                  ),
                  Expanded(
                    child: TextField(
                      controller: controller,
                      minLines: 1,
                      maxLines: 5,
                      textCapitalization: TextCapitalization.sentences,
                      decoration: InputDecoration(
                        hintText: 'Message',
                        filled: true,
                        fillColor: Colors.white,
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.lg,
                          vertical: AppSpacing.md,
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(AppRadii.lg),
                          borderSide: BorderSide(
                            color: AppColors.softCharcoal.withValues(alpha: 0.1),
                          ),
                        ),
                        focusedBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(AppRadii.lg),
                          borderSide: const BorderSide(color: AppColors.warmCoral),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  // The swap. Empty composer offers the mic; the first
                  // character turns it into send. Same position, same size, so
                  // the thumb never has to look for it.
                  AnimatedSwitcher(
                    duration: const Duration(milliseconds: 150),
                    transitionBuilder: (child, animation) =>
                        ScaleTransition(scale: animation, child: child),
                    child: hasText || sending
                        ? _sendButton()
                        : _micButton(),
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }

  Widget _sendButton() {
    return IconButton(
      key: const Key('send_button'),
      onPressed: sending ? null : onSend,
      tooltip: 'Send',
      icon: sending
          ? const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: AppColors.warmCoral,
              ),
            )
          : const Icon(Icons.arrow_upward_rounded),
      style: IconButton.styleFrom(
        backgroundColor: AppColors.warmCoral,
        foregroundColor: Colors.white,
        disabledBackgroundColor: AppColors.warmCoral.withValues(alpha: 0.4),
        padding: const EdgeInsets.all(AppSpacing.md),
      ),
    );
  }

  Widget _micButton() {
    // A long-press rather than a tap: a tap that starts recording is a tap
    // that records every time the thumb brushes the wrong place.
    return GestureDetector(
      key: const Key('mic_button'),
      onLongPress: onStartRecording,
      onLongPressMoveUpdate: (details) => onRecordDrag(details.offsetFromOrigin),
      onLongPressEnd: (_) => onRecordRelease(),
      onLongPressCancel: onRecordRelease,
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: const BoxDecoration(
          color: AppColors.warmCoral,
          shape: BoxShape.circle,
        ),
        child: const Icon(Icons.mic_rounded, color: Colors.white),
      ),
    );
  }
}
