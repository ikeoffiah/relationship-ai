import 'package:flutter/material.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';
import 'package:mobile/features/consent/consent_summary_sheet.dart';
import 'package:mobile/features/chat/widgets/in_session_consent_banner.dart';
import 'package:mobile/features/consent/widgets/consent_badge.dart';
import 'package:mobile/shared/widgets/get_help_now_button.dart';
import 'package:mobile/features/chat/providers/chat_provider.dart';
import 'package:mobile/features/chat/models/chat_models.dart';
import 'package:mobile/features/chat/widgets/chat_header.dart';
import 'package:mobile/features/chat/widgets/message_list.dart';
import 'package:mobile/features/chat/widgets/message_input.dart';
import 'package:mobile/features/chat/widgets/safety_protocol_modal.dart';

/// The main chat session screen.
///
/// Per Section 14.1: the consent summary sheet is shown before any chat
/// content is visible. The [ConsentBadge] is always visible in the app bar.
///
/// The [userId] is required for all consent API calls.
class ChatScreen extends StatefulWidget {
  final String userId;
  final bool isJointSession;
  final String? jointSessionId;

  const ChatScreen({
    super.key,
    required this.userId,
    this.isJointSession = false,
    this.jointSessionId,
  });

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  bool _sessionStarted = false;

  // A joint session carries its server-issued id; an individual session gets a
  // fresh client-generated id so its turns persist under one history entry.
  late final String _sessionId =
      widget.jointSessionId ?? const Uuid().v4();

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

  Future<void> _handleStepOut() async {
    // In a real app, this would call the API and then navigate back to individual chat
    // For now, we just pop the current joint session state
    Navigator.of(context).pop();
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
          const GetHelpNowButton(compact: true),
          if (widget.isJointSession)
            TextButton(
              onPressed: () => _handleStepOut(),
              child: const Text('Step out', style: TextStyle(color: Colors.orange)),
            ),
          // ConsentBadge always visible — Section 14.1
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: ConsentBadge(userId: widget.userId),
          ),
        ],
      ),
      body: Column(
        children: [
          if (_sessionStarted) const InSessionConsentBanner(),
          Expanded(
            child: _sessionStarted 
              ? _ChatBody(
                  key: const Key('chat_body'),
                  sessionId: _sessionId,
                  sessionState: SessionState(
                    isIndividual: !widget.isJointSession,
                    isJoint: widget.isJointSession,
                    partnerInitial: 'P',
                    partnerFirstName: 'Partner',
                  ),
                ) 
              : _SessionBlockedState(),
          ),
        ],
      ),
    );
  }
}

class _ChatBody extends ConsumerStatefulWidget {
  final String sessionId;
  final SessionState sessionState;

  const _ChatBody({super.key, required this.sessionId, required this.sessionState});

  @override
  ConsumerState<_ChatBody> createState() => _ChatBodyState();
}

class _ChatBodyState extends ConsumerState<_ChatBody> {
  final ScrollController _scrollController = ScrollController();

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent + 100,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(chatProvider(widget.sessionId));

    // Handle safety modal trigger
    ref.listen(chatProvider(widget.sessionId), (previous, next) {
      if (next.safetyOverlayLevel != null && previous?.safetyOverlayLevel == null) {
        showDialog(
          context: context,
          barrierDismissible: false,
          builder: (_) => SafetyProtocolModal(
            level: next.safetyOverlayLevel!,
            resources: next.safetyOverlayResources ?? [],
          ),
        );
      }
      
      if (next.messages.length > (previous?.messages.length ?? 0)) {
        Future.delayed(const Duration(milliseconds: 100), _scrollToBottom);
      }
    });

    final isTurnHold = chatState.turnHoldCountdown > 0;

    return Column(
      children: [
        ChatHeader(session: widget.sessionState),
        _AIDisclosureBanner(),
        if (isTurnHold) _TurnHoldBanner(countdown: chatState.turnHoldCountdown),
        Expanded(
          child: MessageList(
            messages: chatState.messages,
            controller: _scrollController,
            onRejectReframe: (correction) {
              // TODO: Find message ID for the reframe correction
            },
          ),
        ),
        MessageInput(
          disabled: isTurnHold,
          onSend: (text) {
            ref.read(chatProvider(widget.sessionId).notifier).sendMessage(text);
            Future.delayed(const Duration(milliseconds: 100), _scrollToBottom);
          },
        ),
      ],
    );
  }
}

class _AIDisclosureBanner extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      color: Colors.grey.shade100,
      padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 12),
      child: Row(
        children: [
          const Icon(Icons.smart_toy_outlined, size: 14, color: Colors.grey),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              'You are talking to an AI, not a licensed therapist.',
              style: TextStyle(fontSize: 11, color: Colors.grey.shade700),
            ),
          ),
          TextButton(
            onPressed: () {},
            child: Text('Learn more', style: TextStyle(fontSize: 11, color: Colors.blue.shade600)),
          ),
        ],
      ),
    );
  }
}

class _TurnHoldBanner extends StatelessWidget {
  final int countdown;

  const _TurnHoldBanner({required this.countdown});

  @override
  Widget build(BuildContext context) {
    if (countdown <= 0) return const SizedBox.shrink();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 16),
      color: Colors.indigo.shade50,
      child: Text(
        'Take a moment to reflect before responding... ($countdown)',
        style: TextStyle(color: Colors.indigo.shade700, fontSize: 13),
        textAlign: TextAlign.center,
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
