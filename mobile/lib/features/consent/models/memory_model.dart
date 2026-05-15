import 'package:intl/intl.dart';

enum MemoryZone {
  private,
  shared,
  therapist;

  String get label {
    switch (this) {
      case MemoryZone.private: return 'Private';
      case MemoryZone.shared: return 'Shared';
      case MemoryZone.therapist: return 'Therapist';
    }
  }
}

class MemoryModel {
  final String id;
  final String title;
  final String whyStored;
  final DateTime createdAt;
  final MemoryZone zone;

  const MemoryModel({
    required this.id,
    required this.title,
    required this.whyStored,
    required this.createdAt,
    this.zone = MemoryZone.private,
  });

  factory MemoryModel.fromJson(Map<String, dynamic> json) {
    MemoryZone zone;
    switch (json['zone']) {
      case 'shared': zone = MemoryZone.shared; break;
      case 'therapist': zone = MemoryZone.therapist; break;
      default: zone = MemoryZone.private;
    }

    return MemoryModel(
      id: json['id'] as String,
      title: json['title'] as String,
      whyStored: json['why_stored'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      zone: zone,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'why_stored': whyStored,
        'created_at': createdAt.toIso8601String(),
        'zone': zone.name,
      };

  String get formattedDate => DateFormat('MMM d, y').format(createdAt);

  MemoryModel copyWith({
    String? title,
    String? whyStored,
    DateTime? createdAt,
    MemoryZone? zone,
  }) {
    return MemoryModel(
      id: id,
      title: title ?? this.title,
      whyStored: whyStored ?? this.whyStored,
      createdAt: createdAt ?? this.createdAt,
      zone: zone ?? this.zone,
    );
  }
}
