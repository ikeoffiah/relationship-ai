/// The stickers a couple can send each other.
///
/// These are large glyphs, not commissioned illustration — the model already
/// stores only an id and the art "ships with the client", so replacing the
/// glyph with a real asset later is a one-line change per sticker and no
/// migration. Calling them stickers now and drawing them later is the right
/// order: what a sticker set is *for* is worth getting right before what it
/// looks like.
///
/// Ids are stable strings, never indexes. A sticker's meaning is stored in the
/// thread forever; reordering this file must not silently rewrite what someone
/// said two years ago.
library;

class CoupleSticker {
  final String id;
  final String glyph;

  /// Read aloud by screen readers, and shown as the fallback if an id ever
  /// arrives that this build does not know about.
  final String label;

  const CoupleSticker({
    required this.id,
    required this.glyph,
    required this.label,
  });
}

class StickerPack {
  final String key;
  final String title;

  /// Whether this pack needs the couple's mutual spicy consent. Reuses the
  /// existing games gate rather than inventing a second one — both partners
  /// age-verified and both opted in, or it does not appear.
  final bool intimate;
  final List<CoupleSticker> stickers;

  const StickerPack({
    required this.key,
    required this.title,
    required this.stickers,
    this.intimate = false,
  });
}

/// The repair pack is the one that earns its place in *this* product rather
/// than in any chat app. Gottman's research is blunt about it: what separates
/// couples who last is not whether they fight, it is whether a repair attempt
/// gets made and accepted. Making the smallest possible repair a single tap —
/// at the exact moment when finding words is hardest — is the most useful
/// thing a sticker can do here.
const List<StickerPack> kStickerPacks = [
  StickerPack(
    key: 'love',
    title: 'Love',
    stickers: [
      CoupleSticker(id: 'love.heart', glyph: '❤️', label: 'Love you'),
      CoupleSticker(id: 'love.hearteyes', glyph: '😍', label: 'Heart eyes'),
      CoupleSticker(id: 'love.kiss', glyph: '😘', label: 'Kiss'),
      CoupleSticker(id: 'love.hug', glyph: '🤗', label: 'Hug'),
      CoupleSticker(id: 'love.blush', glyph: '🥰', label: 'Smitten'),
      CoupleSticker(id: 'love.bouquet', glyph: '💐', label: 'Flowers'),
      CoupleSticker(id: 'love.two', glyph: '💑', label: 'Us'),
      CoupleSticker(id: 'love.forever', glyph: '💞', label: 'Always'),
    ],
  ),
  StickerPack(
    key: 'repair',
    title: 'Repair',
    stickers: [
      CoupleSticker(id: 'repair.sorry', glyph: '🙏', label: "I'm sorry"),
      CoupleSticker(id: 'repair.pause', glyph: '⏸️', label: 'Can we pause'),
      CoupleSticker(id: 'repair.truce', glyph: '🤍', label: 'Truce'),
      CoupleSticker(id: 'repair.listening', glyph: '👂', label: "I'm listening"),
      CoupleSticker(id: 'repair.myfault', glyph: '🫱', label: 'That was on me'),
      CoupleSticker(id: 'repair.stillhere', glyph: '🫂', label: "I'm still here"),
    ],
  ),
  StickerPack(
    key: 'playful',
    title: 'Playful',
    stickers: [
      CoupleSticker(id: 'playful.wink', glyph: '😉', label: 'Wink'),
      CoupleSticker(id: 'playful.laugh', glyph: '😂', label: 'Laughing'),
      CoupleSticker(id: 'playful.smug', glyph: '😏', label: 'Smug'),
      CoupleSticker(id: 'playful.eyes', glyph: '👀', label: 'Eyes'),
      CoupleSticker(id: 'playful.party', glyph: '🎉', label: 'Celebrate'),
      CoupleSticker(id: 'playful.dance', glyph: '💃', label: 'Dancing'),
    ],
  ),
  StickerPack(
    key: 'close',
    title: 'Close',
    intimate: true,
    stickers: [
      CoupleSticker(id: 'close.fire', glyph: '🔥', label: 'Hot'),
      CoupleSticker(id: 'close.lips', glyph: '💋', label: 'Kiss mark'),
      CoupleSticker(id: 'close.bed', glyph: '🛏️', label: 'Come to bed'),
      CoupleSticker(id: 'close.tonight', glyph: '🌙', label: 'Tonight'),
      CoupleSticker(id: 'close.thinking', glyph: '🥵', label: 'Thinking of you'),
      CoupleSticker(id: 'close.wine', glyph: '🍷', label: 'Just us'),
    ],
  ),
];

final Map<String, CoupleSticker> _byId = {
  for (final pack in kStickerPacks)
    for (final sticker in pack.stickers) sticker.id: sticker,
};

/// Look up a sticker by the id stored on a message.
///
/// Returns null for an id this build does not know — a message sent from a
/// newer client, or a pack we later retire. The bubble renders a placeholder
/// rather than an empty gap, because a message that silently disappears is
/// worse than one that says it cannot be shown.
CoupleSticker? stickerById(String id) => _byId[id];
