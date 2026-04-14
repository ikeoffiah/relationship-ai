import 'package:mobile/features/auth/views/login_screen.dart';
import 'package:mobile/features/auth/views/signup_screen.dart';
import 'package:flutter/material.dart';
import 'package:mobile/features/auth/models/welcome_config.dart';

/// ViewModel for the welcome screen
/// Manages animation state and navigation logic
class WelcomeViewModel extends ChangeNotifier {
  late AnimationController _logoController;
  late AnimationController _buttonController;
  late AnimationController _heartPulseController;
  late AnimationController _textBoxController;
  late AnimationController _indicatorPulseController;
  late AnimationController _logoFloatController;

  late PageController _pageController;
  int _currentIndex = 0;
  // ignore: unused_field
  double _page = 0.0;

  bool _isInitialized = false;
  bool get isInitialized => _isInitialized;

  PageController get pageController => _pageController;
  int get currentIndex => _currentIndex;
  double get page => _pageController.hasClients
      ? (_pageController.page ?? _currentIndex.toDouble())
      : _currentIndex.toDouble();

  /// Initialize animation controllers
  void initialize(TickerProvider vsync) {
    if (_isInitialized) return;

    _logoController = AnimationController(
      duration: WelcomeConfig.logoFadeInDuration,
      vsync: vsync,
    );

    _buttonController = AnimationController(
      duration: WelcomeConfig.buttonAnimationDuration,
      vsync: vsync,
    );

    _heartPulseController = AnimationController(
      duration: WelcomeConfig.heartPulseDuration,
      vsync: vsync,
    );

    _textBoxController = AnimationController(
      duration: WelcomeConfig.textBoxFadeDuration,
      vsync: vsync,
    );

    _indicatorPulseController = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: vsync,
    );

    _logoFloatController = AnimationController(
      duration: const Duration(seconds: 4),
      vsync: vsync,
    );

    _pageController = PageController(viewportFraction: 1.0);
    _pageController.addListener(() {
      _page = page;
      notifyListeners();
    });

    _startAnimations();
    _startAutoSlide();
    _isInitialized = true;
    notifyListeners();
  }

  /// Start all animations in sequence
  void _startAnimations() {
    // Logo fade in and slide up
    _logoController.forward();

    // Button animations after delay
    Future.delayed(WelcomeConfig.buttonAnimationDelay, () {
      _buttonController.forward();
    });

    // Heart pulse (repeating)
    _heartPulseController.repeat(reverse: true);

    // Indicators pulse (repeating)
    _indicatorPulseController.repeat(reverse: true);

    // Logo gentle float
    _logoFloatController.repeat();

    // Initial text box fade
    _textBoxController.forward(from: 0.0);
  }

  void _startAutoSlide() {
    Future.delayed(WelcomeConfig.autoSlideInterval, () async {
      if (!_pageController.hasClients) return;
      final next = (_currentIndex + 1) % WelcomeConfig.slides.length;
      _animateToPage(next);
      _startAutoSlide();
    });
  }

  void onPageChanged(int index) {
    _currentIndex = index;
    _textBoxController.forward(from: 0.0);
    notifyListeners();
  }

  /// Get logo fade animation
  Animation<double> getLogoFadeAnimation() {
    return CurvedAnimation(parent: _logoController, curve: Curves.easeOut);
  }

  /// Get logo slide animation
  Animation<double> getLogoSlideAnimation() {
    return Tween<double>(
      begin: WelcomeConfig.logoSlideUpDistance,
      end: 0.0,
    ).animate(CurvedAnimation(parent: _logoController, curve: Curves.easeOut));
  }

  /// Get button scale animation
  Animation<double> getButtonScaleAnimation() {
    return Tween<double>(begin: 0.9, end: 1.0).animate(
      CurvedAnimation(parent: _buttonController, curve: Curves.easeOut),
    );
  }

  /// Get button fade animation
  Animation<double> getButtonFadeAnimation() {
    return CurvedAnimation(parent: _buttonController, curve: Curves.easeIn);
  }

  /// Get heart pulse animation
  Animation<double> getHeartPulseAnimation() {
    return Tween<double>(begin: 1.0, end: 1.15).animate(
      CurvedAnimation(parent: _heartPulseController, curve: Curves.easeInOut),
    );
  }

  /// Get text box fade animation
  Animation<double> getTextBoxFadeAnimation() {
    return CurvedAnimation(parent: _textBoxController, curve: Curves.easeIn);
  }

  /// Get indicator pulse animation
  Animation<double> getIndicatorPulseAnimation() {
    return Tween<double>(begin: 1.0, end: 1.2).animate(
      CurvedAnimation(
        parent: _indicatorPulseController,
        curve: Curves.easeInOut,
      ),
    );
  }

  void _animateToPage(int index) {
    _pageController.animateToPage(
      index,
      duration: WelcomeConfig.slideTransitionDuration,
      curve: Curves.easeInOut,
    );
    onPageChanged(index);
  }

  Animation<double> getLogoFloatController() => _logoFloatController;
  double get logoFloatProgress => _logoFloatController.value;

  /// Handle start button tap
  void onStartTapped(BuildContext context) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => const LoginScreen()),
    );
    debugPrint('Start button tapped');
  }

  /// Handle learn more button tap
  void onLearnMoreTapped(BuildContext context) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => const SignupScreen()),
    );
    debugPrint('Learn More button tapped');
  }

  /// Clean up resources
  @override
  void dispose() {
    if (_isInitialized) {
      _logoController.dispose();
      _buttonController.dispose();
      _heartPulseController.dispose();
      _textBoxController.dispose();
      _indicatorPulseController.dispose();
      _logoFloatController.dispose();
      _pageController.dispose();
    }
    super.dispose();
  }
}
