import 'package:intl/intl.dart';

// ---------------------------------------------------------------------------
// MemoryType enum (REL-89)
// ---------------------------------------------------------------------------

enum MemoryType {
  communicationStyle,
  trigger,
  conflictPattern,
  repairEvent,
  statedNeed,
  unknown;

  String get label {
    switch (this) {
      case MemoryType.communicationStyle:
        return 'Communication';
      case MemoryType.trigger:
        return 'Trigger';
      case MemoryType.conflictPattern:
        return 'Conflict';
      case MemoryType.repairEvent:
        return 'Repair';
      case MemoryType.statedNeed:
        return 'Need';
      case MemoryType.unknown:
        return 'Other';
    }
  }

  static MemoryType fromJson(String? value) {
    switch (value) {
      case 'communication_style':
        return MemoryType.communicationStyle;
      case 'trigger':
        return MemoryType.trigger;
      case 'conflict_pattern':
        return MemoryType.conflictPattern;
      case 'repair_event':
        return MemoryType.repairEvent;
      case 'stated_need':
        return MemoryType.statedNeed;
      default:
        return MemoryType.unknown;
    }
  }

  String toJson() {
    switch (this) {
      case MemoryType.communicationStyle:
        return 'communication_style';
      case MemoryType.trigger:
        return 'trigger';
      case MemoryType.conflictPattern:
        return 'conflict_pattern';
      case MemoryType.repairEvent:
        return 'repair_event';
      case MemoryType.statedNeed:
        return 'stated_need';
      case MemoryType.unknown:
        return 'unknown';
    }
  }
}

// ---------------------------------------------------------------------------
// MemoryZone enum (unchanged)
// ---------------------------------------------------------------------------

enum MemoryZone {
  private,
  shared,
  therapist;

  String get label {
    switch (this) {
      case MemoryZone.private:
        return 'Private';
      case MemoryZone.shared:
        return 'Shared';
      case MemoryZone.therapist:
        return 'Therapist';
    }
  }
}

// ---------------------------------------------------------------------------
// MemoryModel
// ---------------------------------------------------------------------------

class MemoryModel {
  final String id;

  /// Primary display text (full content). Maps to backend `content` field.
  final String title;

  final String whyStored;
  final DateTime createdAt;
  final MemoryZone zone;

  // REL-89: structured memory type
  final MemoryType memoryType;

  // REL-89: first 50 chars of content for dashboard preview (plaintext)
  final String? contentPreview;

  const MemoryModel({
    required this.id,
    required this.title,
    required this.whyStored,
    required this.createdAt,
    this.zone = MemoryZone.private,
    this.memoryType = MemoryType.unknown,
    this.contentPreview,
  });

  factory MemoryModel.fromJson(Map<String, dynamic> json) {
    MemoryZone zone;
    switch (json['zone']) {
      case 'shared':
        zone = MemoryZone.shared;
        break;
      case 'therapist':
        zone = MemoryZone.therapist;
        break;
      default:
        zone = MemoryZone.private;
    }

    return MemoryModel(
      id: json['id'] as String,
      title: json['title'] as String,
      whyStored: json['why_stored'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      zone: zone,
      memoryType: MemoryType.fromJson(json['memory_type'] as String?),
      contentPreview: json['content_preview'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'why_stored': whyStored,
        'created_at': createdAt.toIso8601String(),
        'zone': zone.name,
        'memory_type': memoryType.toJson(),
        'content_preview': contentPreview,
      };

  String get formattedDate => DateFormat('MMM d, y').format(createdAt);

  MemoryModel copyWith({
    String? title,
    String? whyStored,
    DateTime? createdAt,
    MemoryZone? zone,
    MemoryType? memoryType,
    String? contentPreview,
  }) {
    return MemoryModel(
      id: id,
      title: title ?? this.title,
      whyStored: whyStored ?? this.whyStored,
      createdAt: createdAt ?? this.createdAt,
      zone: zone ?? this.zone,
      memoryType: memoryType ?? this.memoryType,
      contentPreview: contentPreview ?? this.contentPreview,
    );
  }
}
