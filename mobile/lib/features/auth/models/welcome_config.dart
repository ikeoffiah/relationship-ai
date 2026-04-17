/// Configuration for the welcome screen
class WelcomeConfig {
  // Button labels
  static const String startButtonLabel = "Start Your Journey";
  static const String learnMoreButtonLabel = "Learn More";
  
  // Animation timing
  static const Duration logoFadeInDuration = Duration(milliseconds: 1200);
  static const double logoSlideUpDistance = 20.0;
  static const Duration headlineFadeDelay = Duration(milliseconds: 400);
  static const Duration headlineFadeDuration = Duration(milliseconds: 1000);
  static const Duration buttonAnimationDelay = Duration(milliseconds: 800);
  static const Duration buttonAnimationDuration = Duration(milliseconds: 800);
  static const Duration heartPulseDuration = Duration(milliseconds: 1500);
  static const Duration floatingShapesDuration = Duration(seconds: 8);
  static const Duration autoSlideInterval = Duration(seconds: 6);
  static const Duration slideTransitionDuration = Duration(milliseconds: 1200);
  static const Duration textBoxFadeDuration = Duration(milliseconds: 800);
  
  // Layout
  static const double logoTopPadding = 80.0;
  static const double buttonBottomPadding = 80.0;
  static const double buttonSpacing = 16.0;
  static const double buttonHeight = 60.0;
  static const double buttonHorizontalPadding = 40.0;
  static const double overlayHorizontalPadding = 24.0;
  static const double overlayBorderRadius = 20.0;
  static const double overlayOpacity = 0.65;
  
  // Slides
  static const List<WelcomeSlide> slides = [
    WelcomeSlide(
      imageAsset: 'assets/images/discovery.png',
      heading: 'Discover each other daily',
      body: 'Gently, playfully, meaningfully.',
      sparkles: true,
    ),
    WelcomeSlide(
      imageAsset: 'assets/images/understanding.png',
      heading: 'Understand before judgment',
      body: 'Communicate with curiosity.',
      sparkles: false,
    ),
    WelcomeSlide(
      imageAsset: 'assets/images/repair.png',
      heading: 'Turn tension into growth',
      body: 'Even small gestures matter.',
      sparkles: true,
    ),
    WelcomeSlide(
      imageAsset: 'assets/images/understanding.png',
      heading: 'Grow together',
      body: 'Create shared meaning.',
      sparkles: false,
    ),
  ];
}

class WelcomeSlide {
  final String imageAsset;
  final String heading;
  final String body;
  final bool sparkles;
  
  const WelcomeSlide({
    required this.imageAsset,
    required this.heading,
    required this.body,
    this.sparkles = false,
  });
}
