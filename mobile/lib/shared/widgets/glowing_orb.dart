import 'package:flutter/material.dart';
import 'package:mobile/features/auth/models/orb_model.dart';

/// Reusable widget for displaying a glowing orb
/// Features soft glow effect with no sharp corners
class GlowingOrb extends StatelessWidget {
  final OrbModel orb;

  const GlowingOrb({super.key, required this.orb});

  @override
  Widget build(BuildContext context) {
    return Positioned(
      left: orb.position.dx - orb.size / 2,
      top: orb.position.dy - orb.size / 2,
      child: Container(
        width: orb.size,
        height: orb.size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: orb.color,
          boxShadow: [
            // Multiple shadow layers for soft glow effect
            BoxShadow(
              color: orb.color.withValues(alpha: orb.glowIntensity * 0.6),
              blurRadius: 40,
              spreadRadius: 10,
            ),
            BoxShadow(
              color: orb.color.withValues(alpha: orb.glowIntensity * 0.4),
              blurRadius: 60,
              spreadRadius: 20,
            ),
            BoxShadow(
              color: orb.color.withValues(alpha: orb.glowIntensity * 0.2),
              blurRadius: 80,
              spreadRadius: 30,
            ),
          ],
        ),
      ),
    );
  }
}
