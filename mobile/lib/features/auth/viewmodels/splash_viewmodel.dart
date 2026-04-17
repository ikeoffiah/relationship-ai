import 'dart:math';
import 'package:flutter/material.dart';
import 'package:mobile/features/auth/models/orb_model.dart';
import 'package:mobile/features/auth/models/splash_config.dart';
import 'package:mobile/core/theme/app_colors.dart';

/// ViewModel for the splash screen
/// Manages animation state and business logic
class SplashViewModel extends ChangeNotifier {
  late AnimationController _orbController;
  late AnimationController _textController;

  OrbModel? _orb1;
  OrbModel? _orb2;

  bool _isInitialized = false;
  VoidCallback? _onAnimationComplete;

  bool get isInitialized => _isInitialized;
  OrbModel? get orb1 => _orb1;
  OrbModel? get orb2 => _orb2;

  /// Initialize animation controllers
  void initialize(
    TickerProvider vsync,
    Size screenSize, {
    VoidCallback? onAnimationComplete,
  }) {
    if (_isInitialized) return;

    _onAnimationComplete = onAnimationComplete;

    // Create animation controllers
    _orbController = AnimationController(
      duration: SplashConfig.orbMovementDuration,
      vsync: vsync,
    );

    _textController = AnimationController(
      duration: SplashConfig.textFadeInDuration,
      vsync: vsync,
    );

    // Initialize orbs with starting positions
    _initializeOrbs(screenSize);

    // Start animations
    _startAnimations();

    _isInitialized = true;
    notifyListeners();
  }

  /// Initialize orb positions
  void _initializeOrbs(Size screenSize) {
    final centerX = screenSize.width / 2;
    final centerY = screenSize.height / 2;

    // Orb 1 - starts upper left
    _orb1 = OrbModel(
      position: Offset(centerX - 80, centerY - 100),
      velocity: const Offset(0.3, 0.2),
      size: SplashConfig.orb1Size,
      color: AppColors.warmCoral.withValues(alpha: 0.6),
      glowIntensity: SplashConfig.orbGlowIntensity,
    );

    // Orb 2 - starts lower right
    _orb2 = OrbModel(
      position: Offset(centerX + 60, centerY + 80),
      velocity: const Offset(-0.25, -0.18),
      size: SplashConfig.orb2Size,
      color: AppColors.softRose.withValues(alpha: 0.6),
      glowIntensity: SplashConfig.orbGlowIntensity,
    );
  }

  /// Start animations
  void _startAnimations() {
    // Listen to orb animation
    _orbController.addListener(_updateOrbPositions);

    // Listen for animation completion
    _orbController.addStatusListener((status) {
      if (status == AnimationStatus.completed) {
        // Wait a bit after animation completes, then navigate
        Future.delayed(const Duration(seconds: 1), () {
          _onAnimationComplete?.call();
        });
      }
    });

    // Start orb movement
    _orbController.forward();

    // Delay text fade in
    Future.delayed(SplashConfig.textFadeInDelay, () {
      _textController.forward();
    });
  }

  /// Update orb positions with organic movement
  void _updateOrbPositions() {
    if (_orb1 == null || _orb2 == null) return;

    final progress = _orbController.value;

    // Use custom curve for gentle, organic motion
    final curvedProgress = Curves.easeInOutCubic.transform(progress);

    // Add slight drift with sine wave for organic feel
    final drift1 = sin(progress * pi * 2) * 15;
    final drift2 = cos(progress * pi * 2) * 12;

    // Calculate new positions - slowly moving closer
    final newPos1 = Offset(
      _orb1!.position.dx + (_orb1!.velocity.dx * curvedProgress) + drift1,
      _orb1!.position.dy + (_orb1!.velocity.dy * curvedProgress),
    );

    final newPos2 = Offset(
      _orb2!.position.dx + (_orb2!.velocity.dx * curvedProgress) + drift2,
      _orb2!.position.dy + (_orb2!.velocity.dy * curvedProgress),
    );

    _orb1 = _orb1!.copyWith(position: newPos1);
    _orb2 = _orb2!.copyWith(position: newPos2);

    notifyListeners();
  }

  /// Get text fade animation
  Animation<double> getTextFadeAnimation() {
    return CurvedAnimation(parent: _textController, curve: Curves.easeIn);
  }

  /// Clean up resources
  @override
  void dispose() {
    if (_isInitialized) {
      _orbController.dispose();
      _textController.dispose();
    }
    super.dispose();
  }
}
