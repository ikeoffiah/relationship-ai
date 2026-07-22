import 'dart:async';
import 'package:flutter/material.dart';
import 'package:mobile/core/api_services/joint_session_api_service.dart';

enum JointSessionStatus {
  pendingA,
  pendingB,
  active,
  exited,
  terminated,
  none
}

class JointSessionViewModel extends ChangeNotifier {
  final JointSessionApiService _apiService;

  JointSessionViewModel({JointSessionApiService? apiService})
      : _apiService = apiService ?? JointSessionApiService();
  
  JointSessionStatus _status = JointSessionStatus.none;
  String? _sessionId;
  bool _partnerConfirmed = false;
  bool _isActionLoading = false;
  Timer? _pollingTimer;

  JointSessionStatus get status => _status;
  String? get sessionId => _sessionId;
  bool get partnerConfirmed => _partnerConfirmed;
  bool get isActionLoading => _isActionLoading;

  Future<bool> initiateJointSession() async {
    _isActionLoading = true;
    notifyListeners();

    try {
      final data = await _apiService.initiateJointSession();
      _sessionId = data['joint_session_id'];
      _status = JointSessionStatus.pendingA;
      _startPolling();
      _isActionLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      debugPrint('Initiate failed: $e');
    }

    _isActionLoading = false;
    notifyListeners();
    return false;
  }

  Future<void> confirmReady() async {
    if (_sessionId == null) return;
    _isActionLoading = true;
    notifyListeners();

    try {
      final data = await _apiService.confirmReady(_sessionId!);
      _partnerConfirmed = data['partner_confirmed'];
      if (data['both_confirmed']) {
        _status = JointSessionStatus.active;
        _stopPolling();
      } else {
        _status = JointSessionStatus.pendingB;
      }
    } catch (e) {
      debugPrint('Confirm failed: $e');
    }

    _isActionLoading = false;
    notifyListeners();
  }

  Future<void> exitSession() async {
    if (_sessionId == null) return;
    
    try {
      await _apiService.exitSession(_sessionId!);
      _status = JointSessionStatus.exited;
      _stopPolling();
      notifyListeners();
    } catch (e) {
      debugPrint('Exit failed: $e');
    }
  }

  void _startPolling() {
    _pollingTimer?.cancel();
    _pollingTimer = Timer.periodic(const Duration(seconds: 3), (timer) async {
      if (_sessionId == null) return;

      try {
        final data = await _apiService.getSessionStatus(_sessionId!);
        _partnerConfirmed = data['partner_confirmed'];
        
        final newStateStr = data['state'];
        if (newStateStr == 'ACTIVE') {
          _status = JointSessionStatus.active;
          _stopPolling();
        } else if (newStateStr == 'TERMINATED') {
          _status = JointSessionStatus.terminated;
          _stopPolling();
        }
        notifyListeners();
      } catch (e) {
        debugPrint('Poll failed: $e');
      }
    });
  }

  void _stopPolling() {
    _pollingTimer?.cancel();
    _pollingTimer = null;
  }

  @override
  void dispose() {
    _stopPolling();
    super.dispose();
  }
}
