/// Configuration for the splash screen
class SplashConfig {
  // Animation timing
  static const Duration totalDuration = Duration(seconds: 5);
  static const Duration orbMovementDuration = Duration(seconds: 4);
  static const Duration textFadeInDelay = Duration(milliseconds: 800);
  static const Duration textFadeInDuration = Duration(milliseconds: 1200);
  
  // Text content
  static const String mainText = "Love grows with understanding.";
  static const String subText = "A shared space for reflection and connection";
  
  // Orb configuration
  static const double orb1Size = 120.0;
  static const double orb2Size = 100.0;
  static const double orbGlowIntensity = 0.7;
  
  // Layout
  static const double textBottomPadding = 120.0;
  static const double textSpacing = 16.0;
}
