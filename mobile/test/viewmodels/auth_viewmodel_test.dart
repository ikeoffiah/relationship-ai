import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';

import 'package:mobile/features/auth/models/responses/auth_response.dart';
import '../helpers/mock_services.dart';

void main() {
  late AuthViewModel authViewModel;
  late MockAuthApiService mockAuthService;
  late MockBiometricService mockBiometricService;
  late MockGoogleSignIn mockGoogleSignIn;

  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    setupMockSecureStorage();
  });

  setUp(() {
    mockAuthService = MockAuthApiService();
    mockBiometricService = MockBiometricService();
    mockGoogleSignIn = MockGoogleSignIn();

    authViewModel = AuthViewModel(
      authService: mockAuthService,
      biometricService: mockBiometricService,
      googleSignIn: mockGoogleSignIn,
    );
  });

  group('AuthViewModel Validation Logic', () {
    test('Initial state is correct', () {
      expect(authViewModel.isLoading, false);
      expect(authViewModel.errorMessage, null);
      expect(authViewModel.email, '');
      expect(authViewModel.password, '');
      expect(authViewModel.confirmPassword, '');
      expect(authViewModel.fullName, '');
    });

    test('setEmail clears error and sets value', () {
      authViewModel.setEmail('test@email.com');
      expect(authViewModel.email, 'test@email.com');
      expect(authViewModel.errorMessage, null);
    });

    test('setPassword clears error and sets value', () {
      authViewModel.setPassword('Password123');
      expect(authViewModel.password, 'Password123');
      expect(authViewModel.errorMessage, null);
    });

    test('validateLoginForm returns false for empty email', () {
      authViewModel.setEmail('');
      authViewModel.setPassword('password123');
      final result = authViewModel.validateLoginForm();
      expect(result, false);
      expect(authViewModel.errorMessage, 'Please enter your email');
    });

    test('validateLoginForm returns false for invalid email', () {
      authViewModel.setEmail('invalid_email');
      authViewModel.setPassword('password123');
      final result = authViewModel.validateLoginForm();
      expect(result, false);
      expect(authViewModel.errorMessage, 'Please enter a valid email');
    });

    test('validateLoginForm returns false for small password', () {
      authViewModel.setEmail('test@example.com');
      authViewModel.setPassword('123');
      final result = authViewModel.validateLoginForm();
      expect(result, false);
      expect(authViewModel.errorMessage, 'Password must be at least 6 characters');
    });

    test('validateSignupForm returns false for password mismatch', () {
      authViewModel.setFullName('Test User');
      authViewModel.setEmail('test@example.com');
      authViewModel.setPassword('password123');
      authViewModel.setConfirmPassword('password321');
      final result = authViewModel.validateSignupForm();
      expect(result, false);
      expect(authViewModel.errorMessage, 'Passwords do not match');
    });

    test('validateSignupForm returns false for empty full name', () {
      authViewModel.setFullName('');
      final result = authViewModel.validateSignupForm();
      expect(result, false);
      expect(authViewModel.errorMessage, 'Please enter your full name');
    });

    test('validateSignupForm returns false for short name', () {
      authViewModel.setFullName('A');
      final result = authViewModel.validateSignupForm();
      expect(result, false);
      expect(authViewModel.errorMessage, 'Name must be at least 2 characters');
    });

    test('validateSignupForm returns false for empty confirm password', () {
      authViewModel.setFullName('Test User');
      authViewModel.setEmail('test@example.com');
      authViewModel.setPassword('password123');
      authViewModel.setConfirmPassword('');
      final result = authViewModel.validateSignupForm();
      expect(result, false);
      expect(authViewModel.errorMessage, 'Please confirm your password');
    });

    test('resetForm resets all fields', () {
      authViewModel.setFullName('Test');
      authViewModel.setEmail('test@email.com');
      authViewModel.setPassword('pass123');
      authViewModel.setConfirmPassword('pass123');
      
      authViewModel.resetForm();
      
      expect(authViewModel.fullName, '');
      expect(authViewModel.email, '');
      expect(authViewModel.password, '');
      expect(authViewModel.confirmPassword, '');
      expect(authViewModel.isLoading, false);
    });
  });

  group('AuthViewModel API Calls', () {
    test('loginWithEmail triggers AuthApiService.login on successful validation', () async {
      authViewModel.setEmail('test@example.com');
      authViewModel.setPassword('password123');
      
      when(() => mockAuthService.login(any(), any()))
          .thenAnswer((_) async => AuthResponse(token: 'test_token', user: null));
          
      final result = await authViewModel.loginWithEmail();
      
      expect(result, true);
      expect(authViewModel.isLoading, false);
      verify(() => mockAuthService.login('test@example.com', 'password123')).called(1);
    });
    
    test('loginWithEmail catches exception and sets error', () async {
      authViewModel.setEmail('test@example.com');
      authViewModel.setPassword('password123');
      
      when(() => mockAuthService.login(any(), any()))
          .thenThrow(Exception('Invalid credentials'));
          
      final result = await authViewModel.loginWithEmail();
      
      expect(result, false);
      expect(authViewModel.isLoading, false);
      expect(authViewModel.errorMessage, 'Invalid credentials');
    });

    test('loginWithBiometrics fails if biometrics not available', () async {
      when(() => mockBiometricService.canCheckBiometrics()).thenAnswer((_) async => false);
      
      final result = await authViewModel.loginWithBiometrics();
      
      expect(result, false);
      expect(authViewModel.errorMessage, 'Biometrics are not supported or enrolled on this device.');
    });

    test('loginWithBiometrics succeeds if biometrics validates', () async {
      when(() => mockBiometricService.canCheckBiometrics()).thenAnswer((_) async => true);
      when(() => mockBiometricService.authenticate()).thenAnswer((_) async => true);
      
      final result = await authViewModel.loginWithBiometrics();
      
      expect(result, true);
      expect(authViewModel.email, 'biometric@user.com');
    });
    test('signupWithEmail triggers AuthApiService.signup', () async {
      authViewModel.setFullName('Test User');
      authViewModel.setEmail('test@example.com');
      authViewModel.setPassword('password123');
      authViewModel.setConfirmPassword('password123');
      
      when(() => mockAuthService.signup(any(), any(), any()))
          .thenAnswer((_) async => AuthResponse(token: 'test_token', user: null));
          
      final result = await authViewModel.signupWithEmail();
      expect(result, true);
      verify(() => mockAuthService.signup('Test User', 'test@example.com', 'password123')).called(1);
    });

    test('signInWithGoogle handles successful GoogleSignInAccount', () async {
      final mockAccount = MockGoogleSignInAccount();
      final mockAuth = MockGoogleSignInAuthentication();
      when(() => mockAccount.email).thenReturn('google@example.com');
      when(() => mockAccount.displayName).thenReturn('Google User');
      when(() => mockAccount.authentication).thenAnswer((_) async => mockAuth);
      when(() => mockAuth.idToken).thenReturn('google_id_token');
      when(() => mockGoogleSignIn.signIn()).thenAnswer((_) async => mockAccount);
      when(() => mockAuthService.googleSignIn(any()))
          .thenAnswer((_) async => AuthResponse(token: 'google_jwt', user: null));

      final result = await authViewModel.signInWithGoogle();
      
      expect(result, true);
      expect(authViewModel.email, 'google@example.com');
      expect(authViewModel.fullName, 'Google User');
      verify(() => mockAuthService.googleSignIn('google_id_token')).called(1);
    });

    test('logout clears user data and storage', () async {
      when(() => mockGoogleSignIn.signOut()).thenAnswer((_) async => null);
      when(() => mockAuthService.logout()).thenAnswer((_) async {});

      await authViewModel.logout();
      expect(authViewModel.email, '');
      verify(() => mockAuthService.logout()).called(1);
    });

    test('sendPasswordResetEmail triggers forgotPassword', () async {
      authViewModel.setEmail('test@example.com');
      when(() => mockAuthService.forgotPassword(any())).thenAnswer((_) async {});

      final result = await authViewModel.sendPasswordResetEmail();
      expect(result, true);
      verify(() => mockAuthService.forgotPassword('test@example.com')).called(1);
    });

    test('resetPassword triggers resetPassword', () async {
      authViewModel.setEmail('test@example.com');
      authViewModel.setPassword('newpassword123');
      authViewModel.setConfirmPassword('newpassword123');
      
      when(() => mockAuthService.resetPassword(any(), any())).thenAnswer((_) async {});

      final result = await authViewModel.resetPassword();
      expect(result, true);
      verify(() => mockAuthService.resetPassword('newpassword123', 'placeholder-token')).called(1);
    });

    test('resetPassword returns false for empty password', () async {
      authViewModel.setPassword('');
      final result = await authViewModel.resetPassword();
      expect(result, false);
      expect(authViewModel.errorMessage, 'Please enter a password');
    });

    test('resetPassword returns false for short password', () async {
      authViewModel.setPassword('123');
      final result = await authViewModel.resetPassword();
      expect(result, false);
      expect(authViewModel.errorMessage, 'Password must be at least 6 characters');
    });

    test('sendPasswordResetEmail returns false for empty email', () async {
      authViewModel.setEmail('');
      final result = await authViewModel.sendPasswordResetEmail();
      expect(result, false);
      expect(authViewModel.errorMessage, 'Please enter your email first');
    });

    test('sendPasswordResetEmail returns false for invalid email', () async {
      authViewModel.setEmail('invalid');
      final result = await authViewModel.sendPasswordResetEmail();
      expect(result, false);
      expect(authViewModel.errorMessage, 'Please enter a valid email');
    });
  });
}
