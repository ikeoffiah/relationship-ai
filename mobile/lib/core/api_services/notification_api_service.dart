import 'package:mobile/core/api_services/base_api_service.dart';

/// API service for the in-app notification center.
class NotificationApiService extends BaseApiService {
  NotificationApiService({super.injectedDio});

  // ── List ──────────────────────────────────────────────────────────────

  /// Fetch a paginated list of notifications, newest first.
  Future<Map<String, dynamic>> getNotifications(
    String userId, {
    int page = 1,
    int limit = 20,
  }) async {
    try {
      final response = await dio.get(
        '/api/v1/users/$userId/notifications',
        queryParameters: {'page': page, 'limit': limit},
      );
      return response.data;
    } catch (e) {
      throw handleError(e);
    }
  }

  // ── Unread count ──────────────────────────────────────────────────────

  /// Returns the number of unread notifications (for the badge).
  Future<int> getUnreadCount(String userId) async {
    try {
      final response = await dio.get(
        '/api/v1/users/$userId/notifications/unread-count',
      );
      return response.data['count'] ?? 0;
    } catch (e) {
      throw handleError(e);
    }
  }

  // ── Mark read ─────────────────────────────────────────────────────────

  /// Mark a single notification as read.
  Future<void> markAsRead(String notificationId) async {
    try {
      await dio.put('/api/v1/notifications/$notificationId/read');
    } catch (e) {
      throw handleError(e);
    }
  }

  /// Mark all notifications as read for a user.
  Future<void> markAllAsRead(String userId) async {
    try {
      await dio.put('/api/v1/users/$userId/notifications/read-all');
    } catch (e) {
      throw handleError(e);
    }
  }

  // ── Delete ────────────────────────────────────────────────────────────

  /// Delete a single notification.
  Future<void> deleteNotification(String notificationId) async {
    try {
      await dio.delete('/api/v1/notifications/$notificationId');
    } catch (e) {
      throw handleError(e);
    }
  }
}
