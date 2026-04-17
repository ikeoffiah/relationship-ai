import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:ui' as ui;
import 'dart:math' as math;
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/shared/widgets/animated_button.dart';
import 'package:mobile/shared/widgets/social_sign_in_button.dart';
import 'package:mobile/features/auth/views/email_verification_screen.dart';

/// Signup Screen with email/password and Google Sign-In
/// Beautiful, emotionally-designed account creation experience
class SignupScreen extends StatefulWidget {
  const SignupScreen({super.key});

  @override
  State<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends State<SignupScreen>
    with TickerProviderStateMixin {
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _confirmPasswordController =
      TextEditingController();

  final FocusNode _nameFocusNode = FocusNode();
  final FocusNode _emailFocusNode = FocusNode();
  final FocusNode _passwordFocusNode = FocusNode();
  final FocusNode _confirmPasswordFocusNode = FocusNode();

  late AnimationController _logoFloatController;
  late AnimationController _fadeController;

  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;
  bool _agreedToTerms = false;

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

    _nameController.addListener(_onNameChanged);
    _emailController.addListener(_onEmailChanged);
    _passwordController.addListener(_onPasswordChanged);
    _confirmPasswordController.addListener(_onConfirmPasswordChanged);
  }

  void _onNameChanged() {
    context.read<AuthViewModel>().setFullName(_nameController.text);
  }

  void _onEmailChanged() {
    context.read<AuthViewModel>().setEmail(_emailController.text);
  }

  void _onPasswordChanged() {
    context.read<AuthViewModel>().setPassword(_passwordController.text);
  }

