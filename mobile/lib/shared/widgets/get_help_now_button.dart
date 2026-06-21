import 'package:flutter/material.dart';

class GetHelpNowButton extends StatelessWidget {
  final bool compact;
  
  const GetHelpNowButton({super.key, this.compact = false});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: compact ? null : double.infinity,
      color: const Color(0xFFB71C1C), // Deep red, non-negotiable color
      child: TextButton.icon(
        icon: const Icon(Icons.emergency, color: Colors.white),
        label: const Text(
          'Get Help Now',
          style: TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.bold,
          ),
        ),
        onPressed: () => Navigator.of(context).pushNamed('/safety'),
      ),
    );
  }
}
