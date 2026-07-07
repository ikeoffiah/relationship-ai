import 'package:flutter/material.dart';
import 'package:mobile/core/api_services/notification_api_service.dart';
import 'package:mobile/features/notifications/models/notification_model.dart';

class NotificationViewModel extends ChangeNotifier {
  final NotificationApiService _apiService;

  NotificationViewModel({NotificationApiService? apiService})
      : _apiService = apiService ?? NotificationApiService();

  List<NotificationItem> _notifications = [];
  int _unreadCount = 0;
  bool _isLoading = false;
  bool _isLoadingMore = false;
  String? _error;
  int _currentPage = 1;
  bool _hasMore = false;
  static const int _limit = 20;

  List<NotificationItem> get notifications => _notifications;
  int get unreadCount => _unreadCount;
  bool get isLoading => _isLoading;
  bool get isLoadingMore => _isLoadingMore;
  String? get error => _error;
  bool get isEmpty => _notifications.isEmpty;

  Future<void> fetchUnreadCount(String userId) async {
    try {
      _unreadCount = await _apiService.getUnreadCount(userId);
      notifyListeners();
    } catch (e) {
      debugPrint('Failed to load unread count: $e');
    }
  }

  Future<void> loadNotifications(String userId) async {
    _isLoading = true;
    _error = null;
    _currentPage = 1;
    notifyListeners();

    try {
      final data = await _apiService.getNotifications(userId, page: _currentPage, limit: _limit);
      final list = data['notifications'] as List;
      _notifications = list.map((x) => NotificationItem.fromJson(x)).toList();
      _hasMore = data['has_more'] ?? false;
      
      await fetchUnreadCount(userId);
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> loadMore(String userId) async {
    if (_isLoadingMore || !_hasMore) return;

    _isLoadingMore = true;
    notifyListeners();

    try {
      final nextPage = _currentPage + 1;
      final data = await _apiService.getNotifications(userId, page: nextPage, limit: _limit);
      final list = data['notifications'] as List;
      final newItems = list.map((x) => NotificationItem.fromJson(x)).toList();

      _notifications.addAll(newItems);
      _currentPage = nextPage;
      _hasMore = data['has_more'] ?? false;
    } catch (e) {
      debugPrint('Failed to load more notifications: $e');
    } finally {
      _isLoadingMore = false;
      notifyListeners();
    }
  }

  Future<void> refresh(String userId) async {
    await loadNotifications(userId);
  }

  Future<void> markAsRead(String userId, String notificationId) async {
    // Optimistic Update
    final index = _notifications.indexWhere((x) => x.id == notificationId);
    if (index != -1 && !_notifications[index].read) {
      final prev = _notifications[index];
      _notifications[index] = prev.copyWith(read: true);
      if (_unreadCount > 0) _unreadCount--;
      notifyListeners();

      try {
        await _apiService.markAsRead(notificationId);
      } catch (e) {
        // Rollback
        _notifications[index] = prev;
        _unreadCount++;
        notifyListeners();
      }
    }
  }

  Future<void> markAllAsRead(String userId) async {
    if (_unreadCount == 0) return;

    final prevList = List<NotificationItem>.from(_notifications);
    final prevCount = _unreadCount;

    _notifications = _notifications.map((x) => x.copyWith(read: true)).toList();
    _unreadCount = 0;
    notifyListeners();

    try {
      await _apiService.markAllAsRead(userId);
    } catch (e) {
      _notifications = prevList;
      _unreadCount = prevCount;
      notifyListeners();
    }
  }

  Future<void> deleteNotification(String userId, String notificationId) async {
    final index = _notifications.indexWhere((x) => x.id == notificationId);
    if (index != -1) {
      final item = _notifications[index];
      final wasUnread = !item.read;

      _notifications.removeAt(index);
      if (wasUnread && _unreadCount > 0) _unreadCount--;
      notifyListeners();

      try {
        await _apiService.deleteNotification(notificationId);
      } catch (e) {
        // Rollback
        _notifications.insert(index, item);
        if (wasUnread) _unreadCount++;
        notifyListeners();
      }
    }
  }
}
