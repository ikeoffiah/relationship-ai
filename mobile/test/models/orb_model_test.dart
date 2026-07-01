import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/auth/models/orb_model.dart';

void main() {
  group('OrbModel Tests', () {
    test('OrbModel initializes with correct values', () {
      const orb = OrbModel(
        position: Offset(100, 100),
        size: 50,
        color: Colors.red,
        velocity: Offset(1, 1),
        glowIntensity: 0.8,
      );

      expect(orb.position, const Offset(100, 100));
      expect(orb.size, 50);
      expect(orb.color, Colors.red);
      expect(orb.velocity, const Offset(1, 1));
      expect(orb.glowIntensity, 0.8);
    });

    test('copyWith updates values correctly', () {
      const orb = OrbModel(
        position: Offset(100, 100),
        size: 50,
        color: Colors.blue,
        velocity: Offset(10, 20),
      );

      final updated = orb.copyWith(position: const Offset(110, 120));
      expect(updated.position, const Offset(110, 120));
      expect(updated.size, 50); // unchanged
      
      final updated2 = updated.copyWith(size: 100, color: Colors.green);
      expect(updated2.size, 100);
      expect(updated2.color, Colors.green);
      expect(updated2.position, const Offset(110, 120)); // preserved
    });
  });
}
