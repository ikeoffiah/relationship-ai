import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../portrait_api_service.dart';
import '../portrait_models.dart';

/// The first-open reveal: a specific, personal reading of how the user shows up
/// in relationships, built from their onboarding answers. Shown right after the
/// last onboarding step, before the completion / invite screen.
class RelationshipPortraitScreen extends StatefulWidget {
  const RelationshipPortraitScreen({super.key});

  @override
  State<RelationshipPortraitScreen> createState() => _RelationshipPortraitScreenState();
}

class _RelationshipPortraitScreenState extends State<RelationshipPortraitScreen> {
  final _api = PortraitApiService();
  late Future<RelationshipPortrait> _future;

  @override
  void initState() {
    super.initState();
    _future = _api.fetch();
  }

  void _continue() {
    Navigator.of(context).pushNamedAndRemoveUntil('/onboarding/complete', (r) => false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      body: SafeArea(
        child: FutureBuilder<RelationshipPortrait>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const _Loading();
            }
            final portrait = snap.data;
            if (snap.hasError || portrait == null || !portrait.ready) {
              return _Fallback(onContinue: _continue);
            }
            return _PortraitBody(portrait: portrait, onContinue: _continue);
          },
        ),
      ),
    );
  }
}

class _Loading extends StatelessWidget {
  const _Loading();

  @override
  Widget build(BuildContext context) => const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(color: AppColors.warmCoral),
            SizedBox(height: 20),
            Text('Reading your answers…', style: TextStyle(color: AppColors.softCharcoal)),
          ],
        ),
      );
}

class _Fallback extends StatelessWidget {
  final VoidCallback onContinue;
  const _Fallback({required this.onContinue});

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('✨', style: TextStyle(fontSize: 48)),
            const SizedBox(height: 16),
            const Text(
              'Your portrait is on its way',
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              "We'll have your personal relationship reading ready shortly.",
              textAlign: TextAlign.center,
              style: TextStyle(color: AppColors.softCharcoal),
            ),
            const SizedBox(height: 32),
            _ContinueButton(onPressed: onContinue, label: 'Continue'),
          ],
        ),
      );
}

class _PortraitBody extends StatelessWidget {
  final RelationshipPortrait portrait;
  final VoidCallback onContinue;
  const _PortraitBody({required this.portrait, required this.onContinue});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(24, 24, 24, 8),
            children: [
              Text(
                'YOUR RELATIONSHIP PORTRAIT',
                style: TextStyle(
                  fontSize: 12,
                  letterSpacing: 2,
                  fontWeight: FontWeight.w600,
                  color: AppColors.softCharcoal.withValues(alpha: 0.5),
                ),
              ),
              const SizedBox(height: 16),
              // Hero archetype card
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  gradient: AppColors.goldGradient,
                  borderRadius: BorderRadius.circular(24),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      portrait.archetype ?? '',
                      style: const TextStyle(
                        fontSize: 26,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                    if (portrait.headline != null) ...[
                      const SizedBox(height: 10),
                      Text(
                        portrait.headline!,
                        style: const TextStyle(fontSize: 16, height: 1.35, color: Colors.white),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 20),
              if (portrait.summary != null)
                Text(portrait.summary!, style: const TextStyle(fontSize: 16, height: 1.45)),
              const SizedBox(height: 24),
              if (portrait.whatHelps != null)
                _Section(emoji: '🛟', title: 'What helps you feel safe', body: portrait.whatHelps!),
              if (portrait.whatTripsYouUp != null)
                _Section(emoji: '⚡', title: 'What trips you up', body: portrait.whatTripsYouUp!),
              if (portrait.growthEdge != null)
                _Section(emoji: '🌱', title: 'Your growth edge', body: portrait.growthEdge!),
              if (portrait.communicationNote != null)
                _Section(emoji: '💬', title: 'How you communicate', body: portrait.communicationNote!),
              // The predictive punch — the "how did it know" moment.
              if (portrait.likelyFriction.isNotEmpty) _FrictionCard(items: portrait.likelyFriction),
              if (portrait.contextNote != null) ...[
                const SizedBox(height: 8),
                Text(
                  portrait.contextNote!,
                  style: TextStyle(
                    fontStyle: FontStyle.italic,
                    color: AppColors.softCharcoal.withValues(alpha: 0.75),
                    height: 1.4,
                  ),
                ),
              ],
              const SizedBox(height: 16),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 20),
          child: _ContinueButton(onPressed: onContinue, label: 'This is me — continue'),
        ),
      ],
    );
  }
}

class _Section extends StatelessWidget {
  final String emoji;
  final String title;
  final String body;
  const _Section({required this.emoji, required this.title, required this.body});

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 20),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(emoji, style: const TextStyle(fontSize: 20)),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title,
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                  const SizedBox(height: 4),
                  Text(body, style: const TextStyle(height: 1.4, color: AppColors.softCharcoal)),
                ],
              ),
            ),
          ],
        ),
      );
}

class _FrictionCard extends StatelessWidget {
  final List<String> items;
  const _FrictionCard({required this.items});

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        margin: const EdgeInsets.only(top: 4, bottom: 8),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: AppColors.warmCoral.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(20),
          border: Border(left: BorderSide(color: AppColors.warmCoral, width: 3)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Where your relationship will likely rub',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
            ),
            const SizedBox(height: 4),
            Text(
              'Given how you\'re wired, these are the patterns to watch for:',
              style: TextStyle(color: AppColors.softCharcoal.withValues(alpha: 0.75), fontSize: 13),
            ),
            const SizedBox(height: 12),
            for (final item in items)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('•  ', style: TextStyle(color: AppColors.warmCoral)),
                    Expanded(child: Text(item, style: const TextStyle(height: 1.35))),
                  ],
                ),
              ),
          ],
        ),
      );
}

class _ContinueButton extends StatelessWidget {
  final VoidCallback onPressed;
  final String label;
  const _ContinueButton({required this.onPressed, required this.label});

  @override
  Widget build(BuildContext context) => SizedBox(
        width: double.infinity,
        child: ElevatedButton(
          onPressed: onPressed,
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.warmCoral,
            padding: const EdgeInsets.symmetric(vertical: 16),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
          ),
          child: Text(label,
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 16)),
        ),
      );
}
