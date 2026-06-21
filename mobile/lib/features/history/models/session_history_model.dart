/// Data models for the Session History feature (REL-95).
library session_history_model;

enum SessionType { individual, joint, relay, unknown }

extension SessionTypeX on SessionType {
  String get label {
    switch (this) {
      case SessionType.individual:
        return 'Individual';
      case SessionType.joint:
        return 'Joint';
      case SessionType.relay:
        return 'Relay';
      case SessionType.unknown:
        return 'Session';
    }
  }

  String get filterValue {
    switch (this) {
      case SessionType.individual:
        return 'individual';
      case SessionType.joint:
        return 'joint';
      case SessionType.relay:
        return 'relay';
      case SessionType.unknown:
        return 'all';
    }
  }

  static SessionType fromString(String? value) {
    switch (value?.toLowerCase()) {
      case 'individual':
        return SessionType.individual;
      case 'joint':
        return SessionType.joint;
      case 'relay':
        return SessionType.relay;
      default:
        return SessionType.unknown;
    }
  }
}

/// A lightweight representation of a past session used in the list view.
class SessionHistoryItem {
  final String id;
  final SessionType type;
  final DateTime dateTime;
  final int turnCount;
  final String summaryPreview;
  final String? relayFromPartner;

  const SessionHistoryItem({
    required this.id,
    required this.type,
    required this.dateTime,
    required this.turnCount,
    required this.summaryPreview,
    this.relayFromPartner,
  });

  factory SessionHistoryItem.fromJson(Map<String, dynamic> json) {
    final rawSummary =
        (json['summary_preview'] ?? json['summary'] ?? '') as String;
    return SessionHistoryItem(
      id: json['id'] as String,
      type: SessionTypeX.fromString(json['type'] as String?),
      dateTime: DateTime.tryParse(json['created_at'] as String? ?? '') ??
          DateTime.now(),
      turnCount: (json['turn_count'] ?? 0) as int,
      summaryPreview: rawSummary.length > 100
          ? '${rawSummary.substring(0, 100)}…'
          : rawSummary,
      relayFromPartner: json['relay_from_partner'] as String?,
    );
  }
}

/// Full session detail including summary and memories.
class SessionDetail {
  final String id;
  final SessionType type;
  final DateTime dateTime;
  final int turnCount;
  final int durationMinutes;
  final String summary;
  final List<String> frameworks;

  const SessionDetail({
    required this.id,
    required this.type,
    required this.dateTime,
    required this.turnCount,
    required this.durationMinutes,
    required this.summary,
    required this.frameworks,
  });

  factory SessionDetail.fromJson(Map<String, dynamic> json) {
    final rawFrameworks = json['frameworks'] ?? json['framework_tags'] ?? [];
    return SessionDetail(
      id: json['id'] as String? ?? json['session_id'] as String? ?? '',
      type: SessionTypeX.fromString(json['type'] as String?),
      dateTime: DateTime.tryParse(json['created_at'] as String? ?? '') ??
          DateTime.now(),
      turnCount: (json['turn_count'] ?? 0) as int,
      durationMinutes: (json['duration_minutes'] ?? 0) as int,
      summary: (json['summary'] ?? '') as String,
      frameworks: (rawFrameworks as List).map((e) => e.toString()).toList(),
    );
  }
}

/// A single memory item extracted from a session.
class SessionMemory {
  final String id;
  final String content;
  final String category;
  final String sessionId;
  final bool isEditing;

  const SessionMemory({
    required this.id,
    required this.content,
    required this.category,
    required this.sessionId,
    this.isEditing = false,
  });

  SessionMemory copyWith({
    String? content,
    bool? isEditing,
  }) {
    return SessionMemory(
      id: id,
      content: content ?? this.content,
      category: category,
      sessionId: sessionId,
      isEditing: isEditing ?? this.isEditing,
    );
  }

  factory SessionMemory.fromJson(Map<String, dynamic> json) {
    return SessionMemory(
      id: json['id'] as String,
      content: (json['content'] ?? json['value'] ?? '') as String,
      category: (json['category'] ?? json['memory_type'] ?? 'general') as String,
      sessionId: (json['session_id'] ?? '') as String,
    );
  }
}
