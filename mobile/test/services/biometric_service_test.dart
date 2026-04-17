import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/services/biometric_service.dart';
import 'package:local_auth/local_auth.dart';

class FakeLocalAuthentication implements LocalAuthentication {
  bool canCheck = true;
  bool isSupported = true;
  bool authSuccess = true;
  List<BiometricType> types = [BiometricType.face];

  @override
  Future<bool> get canCheckBiometrics async => canCheck;

  @override
  Future<bool> isDeviceSupported() async => isSupported;

  @override
  Future<bool> authenticate({required String localizedReason, Iterable<dynamic>? authMessages, AuthenticationOptions options = const AuthenticationOptions()}) async {
    return authSuccess;
  }

  @override
  Future<List<BiometricType>> getAvailableBiometrics() async => types;
  
  @override
  Future<bool> stopAuthentication() async => true;
}

void main() {
  group('BiometricService Tests', () {
    test('canCheckBiometrics returns correctly', () async {
      final fakeAuth = FakeLocalAuthentication();
      final service = BiometricService(auth: fakeAuth);
      
      final result = await service.canCheckBiometrics();
      expect(result, true);
      
      fakeAuth.canCheck = false;
      fakeAuth.isSupported = false;
      final result2 = await service.canCheckBiometrics();
      expect(result2, false);
    });

    test('authenticate returns correctly', () async {
      final fakeAuth = FakeLocalAuthentication();
      final service = BiometricService(auth: fakeAuth);
      
      final result = await service.authenticate();
      expect(result, true);
    });

    test('getAvailableBiometrics returns correctly', () async {
      final fakeAuth = FakeLocalAuthentication();
      final service = BiometricService(auth: fakeAuth);
      
      final list = await service.getAvailableBiometrics();
      expect(list.length, 1);
      expect(list.contains(BiometricType.face), true);
    });
  });
}
