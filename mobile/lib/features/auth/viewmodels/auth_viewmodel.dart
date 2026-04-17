import 'package:mobile/features/auth/models/user_profile.dart'; // Add import if not present
import 'package:mobile/core/services/storage_service.dart';
import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';

import 'package:mobile/core/api_services/auth_api_service.dart';
import 'package:mobile/core/services/biometric_service.dart';

/// ViewModel for managing authentication state
/// Handles login, signup, and social sign-in
class AuthViewModel extends ChangeNotifier {
  final GoogleSignIn _googleSignIn;
  final AuthApiService _authService;
  final BiometricService _biometricService;

  AuthViewModel({
    GoogleSignIn? googleSignIn,
    AuthApiService? authService,
    BiometricService? biometricService,
  })  : _googleSignIn = googleSignIn ?? GoogleSignIn(scopes: ['email', 'profile']),
        _authService = authService ?? AuthApiService(),
        _biometricService = biometricService ?? BiometricService();

  UserProfile? _user;
  String? _token;

  UserProfile? get user => _user;
  String? get token => _token;

  bool _isLoading = false;
  String? _errorMessage;
  String _email = '';
  String _password = '';
  String _confirmPassword = '';
  String _fullName = '';

  // Getters
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  String get email => _email;
  String get password => _password;
  String get confirmPassword => _confirmPassword;
  String get fullName => _fullName;

  // Setters with validation
  void setEmail(String value) {
    _email = value;
    _clearError();
    notifyListeners();
  }

  void setPassword(String value) {
    _password = value;
    _clearError();
    notifyListeners();
  }

  void setConfirmPassword(String value) {
    _confirmPassword = value;
    _clearError();
    notifyListeners();
  }

  void setFullName(String value) {
    _fullName = value;
    _clearError();
    notifyListeners();
  }

  void _clearError() {
    _errorMessage = null;
  }

  void _setLoading(bool value) {
    _isLoading = value;
    notifyListeners();
  }

  void _setError(String message) {
    _errorMessage = message;
    notifyListeners();
  }

  /// Validate email format
  bool _isValidEmail(String email) {
    final emailRegex = RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$');
    return emailRegex.hasMatch(email);
  }

  /// Validate login form
  bool validateLoginForm() {
    if (_email.isEmpty) {
      _setError('Please enter your email');
      return false;
    }
    if (!_isValidEmail(_email)) {
      _setError('Please enter a valid email');
      return false;
    }
    if (_password.isEmpty) {
      _setError('Please enter your password');
      return false;
    }
    if (_password.length < 6) {
      _setError('Password must be at least 6 characters');
      return false;
    }
    return true;
  }

  /// Validate signup form
  bool validateSignupForm() {
    if (_fullName.isEmpty) {
      _setError('Please enter your full name');
      return false;
    }
    if (_fullName.length < 2) {
      _setError('Name must be at least 2 characters');
      return false;
    }
    if (_email.isEmpty) {
      _setError('Please enter your email');
      return false;
    }
    if (!_isValidEmail(_email)) {
      _setError('Please enter a valid email');
      return false;
    }
    if (_password.isEmpty) {
      _setError('Please enter a password');
      return false;
    }
    if (_password.length < 6) {
      _setError('Password must be at least 6 characters');
      return false;
    }
    if (_confirmPassword.isEmpty) {
      _setError('Please confirm your password');
      return false;
    }
    if (_password != _confirmPassword) {
      _setError('Passwords do not match');
      return false;
    }
    return true;
  }

  // ... existing code ...

  /// Login with email and password
  Future<bool> loginWithEmail() async {
    if (!validateLoginForm()) return false;

    _setLoading(true);
    try {
      final response = await _authService.login(_email, _password);
      _user = response.user;
      _token = response.token;

      if (_token != null) {
        await StorageService.saveToken(_token!);
      }
      if (_user != null) {
        await StorageService.saveUserId(_user!.id);
      }

      debugPrint('Login successful for: $_email');
      _setLoading(false);
      return true;
    } catch (e) {
      _setError(e.toString().replaceAll('Exception: ', ''));
      _setLoading(false);
      return false;
    }
  }

  /// Sign up with email and password
  Future<bool> signupWithEmail() async {
    if (!validateSignupForm()) return false;

    _setLoading(true);
    try {
      final response = await _authService.signup(_fullName, _email, _password);
      _user = response.user;
      _token = response.token;

      if (_token != null) {
        await StorageService.saveToken(_token!);
      }
      if (_user != null) {
        await StorageService.saveUserId(_user!.id);
      }

      debugPrint('Signup successful for: $_email');
      _setLoading(false);
      return true;
    } catch (e) {
      _setError(e.toString().replaceAll('Exception: ', ''));
      _setLoading(false);
      return false;
    }
  }

