import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/shared/widgets/animated_button.dart';
import 'package:mobile/features/auth/views/new_password_screen.dart';

class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final TextEditingController _emailController = TextEditingController();
  final FocusNode _emailFocusNode = FocusNode();

  @override
  void initState() {
    super.initState();
    _emailController.addListener(_onEmailChanged);
    // Pre-fill email if available in ViewModel
    final viewModel = context.read<AuthViewModel>();
    if (viewModel.email.isNotEmpty) {
      _emailController.text = viewModel.email;
    }
  }

  void _onEmailChanged() {
    context.read<AuthViewModel>().setEmail(_emailController.text);
  }

  @override
  void dispose() {
    _emailController.dispose();
    _emailFocusNode.dispose();
    super.dispose();
  }

  Future<void> _handleResetRequest() async {
    final viewModel = context.read<AuthViewModel>();
    final success = await viewModel.sendPasswordResetEmail();

    if (success && mounted) {
      // Navigate to New Password Screen
      Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => const NewPasswordScreen()),
      );
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
                  'Forgot Password?',
                  style: AppTheme.textTheme.displaySmall?.copyWith(
                    color: AppColors.softCharcoal,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  "Don't worry! It happens. Please enter the email associated with your account.",
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
                          controller: _emailController,
                          focusNode: _emailFocusNode,
                          label: 'Email Address',
                          hint: 'Enter your email',
                          icon: Icons.email_outlined,
                          keyboardType: TextInputType.emailAddress,
                          onSubmitted: (_) => _handleResetRequest(),
                        ),
                        const SizedBox(height: 32),

                        AnimatedButton(
                          label: viewModel.isLoading
                              ? 'Sending...'
                              : 'Send Code',
                          onTap: viewModel.isLoading
                              ? () {}
                              : _handleResetRequest,
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
    TextInputType keyboardType = TextInputType.text,
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
            keyboardType: keyboardType,
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
