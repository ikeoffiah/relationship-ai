import 'package:flutter/material.dart';

/// Color palette for the couples app
/// Designed to evoke warmth, safety, and emotional connection
class AppColors {
  // Primary colors - love and warmth
  static const Color warmCoral = Color(0xFFFF9B8A);
  static const Color softRose = Color(0xFFFFB5C5);
  static const Color rosePeach = Color(0xFFFFD4C8);

  // Secondary colors - safety and regulation
  static const Color calmTeal = Color(0xFF7EBDB4);
  static const Color sageGreen = Color(0xFFA8C5B0);

  // Neutrals
  static const Color creamWhite = Color(0xFFFFFBF5);
  static const Color softCharcoal = Color(0xFF4A4A4A);

  // Accent - growth and milestones
  static const Color goldLight = Color(0xFFFFD89B);
  static const Color goldMedium = Color(0xFFFFC870);
  static const Color goldDark = Color(0xFFFFB84D);

  // Error color
  static const Color error = Color.fromARGB(255, 245, 140, 140);

  // Gradient definitions
  static const LinearGradient splashGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [softRose, rosePeach],
  );

  static const LinearGradient goldGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [goldLight, goldMedium, goldDark],
  );

  static const LinearGradient redGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFFFFCDD2), // light red
      Color(0xFFE53935), // medium red
      Color(0xFFB71C1C), // dark red
    ],
  );
}
