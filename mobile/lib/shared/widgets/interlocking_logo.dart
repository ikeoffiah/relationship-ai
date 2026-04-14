import 'package:flutter/material.dart';
import 'package:mobile/core/theme/app_colors.dart';

/// Interlocking logo representing two people coming together
/// Features warm coral gradient and smooth animations
class InterlockingLogo extends StatelessWidget {
  final double size;
  
  const InterlockingLogo({
    super.key,
    this.size = 80.0,
  });
  
  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(
        painter: _InterlockingLogoPainter(),
      ),
    );
  }
}

class _InterlockingLogoPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..shader = AppColors.splashGradient.createShader(
        Rect.fromLTWH(0, 0, size.width, size.height),
      )
      ..style = PaintingStyle.fill;
    
    final strokePaint = Paint()
      ..color = AppColors.warmCoral
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.0
      ..strokeCap = StrokeCap.round;
    
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 3;
    
    // Left circle (person 1)
    final leftCircle = Path()
      ..addOval(Rect.fromCircle(
        center: Offset(center.dx - radius * 0.5, center.dy),
        radius: radius,
      ));
    
    // Right circle (person 2)
    final rightCircle = Path()
      ..addOval(Rect.fromCircle(
        center: Offset(center.dx + radius * 0.5, center.dy),
        radius: radius,
      ));
    
    // Create interlocking effect by combining paths
    final combinedPath = Path.combine(
      PathOperation.union,
      leftCircle,
      rightCircle,
    );
    
    // Draw with gradient fill
    canvas.drawPath(combinedPath, paint);
    
    // Draw outline for definition
    canvas.drawPath(combinedPath, strokePaint);
  }
  
  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
