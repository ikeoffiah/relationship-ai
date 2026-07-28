import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_dimens.dart';
import 'package:mobile/features/couple_chat/couple_chat_viewmodel.dart';
import 'package:mobile/features/couple_chat/models/couple_message.dart';
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
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final vm = context.read<CoupleChatViewModel>();
      vm.load().then((_) {
        vm.markRead();
        _jumpToLatest();
      });
    });
  }

  @override
  void dispose() {
    _composer.dispose();
    _scroll.dispose();
    super.dispose();
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
            title: Text(
              widget.partnerName,
              style: Theme.of(context).textTheme.titleLarge,
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
                            onLongPress: () => _showReactions(message),
                            onRetry: () => vm.retry(message),
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
                onSend: _handleSend,
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
  final VoidCallback onLongPress;
  final VoidCallback onRetry;

  const _Bubble({
    required this.message,
    required this.userId,
    required this.onLongPress,
    required this.onRetry,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    final mine = message.isMine(userId);
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: GestureDetector(
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
              if (message.isPending || message.failed) _status(context, mine),
            ],
          ),
        ),
      ),
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

  Widget _status(BuildContext context, bool mine) {
    if (message.failed) {
      return GestureDetector(
        onTap: onRetry,
        child: Padding(
          padding: const EdgeInsets.only(top: AppSpacing.xs),
          child: Text(
            'Not sent — tap to retry',
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: mine ? Colors.white : AppColors.error,
            ),
          ),
        ),
      );
    }
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.xs),
      child: Text(
        'Sending…',
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
          color: mine
              ? Colors.white.withValues(alpha: 0.8)
              : AppColors.softCharcoal.withValues(alpha: 0.5),
        ),
      ),
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

  const _Composer({
    required this.controller,
    required this.sending,
    required this.onSend,
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
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
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
            IconButton(
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
                disabledBackgroundColor: AppColors.warmCoral.withValues(
                  alpha: 0.4,
                ),
                padding: const EdgeInsets.all(AppSpacing.md),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
