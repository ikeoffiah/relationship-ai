import 'package:flutter/material.dart';

import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_dimens.dart';
import 'package:mobile/features/couple_chat/models/sticker_catalogue.dart';

/// The sticker tray.
///
/// One tap sends. There is no "pick, preview, confirm" — a sticker whose whole
/// value is being faster than typing does not get a three-step flow.
class StickerPickerSheet extends StatelessWidget {
  /// Whether the couple's mutual spicy consent is in place. The intimate pack
  /// is absent, not greyed out, when it is not: a locked row is an invitation
  /// to ask your partner why it is locked, which is pressure, and this gate
  /// exists specifically so that neither partner can apply it.
  final bool intimateUnlocked;
  final void Function(String stickerId) onPick;

  const StickerPickerSheet({
    required this.intimateUnlocked,
    required this.onPick,
    super.key,
  });

  static Future<void> show(
    BuildContext context, {
    required bool intimateUnlocked,
    required void Function(String stickerId) onPick,
  }) {
    return showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (_) => StickerPickerSheet(
        intimateUnlocked: intimateUnlocked,
        onPick: onPick,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final packs = kStickerPacks
        .where((pack) => intimateUnlocked || !pack.intimate)
        .toList();

    return Container(
      constraints: BoxConstraints(
        maxHeight: MediaQuery.of(context).size.height * 0.55,
      ),
      decoration: const BoxDecoration(
        color: AppColors.creamWhite,
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadii.lg)),
      ),
      child: SafeArea(
        top: false,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.xxl,
            AppSpacing.lg,
            AppSpacing.xxl,
            AppSpacing.xxl,
          ),
          children: [
            Center(
              child: Container(
                width: 36,
                height: 4,
                decoration: BoxDecoration(
                  color: AppColors.softCharcoal.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(AppRadii.pill),
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.xl),
            for (final pack in packs) ...[
              Text(
                pack.title,
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: AppColors.softCharcoal.withValues(alpha: 0.55),
                ),
              ),
              if (pack.key == 'repair')
                Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Text(
                    'For when the words are hard to find',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ),
              const SizedBox(height: AppSpacing.md),
              Wrap(
                spacing: AppSpacing.sm,
                runSpacing: AppSpacing.sm,
                children: [
                  for (final sticker in pack.stickers)
                    _StickerButton(
                      sticker: sticker,
                      onTap: () {
                        Navigator.pop(context);
                        onPick(sticker.id);
                      },
                    ),
                ],
              ),
              const SizedBox(height: AppSpacing.xl),
            ],
          ],
        ),
      ),
    );
  }
}

class _StickerButton extends StatelessWidget {
  final CoupleSticker sticker;
  final VoidCallback onTap;

  const _StickerButton({required this.sticker, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      child: InkWell(
        key: Key('sticker_${sticker.id}'),
        borderRadius: BorderRadius.circular(AppRadii.md),
        onTap: onTap,
        child: Container(
          width: 60,
          height: 60,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: AppColors.softRose.withValues(alpha: 0.14),
            borderRadius: BorderRadius.circular(AppRadii.md),
          ),
          child: Text(
            sticker.glyph,
            // Named rather than read as a glyph — an emoji announced by its
            // Unicode name ("person in bed") is not what was meant.
            semanticsLabel: sticker.label,
            style: const TextStyle(fontSize: 30),
          ),
        ),
      ),
    );
  }
}
