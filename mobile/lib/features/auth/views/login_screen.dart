import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:ui' as ui;
import 'dart:math' as math;
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/shared/widgets/animated_button.dart';
import 'package:mobile/shared/widgets/social_sign_in_button.dart';
import 'package:mobile/features/auth/views/signup_screen.dart';
import 'package:mobile/features/auth/views/route_guard_test_screen.dart';
import 'package:mobile/features/auth/views/forgot_password_screen.dart';

/// Login Screen with email/password and Google Sign-In
/// Beautiful, emotionally-designed authentication experience
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen>
    with TickerProviderStateMixin {
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final FocusNode _emailFocusNode = FocusNode();
  final FocusNode _passwordFocusNode = FocusNode();

  late AnimationController _logoFloatController;
  late AnimationController _fadeController;
  bool _obscurePassword = true;

  @override
  void initState() {
    super.initState();

    _logoFloatController = AnimationController(
      duration: const Duration(seconds: 4),
      vsync: this,
    )..repeat();

    _fadeController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    )..forward();

    _emailController.addListener(_onEmailChanged);
    _passwordController.addListener(_onPasswordChanged);
  }

  void _onEmailChanged() {
    context.read<AuthViewModel>().setEmail(_emailController.text);
  }

  void _onPasswordChanged() {
    context.read<AuthViewModel>().setPassword(_passwordController.text);
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _emailFocusNode.dispose();
    _passwordFocusNode.dispose();
    _logoFloatController.dispose();
    _fadeController.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    FocusScope.of(context).unfocus();
    final viewModel = context.read<AuthViewModel>();
    final success = await viewModel.loginWithEmail();

    if (success && mounted) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const RouteGuardTestScreen()),
      );
    }
  }

  Future<void> _handleGoogleSignIn() async {
    final viewModel = context.read<AuthViewModel>();
    final success = await viewModel.signInWithGoogle();

    if (success && mounted) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const RouteGuardTestScreen()),
      );
    }
  }

  Future<void> _handleBiometricSignIn() async {
    FocusScope.of(context).unfocus();
    final viewModel = context.read<AuthViewModel>();
    final success = await viewModel.loginWithBiometrics();

    if (success && mounted) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const RouteGuardTestScreen()),
      );
    }
  }

  void _navigateToSignup() {
    context.read<AuthViewModel>().resetForm();
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const SignupScreen()),
    );
  }

  void _handleForgotPassword() {
    context.read<AuthViewModel>().resetForm();
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const ForgotPasswordScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;

    return Scaffold(
      body: Container(
        width: size.width,
        height: size.height,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              AppColors.softRose,
              AppColors.rosePeach,
              AppColors.creamWhite,
            ],
            stops: [0.0, 0.3, 0.7],
          ),
        ),
        child: SafeArea(
          child: FadeTransition(
            opacity: CurvedAnimation(
              parent: _fadeController,
              curve: Curves.easeOut,
            ),
            child: SingleChildScrollView(
              physics: const ClampingScrollPhysics(),
              child: ConstrainedBox(
                constraints: BoxConstraints(
                  minHeight: size.height - MediaQuery.of(context).padding.top,
                ),
                child: IntrinsicHeight(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 24),
                    child: Column(
                      children: [
                        const SizedBox(height: 40),
                        _buildLogo(),
                        const SizedBox(height: 32),
                        _buildHeader(),
                        const SizedBox(height: 32),
                        _buildForm(),
                        const Spacer(),
                        _buildFooter(),
                        const SizedBox(height: 24),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildLogo() {
    return AnimatedBuilder(
      animation: _logoFloatController,
      builder: (context, child) {
        final floatY = math.sin(_logoFloatController.value * 2 * math.pi) * 4;
        return Transform.translate(offset: Offset(0, floatY), child: child);
      },
      child: ClipRRect(
        borderRadius: BorderRadius.circular(999),
        child: BackdropFilter(
          filter: ui.ImageFilter.blur(sigmaX: 10, sigmaY: 10),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.25),
              borderRadius: BorderRadius.circular(999),
              border: Border.all(
                color: Colors.white.withValues(alpha: 0.4),
                width: 1.5,
              ),
              boxShadow: [
                BoxShadow(
                  color: AppColors.warmCoral.withValues(alpha: 0.15),
                  blurRadius: 20,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            child: Image.asset(
              'assets/images/bliss_logo.png',
              height: 32,
              color: AppColors.warmCoral,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Column(
      children: [
        Text(
          'Welcome Back! 💕',
          style: AppTheme.textTheme.displaySmall?.copyWith(
            color: AppColors.softCharcoal,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Sign in to continue your\njourney together',
          textAlign: TextAlign.center,
          style: AppTheme.textTheme.bodyLarge?.copyWith(
            color: AppColors.softCharcoal.withValues(alpha: 0.7),
            height: 1.5,
          ),
        ),
      ],
    );
  }

  Widget _buildForm() {
    return Consumer<AuthViewModel>(
      builder: (context, viewModel, _) {
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Error message
            if (viewModel.errorMessage != null) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.error.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: AppColors.error.withValues(alpha: 0.3),
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.error_outline_rounded,
                      color: AppColors.error,
                      size: 20,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        viewModel.errorMessage!,
                        style: TextStyle(
                          color: AppColors.error,
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],

            // Email field
            _buildTextField(
              controller: _emailController,
              focusNode: _emailFocusNode,
              label: 'Email',
              hint: 'Enter your email',
              icon: Icons.email_outlined,
              keyboardType: TextInputType.emailAddress,
              textInputAction: TextInputAction.next,
              onSubmitted: (_) => _passwordFocusNode.requestFocus(),
            ),
            const SizedBox(height: 16),

            // Password field
            _buildTextField(
              controller: _passwordController,
              focusNode: _passwordFocusNode,
              label: 'Password',
              hint: 'Enter your password',
              icon: Icons.lock_outline_rounded,
              obscureText: _obscurePassword,
              textInputAction: TextInputAction.done,
              onSubmitted: (_) => _handleLogin(),
              suffixIcon: IconButton(
                icon: Icon(
                  _obscurePassword
                      ? Icons.visibility_off_outlined
                      : Icons.visibility_outlined,
                  color: AppColors.softCharcoal.withValues(alpha: 0.5),
                  size: 22,
                ),
                onPressed: () {
                  setState(() => _obscurePassword = !_obscurePassword);
                },
              ),
            ),

            // Forgot Password
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: _handleForgotPassword,
                style: TextButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                ),
                child: Text(
                  'Forgot Password?',
                  style: TextStyle(
                    color: AppColors.warmCoral,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 8),

            // Sign In Button
            AnimatedButton(
              label: viewModel.isLoading ? 'Signing in...' : 'Sign In',
              onTap: viewModel.isLoading ? () {} : _handleLogin,
              isFilled: true,
              height: 56,
              borderRadius: 14,
            ),
            const SizedBox(height: 24),

            // OR Divider
            _buildOrDivider(),
            const SizedBox(height: 24),

            // Google Sign In
            SocialSignInButton(
              label: 'Sign in with Google',
              isGoogle: true,
              isLoading: viewModel.isLoading,
              onTap: viewModel.isLoading ? () {} : _handleGoogleSignIn,
            ),
            const SizedBox(height: 16),
            AnimatedButton(
              label: viewModel.isLoading ? 'Processing...' : 'Face ID / Fingerprint',
              onTap: viewModel.isLoading ? () {} : _handleBiometricSignIn,
              isFilled: false,
              height: 56,
              borderRadius: 14,
            ),
          ],
        );
      },
    );
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required FocusNode focusNode,
    required String label,
    required String hint,
    required IconData icon,
    bool obscureText = false,
    TextInputType keyboardType = TextInputType.text,
    TextInputAction textInputAction = TextInputAction.next,
    void Function(String)? onSubmitted,
    Widget? suffixIcon,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label.toUpperCase(),
          style: AppTheme.textTheme.bodySmall?.copyWith(
            fontWeight: FontWeight.w600,
            letterSpacing: 1.2,
            color: AppColors.softCharcoal.withValues(alpha: 0.6),
          ),
        ),
        const SizedBox(height: 8),
        Container(
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.7),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.white, width: 1.5),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.04),
                blurRadius: 10,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: TextField(
            controller: controller,
            focusNode: focusNode,
            obscureText: obscureText,
            keyboardType: keyboardType,
            textInputAction: textInputAction,
            onSubmitted: onSubmitted,
            style: AppTheme.textTheme.bodyLarge,
            cursorColor: AppColors.warmCoral,
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: AppTheme.textTheme.bodyLarge?.copyWith(
                color: AppColors.softCharcoal.withValues(alpha: 0.35),
              ),
              prefixIcon: Icon(
                icon,
                color: AppColors.softCharcoal.withValues(alpha: 0.5),
                size: 22,
              ),
              suffixIcon: suffixIcon,
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 16,
              ),
              border: InputBorder.none,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildOrDivider() {
    return Row(
      children: [
        Expanded(
          child: Container(
            height: 1,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  Colors.transparent,
                  AppColors.softCharcoal.withValues(alpha: 0.2),
                ],
              ),
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Text(
            'OR',
            style: TextStyle(
              color: AppColors.softCharcoal.withValues(alpha: 0.5),
              fontSize: 13,
              fontWeight: FontWeight.w600,
              letterSpacing: 1,
            ),
          ),
        ),
        Expanded(
          child: Container(
            height: 1,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppColors.softCharcoal.withValues(alpha: 0.2),
                  Colors.transparent,
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildFooter() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text(
          "Don't have an account? ",
          style: TextStyle(
            color: AppColors.softCharcoal.withValues(alpha: 0.7),
            fontSize: 15,
          ),
        ),
        GestureDetector(
          onTap: _navigateToSignup,
          child: Text(
            'Sign Up',
            style: TextStyle(
              color: AppColors.warmCoral,
              fontSize: 15,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ],
    );
  }
}
