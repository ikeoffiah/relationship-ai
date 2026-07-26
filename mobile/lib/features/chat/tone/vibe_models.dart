/// Model for the daily conversation "vibe" (FastAPI /tone/vibe).
library;

class DailyVibe {
  final String label;
  final String emoji;
  final String blurb;
  final String disclaimer;

  const DailyVibe({
    this.label = 'Quiet',
    this.emoji = '🌙',
    this.blurb = '',
    this.disclaimer = '',
  });

  factory DailyVibe.fromJson(Map<String, dynamic> j) => DailyVibe(
        label: j['label'] as String? ?? 'Quiet',
        emoji: j['emoji'] as String? ?? '🌙',
        blurb: j['blurb'] as String? ?? '',
        disclaimer: j['disclaimer'] as String? ?? '',
      );
}
