/// Models for the @bliss assistant (talks to the Django engagement API).
library;

/// A parsed-but-unsaved draft returned by POST bliss/interpret.
class BlissDraft {
  final String kind; // 'reminder' | 'event'
  final String title;
  final DateTime? dueAt;
  final bool hasTime;

  const BlissDraft({
    required this.kind,
    required this.title,
    this.dueAt,
    this.hasTime = false,
  });

  factory BlissDraft.fromJson(Map<String, dynamic> j) => BlissDraft(
        kind: j['kind'] as String? ?? 'reminder',
        title: j['title'] as String? ?? '',
        dueAt: j['due_at'] != null ? DateTime.tryParse(j['due_at'] as String) : null,
        hasTime: j['has_time'] as bool? ?? false,
      );

  BlissDraft copyWith({String? kind, String? title, DateTime? dueAt, bool? hasTime}) => BlissDraft(
        kind: kind ?? this.kind,
        title: title ?? this.title,
        dueAt: dueAt ?? this.dueAt,
        hasTime: hasTime ?? this.hasTime,
      );
}

/// A persisted reminder or calendar event shared by the couple.
class BlissItem {
  final String id;
  final String kind;
  final String title;
  final DateTime? dueAt;
  final String status; // 'pending' | 'done' | 'cancelled'
  final String source;

  const BlissItem({
    required this.id,
    this.kind = 'reminder',
    this.title = '',
    this.dueAt,
    this.status = 'pending',
    this.source = 'bliss',
  });

  bool get isEvent => kind == 'event';

  factory BlissItem.fromJson(Map<String, dynamic> j) => BlissItem(
        id: j['id'] as String,
        kind: j['kind'] as String? ?? 'reminder',
        title: j['title'] as String? ?? '',
        dueAt: j['due_at'] != null ? DateTime.tryParse(j['due_at'] as String) : null,
        status: j['status'] as String? ?? 'pending',
        source: j['source'] as String? ?? 'bliss',
      );
}
