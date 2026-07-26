import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/api_services/settings_api_service.dart';
import 'package:mobile/core/services/biometric_service.dart';
import 'package:mobile/features/settings/viewmodels/settings_viewmodel.dart';
import 'package:mocktail/mocktail.dart';

class MockBiometricService extends Mock implements BiometricService {}

class MockSettingsApiService extends Mock implements SettingsApiService {}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late MockBiometricService biometric;
  late SettingsViewModel vm;

  setUp(() {
    biometric = MockBiometricService();
    vm = SettingsViewModel(apiService: MockSettingsApiService(), biometric: biometric);
  });

  test('enabling requires availability AND a successful auth', () async {
    when(() => biometric.canCheckBiometrics()).thenAnswer((_) async => true);
    when(() => biometric.authenticate(localizedReason: any(named: 'localizedReason')))
        .thenAnswer((_) async => true);

    final result = await vm.setBiometricEnabled(true);
    expect(result, isTrue);
    expect(vm.biometricEnabled, isTrue);
    verify(() => biometric.authenticate(localizedReason: any(named: 'localizedReason'))).called(1);
  });

  test('enabling is refused when the device cannot do biometrics', () async {
    when(() => biometric.canCheckBiometrics()).thenAnswer((_) async => false);

    final result = await vm.setBiometricEnabled(true);
    expect(result, isFalse);
    expect(vm.biometricEnabled, isFalse);
    expect(vm.errorMessage, contains('available'));
    // Never even prompts if unavailable.
    verifyNever(() => biometric.authenticate(localizedReason: any(named: 'localizedReason')));
  });

  test('a failed/cancelled auth leaves it disabled', () async {
    when(() => biometric.canCheckBiometrics()).thenAnswer((_) async => true);
    when(() => biometric.authenticate(localizedReason: any(named: 'localizedReason')))
        .thenAnswer((_) async => false);

    final result = await vm.setBiometricEnabled(true);
    expect(result, isFalse);
    expect(vm.biometricEnabled, isFalse);
  });

  test('disabling needs no auth', () async {
    final result = await vm.setBiometricEnabled(false);
    expect(result, isFalse);
    expect(vm.biometricEnabled, isFalse);
    verifyNever(() => biometric.canCheckBiometrics());
  });
}
