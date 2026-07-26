/// Models for the in-chat tone coach (talks to the FastAPI /tone endpoints).
library;

class MoodRead {
  final String mood;
  final String intensity;
  final String summary;
  final String suggestion;
  final String disclaimer;

  const MoodRead({
    this.mood = 'unclear',
    this.intensity = 'medium',
    this.summary = '',
    this.suggestion = '',
    this.disclaimer = '',
  });

  factory MoodRead.fromJson(Map<String, dynamic> j) => MoodRead(
        mood: j['mood'] as String? ?? 'unclear',
        intensity: j['intensity'] as String? ?? 'medium',
        summary: j['summary'] as String? ?? '',
        suggestion: j['suggestion'] as String? ?? '',
        disclaimer: j['disclaimer'] as String? ?? '',
      );
}

/// Present only when the coach declined to rewrite (harm signals / writer in
/// distress) — carries a support message instead of rewrites.
class CoachSafety {
  final bool declined;
  final String reason;
  final String message;

  const CoachSafety({this.declined = true, this.reason = '', this.message = ''});

  factory CoachSafety.fromJson(Map<String, dynamic> j) => CoachSafety(
        declined: j['declined'] as bool? ?? true,
        reason: j['reason'] as String? ?? '',
        message: j['message'] as String? ?? '',
      );
}

class CoachResult {
  final String read;
  final String tone;
  final List<String> rewrites;
  final String disclaimer;
  final CoachSafety? safety;

  const CoachResult({
    this.read = '',
    this.tone = '',
    this.rewrites = const [],
    this.disclaimer = '',
    this.safety,
  });

  bool get declined => safety?.declined ?? false;

  factory CoachResult.fromJson(Map<String, dynamic> j) => CoachResult(
        read: j['read'] as String? ?? '',
        tone: j['tone'] as String? ?? '',
        rewrites: (j['rewrites'] as List?)?.map((e) => e.toString()).toList() ?? const [],
        disclaimer: j['disclaimer'] as String? ?? '',
        safety: j['safety'] != null
            ? CoachSafety.fromJson(j['safety'] as Map<String, dynamic>)
            : null,
      );
}
