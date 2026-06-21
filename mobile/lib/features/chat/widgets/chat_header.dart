import 'package:flutter/material.dart';
import 'package:mobile/features/chat/models/chat_models.dart';

class ChatHeader extends StatelessWidget {
  final SessionState session;

  const ChatHeader({super.key, required this.session});

  void _confirmExitJoint(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Exit to private session?'),
        content: const Text('Your partner will be notified that you stepped out. You can rejoin at any time.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              // Handle exit logic in parent
            },
            child: const Text('Exit'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: Colors.grey.shade200)),
      ),
      child: Row(
        children: [
          if (session.isIndividual)
            Row(
              children: [
                const Icon(Icons.lock_outline, size: 16, color: Colors.green),
                const SizedBox(width: 4),
                const Text('Your private session', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
              ],
            ),
          if (session.isJoint)
            Row(
              children: [
                CircleAvatar(
                  radius: 12, 
                  backgroundColor: Colors.blue.shade100,
                  child: Text(session.partnerInitial, style: const TextStyle(fontSize: 12)),
                ),
                const SizedBox(width: 6),
                Text('Session with ${session.partnerFirstName}', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
              ],
            ),
          const Spacer(),
          if (session.isJoint)
            TextButton.icon(
              onPressed: () => _confirmExitJoint(context),
              icon: const Icon(Icons.logout, size: 16, color: Colors.orange),
              label: const Text('Step out', style: TextStyle(fontSize: 12, color: Colors.orange)),
            ),
        ],
      ),
    );
  }
}
