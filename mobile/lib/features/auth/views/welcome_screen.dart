import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/features/auth/viewmodels/welcome_viewmodel.dart';
import 'package:mobile/features/auth/models/welcome_config.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/shared/widgets/animated_button.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'dart:math' as math;
import 'dart:ui' as ui;

/// Welcome & Onboarding screen
/// Sets emotional tone with gentle animations and warm design
class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});

  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen>
    with TickerProviderStateMixin {
  @override
  void initState() {
    super.initState();

    // Initialize ViewModel after first frame
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final viewModel = context.read<WelcomeViewModel>();
      viewModel.initialize(this);
    });
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;

    return Scaffold(
      body: Consumer<WelcomeViewModel>(
        builder: (context, viewModel, child) {
          if (!viewModel.isInitialized) {
            return const SizedBox.shrink();
          }

          return Stack(
            children: [
              // Background carousel with parallax
              PageView.builder(
                controller: viewModel.pageController,
                onPageChanged: viewModel.onPageChanged,
                itemCount: WelcomeConfig.slides.length,
                itemBuilder: (context, index) {
                  final slide = WelcomeConfig.slides[index];
                  final page = viewModel.page;
                  final delta = (index - page);
                  final parallaxX = -delta * 20; // gentle parallax

                  return Stack(
                    children: [
                      Positioned.fill(
                        child: Transform.translate(
                          offset: Offset(parallaxX, 0),
                          child: Opacity(
                            opacity: (1.0 - (delta.abs() * 0.3)).clamp(
                              0.4,
                              1.0,
                            ),
                            child: Image.asset(
                              slide.imageAsset,
                              fit: BoxFit.cover,
                            ),
                          ),
                        ),
                      ),
                      // Subtle sparkles on some slides
                      if (slide.sparkles) _buildSparkles(size),
                    ],
                  );
                },
              ),

              // Top logo
              SafeArea(
                child: Align(
                  alignment: Alignment.topCenter,
                  child: Padding(
                    padding: EdgeInsets.only(top: WelcomeConfig.logoTopPadding),
                    child: FadeTransition(
                      opacity: viewModel.getLogoFadeAnimation(),
                      child: AnimatedBuilder(
                        animation: viewModel.getLogoSlideAnimation(),
                        builder: (context, child) {
                          return Transform.translate(
                            offset: Offset(
                              0,
                              viewModel.getLogoSlideAnimation().value,
                            ),
                            child: child,
                          );
                        },
                        child: AnimatedBuilder(
                          animation: viewModel.getLogoFloatController(),
                          builder: (context, child) {
                            final floatY =
                                math.sin(
                                  viewModel.logoFloatProgress * 2 * math.pi,
                                ) *
                                4;
                            return Transform.translate(
                              offset: Offset(0, floatY),
                              child: child,
                            );
                          },
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(999),
                            child: BackdropFilter(
                              filter: ui.ImageFilter.blur(
                                sigmaX: 10,
                                sigmaY: 10,
                              ),
                              child: Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 14,
                                  vertical: 10,
                                ),
                                decoration: BoxDecoration(
                                  color: Colors.white.withValues(alpha: 0.08),
                                  borderRadius: BorderRadius.circular(999),
                                  border: Border.all(
                                    color: Colors.white.withValues(alpha: 0.25),
                                    width: 1,
                                  ),
                                ),
                                child: Image.asset(
                                  'assets/images/bliss_logo.png',
                                  height: 28,
                                  color: Colors.white.withValues(alpha: 0.95),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),

              Positioned(
                left: 0,
                right: 0,
                bottom: 0,
                child: _buildBottomArea(context),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildBottomArea(BuildContext context) {
    final viewModel = context.watch<WelcomeViewModel>();
    final slide = WelcomeConfig.slides[viewModel.currentIndex];
    final size = MediaQuery.of(context).size;

    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color.fromARGB(0, 255, 255, 255), Colors.white],
          stops: [0.0, 0.35],
        ),
      ),
      child: SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(
            minHeight: size.height * 0.35,
            maxHeight: size.height * 0.5,
          ),
          child: SingleChildScrollView(
            physics: const ClampingScrollPhysics(),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                mainAxisSize: MainAxisSize.min,
                children: [
                  const SizedBox(height: 8),
                  // Text content with fade animation
                  FadeTransition(
                    opacity: viewModel.getTextBoxFadeAnimation(),
                    child: Column(
                      children: [
                        Text(
                          slide.heading,
                          textAlign: TextAlign.center,
                          style: AppTheme.textTheme.displaySmall?.copyWith(
                            color: Colors.black,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          slide.body,
                          textAlign: TextAlign.center,
                          style: AppTheme.textTheme.bodyLarge?.copyWith(
                            color: Colors.black,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  _buildIndicators(context),
                  const SizedBox(height: 24),
                  // Buttons remain static (no fade/scale on page change)
                  _buildCTAInline(context),
                  const SizedBox(height: 8),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildIndicators(BuildContext context) {
    final viewModel = context.watch<WelcomeViewModel>();
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(WelcomeConfig.slides.length, (i) {
        final active = i == viewModel.currentIndex;
        final dot = AnimatedContainer(
          duration: const Duration(milliseconds: 300),
          width: active ? 16 : 10,
          height: 10,
          decoration: BoxDecoration(
            color: active ? AppColors.warmCoral : Colors.transparent,
            border: Border.all(
              color: active
                  ? AppColors.warmCoral
                  : AppColors.warmCoral.withValues(alpha: 0.4),
              width: 2,
            ),
            borderRadius: BorderRadius.circular(999),
          ),
          margin: const EdgeInsets.symmetric(horizontal: 6),
        );
        return active
            ? ScaleTransition(
                scale: viewModel.getIndicatorPulseAnimation(),
                child: dot,
              )
            : dot;
      }),
    );
  }

  Widget _buildCTAInline(BuildContext context) {
    final viewModel = context.read<WelcomeViewModel>();

    // Buttons are static - only animate on initial load
    return AnimatedOpacity(
      opacity: viewModel.isInitialized ? 1.0 : 0.0,
      duration: const Duration(milliseconds: 800),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          AnimatedButton(
            label: WelcomeConfig.startButtonLabel,
            onTap: () => viewModel.onStartTapped(context),
            isFilled: true,
            useGoldGradient: false,
            height: WelcomeConfig.buttonHeight,
            borderRadius: 14,
          ),
          const SizedBox(height: WelcomeConfig.buttonSpacing),
          AnimatedButton(
            label: WelcomeConfig.learnMoreButtonLabel,
            onTap: () => viewModel.onLearnMoreTapped(context),
            isFilled: false,
            height: WelcomeConfig.buttonHeight,
            borderRadius: 14,
            outlineColor: AppColors.warmCoral,
          ),
        ],
      ),
    );
  }

  Widget _buildSparkles(Size size) {
    final rnd = math.Random();
    List<Widget> icons = [];
    for (int i = 0; i < 6; i++) {
      final left = rnd.nextDouble() * size.width;
      final top = (rnd.nextDouble() * size.height * 0.7) + 40;
      final isHeart = rnd.nextBool();
      icons.add(
        Positioned(
          left: left,
          top: top,
          child: Icon(
            isHeart ? Icons.favorite : Icons.spa_rounded,
            color: Colors.white.withValues(alpha: 0.12),
            size: 16 + rnd.nextDouble() * 8,
          ),
        ),
      );
    }
    return Stack(children: icons);
  }
}
