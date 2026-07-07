/// Notification types matching the backend enum.
enum NotificationType {
  sessionReminder('session_reminder', 'Session Reminder'),
  partnerJoined('partner_joined', 'Partner Joined'),
  relayReceived('relay_received', 'Relay Message'),
  insightDetected('insight_detected', 'Insight Detected'),
  safetyFollowup('safety_followup', 'Safety Follow-up'),
  therapistConnected('therapist_connected', 'Therapist Connected'),
  system('system', 'System');

  final String value;
  final String label;
  const NotificationType(this.value, this.label);

  static NotificationType fromString(String value) {
    return NotificationType.values.firstWhere(
      (e) => e.value == value,
      orElse: () => NotificationType.system,
    );
  }
}

/// A single in-app notification.
class NotificationItem {
  final String id;
  final String userId;
  final NotificationType type;
  final String title;
  final String body;
  final Map<String, dynamic> data;
  final bool read;
  final DateTime createdAt;

  const NotificationItem({
    required this.id,
    required this.userId,
    required this.type,
    required this.title,
    required this.body,
    required this.data,
    required this.read,
    required this.createdAt,
  });

  factory NotificationItem.fromJson(Map<String, dynamic> json) {
    return NotificationItem(
      id: json['id'] ?? '',
      userId: json['user_id'] ?? '',
      type: NotificationType.fromString(json['type'] ?? 'system'),
      title: json['title'] ?? '',
      body: json['body'] ?? '',
      data: json['data'] != null
          ? Map<String, dynamic>.from(json['data'])
          : {},
      read: json['read'] ?? false,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'])
          : DateTime.now(),
    );
  }

  NotificationItem copyWith({bool? read}) {
    return NotificationItem(
      id: id,
      userId: userId,
      type: type,
      title: title,
      body: body,
      data: data,
      read: read ?? this.read,
      createdAt: createdAt,
    );
  }
}