  void _onConfirmPasswordChanged() {
    context.read<AuthViewModel>().setConfirmPassword(
      _confirmPasswordController.text,
    );
  }

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    _nameFocusNode.dispose();
    _emailFocusNode.dispose();
    _passwordFocusNode.dispose();
    _confirmPasswordFocusNode.dispose();
    _logoFloatController.dispose();
    _fadeController.dispose();
    super.dispose();
  }

  Future<void> _handleSignup() async {
    if (!_agreedToTerms) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('Please agree to the Terms of Service'),
          backgroundColor: AppColors.warmCoral,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      );
      return;
    }

    FocusScope.of(context).unfocus();
    final viewModel = context.read<AuthViewModel>();
    final success = await viewModel.signupWithEmail();

    if (success && mounted) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => EmailVerificationScreen(
            email: viewModel.email,
          ),
        ),
      );
    }
  }

  Future<void> _handleGoogleSignIn() async {
    final viewModel = context.read<AuthViewModel>();
    final success = await viewModel.signInWithGoogle();

    if (success && mounted) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => EmailVerificationScreen(
            email: viewModel.email,
          ),
        ),
      );
    }
  }

  void _navigateToLogin() {
    context.read<AuthViewModel>().resetForm();
    Navigator.pop(context);
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
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: Column(
                  children: [
                    const SizedBox(height: 32),
                    _buildBackButton(),
                    const SizedBox(height: 16),
                    _buildLogo(),
                    const SizedBox(height: 24),
                    _buildHeader(),
                    const SizedBox(height: 20),
                    _buildGoogleSignupSection(),
                    const SizedBox(height: 20),
                    _buildForm(),
                    const SizedBox(height: 24),
                    _buildFooter(),
                    const SizedBox(height: 32),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildBackButton() {
    return Align(
      alignment: Alignment.centerLeft,
      child: GestureDetector(
        onTap: _navigateToLogin,
        child: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.4),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.white.withValues(alpha: 0.5)),
          ),
          child: Icon(
            Icons.arrow_back_ios_new_rounded,
            color: AppColors.softCharcoal,
            size: 20,
          ),
        ),
      ),
    );
  }

  Widget _buildLogo() {
    return AnimatedBuilder(
      animation: _logoFloatController,
      builder: (context, child) {
        final floatY = math.sin(_logoFloatController.value * 2 * math.pi) * 3;
        return Transform.translate(offset: Offset(0, floatY), child: child);
      },
      child: ClipRRect(
        borderRadius: BorderRadius.circular(999),
        child: BackdropFilter(
          filter: ui.ImageFilter.blur(sigmaX: 10, sigmaY: 10),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
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
              height: 28,
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
          'Create Your Account 💕',
          style: AppTheme.textTheme.displaySmall?.copyWith(
            color: AppColors.softCharcoal,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Start your relationship\njourney together',
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

            // Name field
            _buildTextField(
              controller: _nameController,
              focusNode: _nameFocusNode,
              label: 'Full Name',
              hint: 'Enter your full name',
              icon: Icons.person_outline_rounded,
              textCapitalization: TextCapitalization.words,
              textInputAction: TextInputAction.next,
              onSubmitted: (_) => _emailFocusNode.requestFocus(),
            ),
            const SizedBox(height: 14),

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
            const SizedBox(height: 14),

            // Password field
            _buildTextField(
              controller: _passwordController,
              focusNode: _passwordFocusNode,
              label: 'Password',
              hint: 'Create a password',
              icon: Icons.lock_outline_rounded,
              obscureText: _obscurePassword,
              textInputAction: TextInputAction.next,
              onSubmitted: (_) => _confirmPasswordFocusNode.requestFocus(),
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
            const SizedBox(height: 14),

            // Confirm Password field
            _buildTextField(
              controller: _confirmPasswordController,
              focusNode: _confirmPasswordFocusNode,
              label: 'Confirm Password',
              hint: 'Confirm your password',
              icon: Icons.lock_outline_rounded,
              obscureText: _obscureConfirmPassword,
              textInputAction: TextInputAction.done,
              onSubmitted: (_) => _handleSignup(),
              suffixIcon: IconButton(
                icon: Icon(
                  _obscureConfirmPassword
                      ? Icons.visibility_off_outlined
                      : Icons.visibility_outlined,
                  color: AppColors.softCharcoal.withValues(alpha: 0.5),
                  size: 22,
                ),
                onPressed: () {
                  setState(
                    () => _obscureConfirmPassword = !_obscureConfirmPassword,
                  );
                },
              ),
            ),
            const SizedBox(height: 16),

            // Terms checkbox
            _buildTermsCheckbox(),
            const SizedBox(height: 20),

            // Create Account Button
            AnimatedButton(
              label: viewModel.isLoading
                  ? 'Creating account...'
                  : 'Create Account',
              onTap: viewModel.isLoading ? () {} : _handleSignup,
              isFilled: true,
              height: 56,
              borderRadius: 14,
            ),
          ],
        );
      },
    );
  }

  Widget _buildGoogleSignupSection() {
    return Consumer<AuthViewModel>(
      builder: (context, viewModel, _) {
        return Column(
          children: [
            SocialSignInButton(
              label: 'Sign up with Google',
              isGoogle: true,
              isLoading: viewModel.isLoading,
              onTap: viewModel.isLoading ? () {} : _handleGoogleSignIn,
            ),
            const SizedBox(height: 16),
            _buildOrDivider(),
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
    TextCapitalization textCapitalization = TextCapitalization.none,
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
            textCapitalization: textCapitalization,
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

  Widget _buildTermsCheckbox() {
    return GestureDetector(
      onTap: () {
        setState(() => _agreedToTerms = !_agreedToTerms);
      },
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            width: 22,
            height: 22,
            decoration: BoxDecoration(
              color: _agreedToTerms
                  ? AppColors.warmCoral
                  : Colors.white.withValues(alpha: 0.7),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(
                color: _agreedToTerms
                    ? AppColors.warmCoral
                    : AppColors.softCharcoal.withValues(alpha: 0.2),
                width: 1.5,
              ),
            ),
            child: _agreedToTerms
                ? const Icon(Icons.check_rounded, size: 16, color: Colors.white)
                : null,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text.rich(
              TextSpan(
                text: 'I agree to the ',
                style: TextStyle(
                  color: AppColors.softCharcoal.withValues(alpha: 0.7),
                  fontSize: 14,
                  height: 1.4,
                ),
                children: [
                  TextSpan(
                    text: 'Terms of Service',
                    style: TextStyle(
                      color: AppColors.warmCoral,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const TextSpan(text: ' and '),
                  TextSpan(
                    text: 'Privacy Policy',
                    style: TextStyle(
                      color: AppColors.warmCoral,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
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
          'Already have an account? ',
          style: TextStyle(
            color: AppColors.softCharcoal.withValues(alpha: 0.7),
            fontSize: 15,
          ),
        ),
        GestureDetector(
          onTap: _navigateToLogin,
          child: Text(
            'Log In',
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
