/// Model for a consensual Focus session (Django engagement API).
library;

class FocusSession {
  final String id;
  final String status; // proposed | active | ended | declined
  final int durationMinutes;
  final bool iInitiated;
  final DateTime? endsAt;
  final int? remainingSeconds;
  final bool isComplete;

  const FocusSession({
    required this.id,
    this.status = 'proposed',
    this.durationMinutes = 20,
    this.iInitiated = false,
    this.endsAt,
    this.remainingSeconds,
    this.isComplete = false,
  });

  bool get isProposed => status == 'proposed';
  bool get isActive => status == 'active';

  factory FocusSession.fromJson(Map<String, dynamic> j) => FocusSession(
        id: j['id'] as String? ?? '',
        status: j['status'] as String? ?? 'proposed',
        durationMinutes: j['duration_minutes'] as int? ?? 20,
        iInitiated: j['i_initiated'] as bool? ?? false,
        endsAt: j['ends_at'] != null ? DateTime.tryParse(j['ends_at'] as String) : null,
        remainingSeconds: j['remaining_seconds'] as int?,
        isComplete: j['is_complete'] as bool? ?? false,
      );

  /// Live seconds remaining, computed from [endsAt] against the device clock so
  /// the countdown ticks smoothly between server polls. Falls back to the
  /// server value.
  int liveRemaining(DateTime now) {
    if (endsAt != null) {
      return endsAt!.difference(now).inSeconds.clamp(0, 1 << 31);
    }
    return remainingSeconds ?? 0;
  }
}
