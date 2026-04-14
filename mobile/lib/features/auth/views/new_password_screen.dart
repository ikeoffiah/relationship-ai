import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/shared/widgets/animated_button.dart';
import 'package:mobile/features/auth/views/login_screen.dart';

class NewPasswordScreen extends StatefulWidget {
  const NewPasswordScreen({super.key});

  @override
  State<NewPasswordScreen> createState() => _NewPasswordScreenState();
}

class _NewPasswordScreenState extends State<NewPasswordScreen> {
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _confirmPasswordController =
      TextEditingController();
  final FocusNode _passwordFocusNode = FocusNode();
  final FocusNode _confirmPasswordFocusNode = FocusNode();
  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;

  @override
  void initState() {
    super.initState();
    _passwordController.addListener(_onPasswordChanged);
    _confirmPasswordController.addListener(_onConfirmPasswordChanged);
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
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    _passwordFocusNode.dispose();
    _confirmPasswordFocusNode.dispose();
    super.dispose();
  }

  Future<void> _handleResetPassword() async {
    final viewModel = context.read<AuthViewModel>();
    final success = await viewModel.resetPassword();

    if (success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('Password reset successfully! Please login.'),
          backgroundColor: AppColors.calmTeal,
          behavior: SnackBarBehavior.floating,
        ),
      );

      // Navigate back to Login Screen and remove all previous routes
      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(builder: (_) => const LoginScreen()),
        (route) => false,
      );

      viewModel.resetForm();
    }
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;

    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(
            Icons.arrow_back_ios_new,
            color: AppColors.softCharcoal,
          ),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      extendBodyBehindAppBar: true,
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
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 20),
                Text(
                  'Reset Password',
                  style: AppTheme.textTheme.displaySmall?.copyWith(
                    color: AppColors.softCharcoal,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  "Please enter your new password below.",
                  style: AppTheme.textTheme.bodyLarge?.copyWith(
                    color: AppColors.softCharcoal.withValues(alpha: 0.7),
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 48),

                Consumer<AuthViewModel>(
                  builder: (context, viewModel, _) {
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // Error message
                        if (viewModel.errorMessage != null) ...[
                          Container(
                            padding: const EdgeInsets.all(12),
                            margin: const EdgeInsets.only(bottom: 16),
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
                        ],

                        _buildTextField(
                          controller: _passwordController,
                          focusNode: _passwordFocusNode,
                          label: 'New Password',
                          hint: 'Enter your new password',
                          icon: Icons.lock_outline_rounded,
                          obscureText: _obscurePassword,
                          toggleObscure: () => setState(
                            () => _obscurePassword = !_obscurePassword,
                          ),
                          onSubmitted: (_) =>
                              _confirmPasswordFocusNode.requestFocus(),
                        ),
                        const SizedBox(height: 16),
                        _buildTextField(
                          controller: _confirmPasswordController,
                          focusNode: _confirmPasswordFocusNode,
                          label: 'Confirm Password',
                          hint: 'Confirm your new password',
                          icon: Icons.lock_outline_rounded,
                          obscureText: _obscureConfirmPassword,
                          toggleObscure: () => setState(
                            () => _obscureConfirmPassword =
                                !_obscureConfirmPassword,
                          ),
                          onSubmitted: (_) => _handleResetPassword(),
                        ),
                        const SizedBox(height: 32),

                        AnimatedButton(
                          label: viewModel.isLoading
                              ? 'Resetting...'
                              : 'Reset Password',
                          onTap: viewModel.isLoading
                              ? () {}
                              : _handleResetPassword,
                          isFilled: true,
                          height: 56,
                          borderRadius: 14,
                        ),
                      ],
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required FocusNode focusNode,
    required String label,
    required String hint,
    required IconData icon,
    bool obscureText = false,
    VoidCallback? toggleObscure,
    void Function(String)? onSubmitted,
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
              suffixIcon: toggleObscure != null
                  ? IconButton(
                      icon: Icon(
                        obscureText
                            ? Icons.visibility_off_outlined
                            : Icons.visibility_outlined,
                        color: AppColors.softCharcoal.withValues(alpha: 0.5),
                        size: 22,
                      ),
                      onPressed: toggleObscure,
                    )
                  : null,
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
}
