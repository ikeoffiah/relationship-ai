import 'package:flutter/material.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/consent/consent_summary_sheet.dart';
import 'package:mobile/features/consent/widgets/consent_badge.dart';

/// The main chat session screen.
///
/// Per Section 14.1: the consent summary sheet is shown before any chat
/// content is visible. The [ConsentBadge] is always visible in the app bar.
///
/// The [userId] is required for all consent API calls.
class ChatScreen extends StatefulWidget {
  final String userId;

  const ChatScreen({super.key, required this.userId});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  bool _sessionStarted = false;

  @override
  void initState() {
    super.initState();
    // Show the consent sheet after the first frame renders,
    // before any chat content is visible to the user.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _showConsentSheet();
    });
  }

  Future<void> _showConsentSheet() async {
    try {
      final started = await ConsentSummarySheet.show(context, widget.userId);
      if (mounted) {
        setState(() => _sessionStarted = started);
      }
    } catch (e) {
      // Re-throw or handle error if sheet fails to open
      debugPrint('ConsentSummarySheet failed to show: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: AppColors.creamWhite,
        elevation: 0,
        centerTitle: false,
        title: Text(
          'Session',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                color: AppColors.softCharcoal,
              ),
        ),
        actions: [
          // ConsentBadge always visible — Section 14.1
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: ConsentBadge(userId: widget.userId),
          ),
        ],
      ),
      body: _sessionStarted ? _ChatBody() : _SessionBlockedState(),
    );
  }
}

/// Placeholder chat body — shown only after "Start session" is tapped.
class _ChatBody extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Center(
      key: const Key('chat_body'),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.chat_bubble_outline,
            size: 64,
            color: AppColors.rosePeach,
          ),
          const SizedBox(height: 16),
          Text(
            'Session started',
            key: const Key('session_started_label'),
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  color: AppColors.softCharcoal.withValues(alpha: 0.6),
                ),
          ),
        ],
      ),
    );
  }
}

/// Empty state shown while consent sheet blocks session start.
class _SessionBlockedState extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return const SizedBox.shrink();
  }
}
