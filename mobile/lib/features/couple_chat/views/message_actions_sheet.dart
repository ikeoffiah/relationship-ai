/// The menu a long press opens on a message.
///
/// Its own widget rather than a closure inside the screen, so it can be driven
/// directly. Buried in the screen it was only reachable through a long press
/// that the widget harness could not land reliably, which meant the one menu
/// containing "Delete" was the least tested thing in the thread.
library;

import 'package:flutter/material.dart';

import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_dimens.dart';
import 'package:mobile/features/couple_chat/models/couple_message.dart';

class MessageActionsSheet extends StatelessWidget {
  final CoupleMessage message;

  /// Whether the viewer wrote this message. Only the author may delete.
  final bool mine;

  final void Function(String emoji) onReact;
  final VoidCallback onReply;
  final VoidCallback onDelete;

  const MessageActionsSheet({
    super.key,
    required this.message,
    required this.mine,
    required this.onReact,
    required this.onReply,
    required this.onDelete,
  });

  /// Opens the sheet and runs whichever action was chosen.
  ///
  /// The callbacks fire *after* the sheet is dismissed, so a reply lands in a
  /// composer that is already visible rather than behind a closing sheet.
  static Future<void> show(
    BuildContext context, {
    required CoupleMessage message,
    required bool mine,
    required void Function(String emoji) onReact,
    required VoidCallback onReply,
    required VoidCallback onDelete,
  }) {
    return showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (_) => MessageActionsSheet(
        message: message,
        mine: mine,
        onReact: onReact,
        onReply: onReply,
        onDelete: onDelete,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.xl),
      decoration: const BoxDecoration(
        color: AppColors.creamWhite,
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadii.lg)),
      ),
      // The ListTiles below need a Material ancestor to draw their ink on. The
      // sheet paints its own background through a DecoratedBox, which is not
      // one — so without this the taps register but the ripple has nowhere to
      // go, and Flutter says so at runtime.
      child: Material(
        color: Colors.transparent,
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
                      Navigator.pop(context);
                      onReact(emoji);
                    },
                    child: Padding(
                      padding: const EdgeInsets.all(AppSpacing.sm),
                      child: Text(emoji, style: const TextStyle(fontSize: 30)),
                    ),
                  ),
              ],
            ),
            const Divider(height: AppSpacing.xxl),
            ListTile(
              key: const Key('action_reply'),
              leading: const Icon(Icons.reply_rounded, size: 20),
              title: const Text('Reply'),
              onTap: () {
                Navigator.pop(context);
                onReply();
              },
            ),
            if (mine)
              ListTile(
                key: const Key('action_delete'),
                leading: const Icon(Icons.delete_outline_rounded, size: 20),
                title: const Text('Delete'),
                onTap: () {
                  Navigator.pop(context);
                  onDelete();
                },
              ),
          ],
        ),
      ),
    );
  }
}
