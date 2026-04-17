import 'package:flutter/material.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_theme.dart';

class CustomTextField extends StatefulWidget {
  final TextEditingController controller;
  final String label;
  final void Function(String)? onChanged;
  final TextCapitalization textCapitalization;
  final bool isOptional;
  final int maxLines;
  final int? maxLength;

  const CustomTextField({
    super.key,
    required this.controller,
    required this.label,
    this.onChanged,
    this.textCapitalization = TextCapitalization.sentences,
    this.isOptional = false,
    this.maxLines = 1,
    this.maxLength,
  });

  @override
  State<CustomTextField> createState() => _CustomTextFieldState();
}

class _CustomTextFieldState extends State<CustomTextField> {
  final FocusNode _focusNode = FocusNode();
  bool _isFocused = false;

  @override
  void initState() {
    super.initState();
    _focusNode.addListener(_handleFocusChange);
  }

  void _handleFocusChange() {
    setState(() {
      _isFocused = _focusNode.hasFocus;
    });
  }

  @override
  void dispose() {
    _focusNode.removeListener(_handleFocusChange);
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          widget.label.toUpperCase(),
          style: AppTheme.textTheme.bodySmall?.copyWith(
            fontWeight: FontWeight.w600,
            letterSpacing: 1.2,
            color: AppColors.softCharcoal.withValues(alpha: 0.6),
          ),
        ),
        const SizedBox(height: 8),
        AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.6),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: _isFocused ? AppColors.warmCoral : Colors.white,
              width: 1.5,
            ),
            boxShadow: _isFocused
                ? [
                    BoxShadow(
                      color: AppColors.warmCoral.withValues(alpha: 0.2),
                      blurRadius: 8,
                      offset: const Offset(0, 2),
                    ),
                  ]
                : [],
          ),
          child: TextField(
            controller: widget.controller,
            focusNode: _focusNode,
            onChanged: widget.onChanged,
            textCapitalization: widget.textCapitalization,
            style: AppTheme.textTheme.bodyLarge,
            cursorColor: AppColors.warmCoral,
            maxLines: widget.maxLines,
            maxLength: widget.maxLength,
            decoration: InputDecoration(
              hintText: 'Enter your ${widget.label.toLowerCase()}',
              hintStyle: AppTheme.textTheme.bodyLarge?.copyWith(
                color: AppColors.softCharcoal.withValues(alpha: 0.3),
              ),
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 20,
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
