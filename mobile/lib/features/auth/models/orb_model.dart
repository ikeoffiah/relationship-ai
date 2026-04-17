import 'package:flutter/material.dart';

/// Model representing an animated orb
class OrbModel {
  final Offset position;
  final Offset velocity;
  final double size;
  final Color color;
  final double glowIntensity;
  
  const OrbModel({
    required this.position,
    required this.velocity,
    required this.size,
    required this.color,
    this.glowIntensity = 0.6,
  });
  
  /// Create a copy with updated values
  OrbModel copyWith({
    Offset? position,
    Offset? velocity,
    double? size,
    Color? color,
    double? glowIntensity,
  }) {
    return OrbModel(
      position: position ?? this.position,
      velocity: velocity ?? this.velocity,
      size: size ?? this.size,
      color: color ?? this.color,
      glowIntensity: glowIntensity ?? this.glowIntensity,
    );
  }
}
