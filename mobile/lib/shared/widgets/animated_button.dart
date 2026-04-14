import 'package:flutter/material.dart';
import 'package:mobile/core/theme/app_colors.dart';

/// Reusable animated button with micro-interactions
/// Supports filled and outline variants
class AnimatedButton extends StatefulWidget {
  final String label;
  final VoidCallback onTap;
  final bool isFilled;
  final double height;
  final bool useGoldGradient;
  final double borderRadius;
  final Color? outlineColor;

  const AnimatedButton({
    super.key,
    required this.label,
    required this.onTap,
    this.isFilled = true,
    this.height = 56.0,
    this.useGoldGradient = false,
    this.borderRadius = 14.0,
    this.outlineColor,
  });

  @override
  State<AnimatedButton> createState() => _AnimatedButtonState();
}

class _AnimatedButtonState extends State<AnimatedButton>
    with SingleTickerProviderStateMixin {
  late AnimationController _bounceController;
  late Animation<double> _scaleAnimation;
  // ignore: unused_field
  bool _isHovered = false;

  @override
  void initState() {
    super.initState();
    _bounceController = AnimationController(
      duration: const Duration(milliseconds: 150),
      vsync: this,
    );

    _scaleAnimation = Tween<double>(begin: 1.0, end: 0.95).animate(
      CurvedAnimation(parent: _bounceController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _bounceController.dispose();
    super.dispose();
  }

  void _handleTapDown(TapDownDetails details) {
    _bounceController.forward();
  }

  void _handleTapUp(TapUpDetails details) {
    _bounceController.reverse();
    widget.onTap();
  }

  void _handleTapCancel() {
    _bounceController.reverse();
  }

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: GestureDetector(
        onTapDown: _handleTapDown,
        onTapUp: _handleTapUp,
        onTapCancel: _handleTapCancel,
        child: ScaleTransition(
          scale: _scaleAnimation,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            height: widget.height,
            decoration: BoxDecoration(
              gradient: widget.isFilled && widget.useGoldGradient
                  ? AppColors.goldGradient
                  : null,
              color: widget.isFilled && !widget.useGoldGradient
                  ? AppColors.warmCoral
                  : Colors.transparent,
              border: widget.isFilled
                  ? null
                  : Border.all(
                      color: widget.outlineColor ?? AppColors.softCharcoal,
                      width: 2.0,
                    ),
              borderRadius: BorderRadius.circular(widget.borderRadius),
              boxShadow: widget.isFilled
                  ? [
                      BoxShadow(
                        color:
                            (widget.useGoldGradient
                                    ? AppColors.goldMedium
                                    : AppColors.warmCoral)
                                .withValues(alpha: 0.3),
                        blurRadius: 12,
                        offset: const Offset(0, 4),
                      ),
                    ]
                  : null,
            ),
            child: Center(
              child: AnimatedDefaultTextStyle(
                duration: const Duration(milliseconds: 200),
                style: TextStyle(
                  color: widget.isFilled
                      ? Colors.white
                      : (widget.outlineColor ?? AppColors.softCharcoal),
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.5,
                ),
                child: Text(widget.label),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
