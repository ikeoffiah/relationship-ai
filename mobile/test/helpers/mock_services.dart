import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:mobile/core/api_services/auth_api_service.dart';
import 'package:mobile/core/services/biometric_service.dart';
import 'package:google_sign_in/google_sign_in.dart';

class MockAuthApiService extends Mock implements AuthApiService {}
class MockBiometricService extends Mock implements BiometricService {}
class MockGoogleSignIn extends Mock implements GoogleSignIn {}
class MockGoogleSignInAccount extends Mock implements GoogleSignInAccount {}
class MockGoogleSignInAuthentication extends Mock implements GoogleSignInAuthentication {}

/// Set up mocked MethodChannel for FlutterSecureStorage to avoid testing errors
void setupMockSecureStorage() {
  const MethodChannel channel = MethodChannel('plugins.it_nomads.com/flutter_secure_storage');
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
    .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
      return null; // Mock return for read, write, delete, deleteAll
  });
}
