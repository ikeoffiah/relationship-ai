import 'package:flutter/material.dart';
import 'package:mobile/core/theme/app_colors.dart';

/// Reusable social sign-in button with animated interactions
/// Supports Google and other social providers
class SocialSignInButton extends StatefulWidget {
  final String label;
  final String iconAsset;
  final VoidCallback onTap;
  final bool isGoogle;
  final bool isLoading;

  const SocialSignInButton({
    super.key,
    required this.label,
    required this.onTap,
    this.iconAsset = '',
    this.isGoogle = true,
    this.isLoading = false,
  });

  @override
  State<SocialSignInButton> createState() => _SocialSignInButtonState();
}

class _SocialSignInButtonState extends State<SocialSignInButton>
    with SingleTickerProviderStateMixin {
  late AnimationController _bounceController;
  late Animation<double> _scaleAnimation;
  bool _isPressed = false;

  @override
  void initState() {
    super.initState();
    _bounceController = AnimationController(
      duration: const Duration(milliseconds: 120),
      vsync: this,
    );

    _scaleAnimation = Tween<double>(begin: 1.0, end: 0.96).animate(
      CurvedAnimation(parent: _bounceController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _bounceController.dispose();
    super.dispose();
  }

  void _handleTapDown(TapDownDetails details) {
    if (widget.isLoading) return;
    setState(() => _isPressed = true);
    _bounceController.forward();
  }

  void _handleTapUp(TapUpDetails details) {
    if (widget.isLoading) return;
    setState(() => _isPressed = false);
    _bounceController.reverse();
    widget.onTap();
  }

  void _handleTapCancel() {
    setState(() => _isPressed = false);
    _bounceController.reverse();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: _handleTapDown,
      onTapUp: _handleTapUp,
      onTapCancel: _handleTapCancel,
      child: ScaleTransition(
        scale: _scaleAnimation,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          height: 56,
          decoration: BoxDecoration(
            color: _isPressed ? Colors.grey.shade100 : Colors.white,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: AppColors.softCharcoal.withValues(alpha: 0.15),
              width: 1.5,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: _isPressed ? 0.03 : 0.06),
                blurRadius: _isPressed ? 4 : 12,
                offset: Offset(0, _isPressed ? 1 : 4),
              ),
            ],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (widget.isLoading)
                SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor: AlwaysStoppedAnimation<Color>(
                      AppColors.softCharcoal.withValues(alpha: 0.6),
                    ),
                  ),
                )
              else if (widget.isGoogle)
                _buildGoogleIcon()
              else if (widget.iconAsset.isNotEmpty)
                Image.asset(widget.iconAsset, width: 24, height: 24),
              const SizedBox(width: 12),
              Text(
                widget.isLoading ? 'Please wait...' : widget.label,
                style: TextStyle(
                  color: AppColors.softCharcoal,
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.3,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Build Google 'G' logo
  Widget _buildGoogleIcon() {
    return Image.asset('assets/images/google_logo.png', width: 24, height: 24);
  }
}