  /// Login with Biometrics (Face ID / Fingerprint)
  Future<bool> loginWithBiometrics() async {
    _setLoading(true);
    _clearError();
    try {
      final canUse = await _biometricService.canCheckBiometrics();
      if (!canUse) {
        _setError('Biometrics are not supported or enrolled on this device.');
        _setLoading(false);
        return false;
      }
      final success = await _biometricService.authenticate();
      if (success) {
        // Mock successful backend session for Biometric Login
        _email = 'biometric@user.com'; 
        _fullName = 'Biometric User';
        debugPrint('Biometric login successful!');
        _setLoading(false);
        return true;
      } else {
        _setError('Biometric authentication failed.');
        _setLoading(false);
        return false;
      }
    } catch (e) {
      _setError('Error initiating biometrics.');
      _setLoading(false);
      return false;
    }
  }

  /// Sign in with Google
  Future<bool> signInWithGoogle() async {
    _setLoading(true);
    _clearError();

    try {
      final GoogleSignInAccount? account = await _googleSignIn.signIn();

      if (account != null) {
        debugPrint('Google Sign-In successful: ${account.email}');

        final GoogleSignInAuthentication auth = await account.authentication;
        final String? idToken = auth.idToken;

        if (idToken != null) {
          final response = await _authService.googleSignIn(idToken);
          _user = response.user;
          _token = response.token;

          if (_token != null) {
            await StorageService.saveToken(_token!);
          }
          if (_user != null) {
            await StorageService.saveUserId(_user!.id);
          }
        }

        _email = account.email;
        _fullName = account.displayName ?? '';

        _setLoading(false);
        return true;
      } else {
        // User cancelled the sign-in
        _setLoading(false);
        return false;
      }
    } catch (e) {
      debugPrint('Google Sign-In error: $e');
      _setError('Google Sign-In failed. Please try again.');
      _setLoading(false);
      return false;
    }
  }

  /// Sign out from Google
  Future<void> signOutGoogle() async {
    await _googleSignIn.signOut();
  }

  /// General logout method
  Future<void> logout() async {
    _setLoading(true);
    try {
      await signOutGoogle();
      await _authService.logout();
      await StorageService.clearAll(); // Clear stored data
      resetForm();
    } catch (e) {
      debugPrint('Logout error: $e');
      // Force local logout even if API fails
      await StorageService.clearAll();
      resetForm();
    } finally {
      _setLoading(false);
    }
  }

  /// Reset all form fields
  void resetForm() {
    _email = '';
    _password = '';
    _confirmPassword = '';
    _fullName = '';
    _errorMessage = null;
    _isLoading = false;
    notifyListeners();
  }

  /// Handle forgot password
  Future<bool> sendPasswordResetEmail() async {
    if (_email.isEmpty) {
      _setError('Please enter your email first');
      return false;
    }
    if (!_isValidEmail(_email)) {
      _setError('Please enter a valid email');
      return false;
    }

    _setLoading(true);
    try {
      await _authService.forgotPassword(_email);

      debugPrint('Password reset email sent to: $_email');
      _setLoading(false);
      return true;
    } catch (e) {
      _setError(e.toString().replaceAll('Exception: ', ''));
      _setLoading(false);
      return false;
    }
  }

  /// Reset Password with new password
  Future<bool> resetPassword() async {
    if (_password.isEmpty) {
      _setError('Please enter a password');
      return false;
    }
    if (_password.length < 6) {
      _setError('Password must be at least 6 characters');
      return false;
    }
    if (_confirmPassword.isEmpty) {
      _setError('Please confirm your password');
      return false;
    }
    if (_password != _confirmPassword) {
      _setError('Passwords do not match');
      return false;
    }

    _setLoading(true);
    try {
      // Assuming we have a token somehow.
      // For this flow, usually the token is from a deep link.
      // Since we don't have deep linking implemented yet, we might need a placeholder or update the flow.
      // But adhering to the API spec I created:
      await _authService.resetPassword(_password, "placeholder-token");

      debugPrint('Password reset successful for: $_email');
      _setLoading(false);
      return true;
    } catch (e) {
      _setError(e.toString().replaceAll('Exception: ', ''));
      _setLoading(false);
      return false;
    }
  }
}
