import 'package:flutter/material.dart';
import 'package:mobile/core/api_services/relationship_api_service.dart';

enum RelationshipStatus {
  notConnected,
  pending,
  active,
  dissolved,
  loading
}

class RelationshipViewModel extends ChangeNotifier {
  final RelationshipApiService _apiService;

  RelationshipViewModel(this._apiService);

  RelationshipStatus _status = RelationshipStatus.loading;
  RelationshipStatus get status => _status;

  Map<String, dynamic>? _currentRelationship;
  Map<String, dynamic>? get currentRelationship => _currentRelationship;

  String? _errorMessage;
  String? get errorMessage => _errorMessage;

  bool _isActionLoading = false;
  bool get isActionLoading => _isActionLoading;

  Future<void> fetchRelationshipStatus() async {
    _status = RelationshipStatus.loading;
    notifyListeners();

    try {
      final data = await _apiService.getMyRelationship();
      _currentRelationship = data;
      
      if (data['status'] == 'not_connected') {
        _status = RelationshipStatus.notConnected;
      } else if (data['status'] == 'pending') {
        _status = RelationshipStatus.pending;
      } else if (data['status'] == 'active') {
        _status = RelationshipStatus.active;
      } else if (data['status'] == 'dissolved') {
        _status = RelationshipStatus.dissolved;
      }
      
      _errorMessage = null;
    } catch (e) {
      _errorMessage = e.toString();
      _status = RelationshipStatus.notConnected; // Default to not connected on error
    } finally {
      notifyListeners();
    }
  }

  Future<bool> sendInvite(String email) async {
    _isActionLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      await _apiService.invitePartner(email);
      await fetchRelationshipStatus();
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      return false;
    } finally {
      _isActionLoading = false;
      notifyListeners();
    }
  }

  Future<bool> acceptInvite(String token) async {
    _isActionLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      await _apiService.acceptInvite(token);
      await fetchRelationshipStatus();
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      return false;
    } finally {
      _isActionLoading = false;
      notifyListeners();
    }
  }

  Future<bool> dissolveRelationship() async {
    if (_currentRelationship == null || _currentRelationship!['id'] == null) return false;

    _isActionLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      await _apiService.dissolveRelationship(_currentRelationship!['id']);
      await fetchRelationshipStatus();
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      return false;
    } finally {
      _isActionLoading = false;
      notifyListeners();
    }
  }

  // --- Shared Context ---

  Map<String, dynamic>? _sharedContext;
  Map<String, dynamic>? get sharedContext => _sharedContext;

  Future<void> fetchSharedContext() async {
    if (_currentRelationship == null || _currentRelationship!['id'] == null) return;
    try {
      final context = await _apiService.getSharedContext(_currentRelationship!['id']);
      _sharedContext = context;
      notifyListeners();
    } catch (e) {
      _errorMessage = 'Failed to load shared context';
      notifyListeners();
    }
  }

  Future<void> addRepairEvent(String description, String sessionId) async {
    if (_currentRelationship == null || _currentRelationship!['id'] == null) return;
    try {
      await _apiService.addRepairEvent(_currentRelationship!['id'], description, sessionId);
      await fetchSharedContext();
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
    }
  }

  Future<void> addGoal(String description) async {
    if (_currentRelationship == null || _currentRelationship!['id'] == null) return;
    try {
      await _apiService.addGoal(_currentRelationship!['id'], description);
      await fetchSharedContext();
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
    }
  }
}
