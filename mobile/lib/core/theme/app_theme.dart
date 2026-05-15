import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mobile/core/theme/app_colors.dart';

/// App theme configuration
/// Implements gentle, human-centered design principles
class AppTheme {
  // Animation durations - slow and gentle
  static const Duration slowFade = Duration(milliseconds: 1200);
  static const Duration gentleMotion = Duration(milliseconds: 1500);
  static const Duration orbAnimation = Duration(seconds: 4);

  // Typography - rounded, human sans-serif
  static TextTheme get textTheme {
    return TextTheme(
      // Headings - rounded, gentle
      displayLarge: GoogleFonts.inter(
        fontSize: 32,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.5,
        color: AppColors.softCharcoal,
      ),
      displayMedium: GoogleFonts.inter(
        fontSize: 28,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.5,
        color: AppColors.softCharcoal,
      ),
      displaySmall: GoogleFonts.inter(
        fontSize: 24,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.3,
        color: AppColors.softCharcoal,
      ),

      // Body text - highly readable, gentle line spacing
      bodyLarge: GoogleFonts.inter(
        fontSize: 16,
        fontWeight: FontWeight.w400,
        height: 1.6,
        letterSpacing: 0.15,
        color: AppColors.softCharcoal,
      ),
      bodyMedium: GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w400,
        height: 1.6,
        letterSpacing: 0.25,
        color: AppColors.softCharcoal,
      ),
      bodySmall: GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        height: 1.5,
        letterSpacing: 0.4,
        color: AppColors.softCharcoal.withValues(alpha: 0.7),
      ),
      headlineSmall: GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.2,
        color: AppColors.softCharcoal,
      ),
    );
  }

  // Light theme
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.light(
        primary: AppColors.warmCoral,
        secondary: AppColors.calmTeal,
        surface: AppColors.creamWhite,
        onPrimary: Colors.white,
        onSecondary: Colors.white,
        onSurface: AppColors.softCharcoal,
      ),
      textTheme: textTheme,
      scaffoldBackgroundColor: AppColors.creamWhite,

      // No harsh elements
      dividerColor: AppColors.softCharcoal.withValues(alpha: 0.1),

      // Rounded corners everywhere
      cardTheme: CardThemeData(
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      ),
    );
  }
}
