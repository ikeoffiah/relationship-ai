import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/shared/widgets/animated_button.dart';

enum DialogType { success, error, info }

class CustomDialog extends StatelessWidget {
  final DialogType? type;
  final String title;
  final String? message;
  final Widget? content;
  final String buttonText;
  final VoidCallback onButtonPressed;
  final bool isForm;

  const CustomDialog._({
    this.type,
    required this.title,
    this.message,
    this.content,
    required this.buttonText,
    required this.onButtonPressed,
    this.isForm = false,
  });

  // Static method for showing a simple message dialog
  static Future<void> showMessage(
    BuildContext context, {
    required String title,
    required String message,
    DialogType type = DialogType.info,
    String buttonText = 'Okay',
    VoidCallback? onButtonPressed,
  }) {
    return showGeneralDialog(
      context: context,
      barrierDismissible: true,
      barrierLabel: 'Dismiss',
      barrierColor: Colors.black.withValues(alpha: 0.4),
      transitionDuration: const Duration(milliseconds: 400),
      pageBuilder: (context, animation, secondaryAnimation) {
        return CustomDialog._(
          title: title,
          message: message,
          type: type,
          buttonText: buttonText,
          onButtonPressed: onButtonPressed ?? () => Navigator.pop(context),
        );
      },
      transitionBuilder: (context, animation, secondaryAnimation, child) {
        return ScaleTransition(
          scale: CurvedAnimation(parent: animation, curve: Curves.easeOutBack),
          child: child,
        );
      },
    );
  }

  // Static method for showing a form dialog
  static Future<void> showForm(
    BuildContext context, {
    required String title,
    required Widget content,
    String buttonText = 'Submit',
    required VoidCallback onButtonPressed,
  }) {
    return showGeneralDialog(
      context: context,
      barrierDismissible: false, // Forms usually require explicit action
      barrierLabel: 'Dismiss',
      barrierColor: Colors.black.withValues(alpha: 0.4),
      transitionDuration: const Duration(milliseconds: 400),
      pageBuilder: (context, animation, secondaryAnimation) {
        return CustomDialog._(
          title: title,
          content: content,
          buttonText: buttonText,
          onButtonPressed: onButtonPressed,
          isForm: true,
        );
      },
      transitionBuilder: (context, animation, secondaryAnimation, child) {
        return ScaleTransition(
          scale: CurvedAnimation(parent: animation, curve: Curves.easeOutBack),
          child: child,
        );
      },
    );
  }

  // Static method for showing a loading dialog
  static Future<void> showLoading(
    BuildContext context, {
    String message = 'Loading...',
  }) {
    return showGeneralDialog(
      context: context,
      barrierDismissible: false, // Cannot be dismissed
      barrierLabel: '',
      barrierColor: Colors.black.withValues(alpha: 0.5),
      transitionDuration: const Duration(milliseconds: 300),
      pageBuilder: (context, animation, secondaryAnimation) {
        return LoadingDialog(message: message);
      },
      transitionBuilder: (context, animation, secondaryAnimation, child) {
        return FadeTransition(
          opacity: animation,
          child: ScaleTransition(
            scale: Tween<double>(begin: 0.8, end: 1.0).animate(
              CurvedAnimation(parent: animation, curve: Curves.easeOut),
            ),
            child: child,
          ),
        );
      },
    );
  }

  Color get _typeColor {
    if (isForm) return AppColors.warmCoral; // Form default color
    switch (type) {
      case DialogType.success:
        return AppColors.sageGreen;
      case DialogType.error:
        return AppColors.warmCoral;
      case DialogType.info:
      default:
        return AppColors.calmTeal;
    }
  }

  IconData get _typeIcon {
    if (isForm) return Icons.edit_note_rounded;
    switch (type) {
      case DialogType.success:
        return Icons.check_circle_outline_rounded;
      case DialogType.error:
        return Icons.error_outline_rounded;
      case DialogType.info:
      default:
        return Icons.info_outline_rounded;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32),
        child: Material(
          color: Colors.transparent,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(32),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
              child: Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.85),
                  borderRadius: BorderRadius.circular(32),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.6),
                    width: 1.5,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.softCharcoal.withValues(alpha: 0.1),
                      blurRadius: 40,
                      offset: const Offset(0, 20),
                    ),
                  ],
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Icon
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: _typeColor.withValues(alpha: 0.1),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(_typeIcon, color: _typeColor, size: 32),
                    ),
                    const SizedBox(height: 16),

                    // Title
                    DefaultTextStyle(
                      style: AppTheme.textTheme.headlineSmall!.copyWith(
                        color: AppColors.softCharcoal,
                        fontWeight: FontWeight.bold,
                      ),
                      textAlign: TextAlign.center,
                      child: Text(title),
                    ),
                    const SizedBox(height: 8),

                    // Message (if applicable)
                    if (message != null)
                      DefaultTextStyle(
                        style: AppTheme.textTheme.bodyMedium!.copyWith(
                          color: AppColors.softCharcoal.withValues(alpha: 0.8),
                        ),
                        textAlign: TextAlign.center,
                        child: Text(message!),
                      ),

                    // Custom Content (Form)
                    if (content != null) ...[
                      const SizedBox(height: 16),
                      DefaultTextStyle(
                        style: AppTheme.textTheme.bodyMedium!,
                        child: content!,
                      ),
                    ],

                    const SizedBox(height: 24),

                    // Action Button
                    SizedBox(
                      width: double.infinity,
                      child: AnimatedButton(
                        label: buttonText,
                        onTap: onButtonPressed,
                        isFilled: true,
                        useGoldGradient: false,
                        // If it's an error, maybe use red button?
                        // The AnimatedButton uses AppColors.warmCoral by default if !useGoldGradient.
                        // That fits our general "Action" color.
                      ),
                    ),

                    // Close button for forms if needed?
                    // Usually forms have a separate cancel or X.
                    // For now, simple design as requested.
                    if (isForm) ...[
                      const SizedBox(height: 12),
                      TextButton(
                        onPressed: () => Navigator.pop(context),
                        child: Text(
                          'Cancel',
                          style: AppTheme.textTheme.bodyMedium?.copyWith(
                            color: AppColors.softCharcoal.withValues(
                              alpha: 0.6,
                            ),
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// Loading Dialog Widget
class LoadingDialog extends StatelessWidget {
  final String message;

  const LoadingDialog({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32),
        child: Material(
          color: Colors.transparent,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(24),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
              child: Container(
                padding: const EdgeInsets.all(32),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.9),
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.6),
                    width: 1.5,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.softCharcoal.withValues(alpha: 0.15),
                      blurRadius: 40,
                      offset: const Offset(0, 20),
                    ),
                  ],
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Loading Indicator
                    SizedBox(
                      width: 48,
                      height: 48,
                      child: CircularProgressIndicator(
                        strokeWidth: 3,
                        valueColor: AlwaysStoppedAnimation<Color>(
                          AppColors.warmCoral,
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),

                    // Loading Message
                    Text(
                      message,
                      style: AppTheme.textTheme.bodyLarge?.copyWith(
                        color: AppColors.softCharcoal,
                        fontWeight: FontWeight.w600,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
