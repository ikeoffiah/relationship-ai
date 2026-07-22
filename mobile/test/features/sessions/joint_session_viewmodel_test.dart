import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/api_services/joint_session_api_service.dart';
import 'package:mobile/features/sessions/joint_session_viewmodel.dart';
import 'package:mocktail/mocktail.dart';

class MockJointApi extends Mock implements JointSessionApiService {}

void main() {
  late MockJointApi api;
  late JointSessionViewModel vm;

  setUp(() {
    api = MockJointApi();
    vm = JointSessionViewModel(apiService: api);
  });

  tearDown(() => vm.dispose());

  test('initiate sets a session id and moves to pending', () async {
    when(() => api.initiateJointSession())
        .thenAnswer((_) async => {'joint_session_id': 'js-1'});
    // Polling reads status; keep it inert for the test.
    when(() => api.getSessionStatus(any())).thenAnswer(
      (_) async => {'partner_confirmed': false, 'state': 'PENDING_B'},
    );

    final ok = await vm.initiateJointSession();

    expect(ok, isTrue);
    expect(vm.sessionId, 'js-1');
    expect(vm.status, JointSessionStatus.pendingA);
  });

  test('confirm goes active only when both have confirmed', () async {
    when(() => api.initiateJointSession())
        .thenAnswer((_) async => {'joint_session_id': 'js-1'});
    when(() => api.getSessionStatus(any())).thenAnswer(
      (_) async => {'partner_confirmed': false, 'state': 'PENDING_B'},
    );
    await vm.initiateJointSession();

    // First confirm: partner not yet ready.
    when(() => api.confirmReady('js-1')).thenAnswer(
      (_) async => {'partner_confirmed': false, 'both_confirmed': false},
    );
    await vm.confirmReady();
    expect(vm.status, JointSessionStatus.pendingB);

    // Second confirm: both ready → active.
    when(() => api.confirmReady('js-1')).thenAnswer(
      (_) async => {'partner_confirmed': true, 'both_confirmed': true},
    );
    await vm.confirmReady();
    expect(vm.status, JointSessionStatus.active);
  });

  test('exit terminates the session', () async {
    when(() => api.initiateJointSession())
        .thenAnswer((_) async => {'joint_session_id': 'js-1'});
    when(() => api.getSessionStatus(any())).thenAnswer(
      (_) async => {'partner_confirmed': false, 'state': 'PENDING_B'},
    );
    when(() => api.exitSession('js-1')).thenAnswer((_) async {});
    await vm.initiateJointSession();

    await vm.exitSession();

    expect(vm.status, JointSessionStatus.exited);
  });

  test('confirm is a no-op before a session exists', () async {
    await vm.confirmReady();
    expect(vm.status, JointSessionStatus.none);
    verifyNever(() => api.confirmReady(any()));
  });
}
