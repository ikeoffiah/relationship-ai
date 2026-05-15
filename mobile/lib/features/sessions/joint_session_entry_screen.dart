import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/features/sessions/joint_session_viewmodel.dart';
import 'package:mobile/shared/widgets/animated_button.dart';
import 'package:mobile/core/theme/app_colors.dart';

class JointSessionEntryScreen extends StatelessWidget {
  final bool isInitiator;
  final String partnerName;

  const JointSessionEntryScreen({
    super.key,
    required this.isInitiator,
    required this.partnerName,
  });

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => JointSessionViewModel(),
      child: _JointSessionEntryContent(
        isInitiator: isInitiator,
        partnerName: partnerName,
      ),
    );
  }
}

class _JointSessionEntryContent extends StatefulWidget {
  final bool isInitiator;
  final String partnerName;

  const _JointSessionEntryContent({
    required this.isInitiator,
    required this.partnerName,
  });

  @override
  State<_JointSessionEntryContent> createState() => _JointSessionEntryContentState();
}

class _JointSessionEntryContentState extends State<_JointSessionEntryContent> {
  @override
  void initState() {
    super.initState();
    if (widget.isInitiator) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        context.read<JointSessionViewModel>().initiateJointSession();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final viewModel = context.watch<JointSessionViewModel>();

    return Scaffold(
      backgroundColor: AppColors.softIvory,
      appBar: AppBar(
        title: const Text('Joint Session'),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            const Spacer(),
            Icon(
              Icons.people_outline,
              size: 80,
              color: AppColors.warmCoral,
            ),
            const SizedBox(height: 32),
            if (viewModel.status == JointSessionStatus.pendingA || viewModel.status == JointSessionStatus.pendingB)
              _buildPendingView(viewModel)
            else if (viewModel.status == JointSessionStatus.active)
              _buildActiveView(viewModel)
            else if (viewModel.status == JointSessionStatus.terminated)
              _buildTerminatedView(viewModel)
            else if (viewModel.status == JointSessionStatus.none && !widget.isInitiator)
              _buildInviteView(viewModel)
            else
              const CircularProgressIndicator(),
            const Spacer(),
          ],
        ),
      ),
    );
  }

  Widget _buildPendingView(JointSessionViewModel viewModel) {
    return Column(
      children: [
        Text(
          'Waiting for ${widget.partnerName} to join...',
          style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 16),
        const Text(
          'You\'ve opened a joint session. Your partner will receive a notification.\nThere\'s no pressure — they can join when ready, or you can continue individually.',
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.grey),
        ),
        const SizedBox(height: 40),
        AnimatedButton(
          label: 'Continue individually',
          onTap: () => Navigator.pop(context),
          isFilled: false,
        ),
        const SizedBox(height: 12),
        TextButton(
          onPressed: () => viewModel.exitSession(),
          child: const Text('Cancel invite', style: TextStyle(color: Colors.red)),
        ),
      ],
    );
  }

  Widget _buildInviteView(JointSessionViewModel viewModel) {
    return Column(
      children: [
        Text(
          '${widget.partnerName} has opened a joint session.',
          style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 16),
        const Text(
          'You can join when you\'re ready. This is completely optional.\nYou can leave at any time — no explanation needed.',
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.grey),
        ),
        const SizedBox(height: 40),
        AnimatedButton(
          label: 'Join the session',
          onTap: () => viewModel.confirmReady(),
        ),
        const SizedBox(height: 12),
        AnimatedButton(
          label: 'Continue individually',
          onTap: () => Navigator.pop(context),
          isFilled: false,
        ),
      ],
    );
  }

  Widget _buildActiveView(JointSessionViewModel viewModel) {
    return Column(
      children: [
        const Text(
          'You\'re both here.',
          style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 16),
        const Text(
          'This is a joint session. Either of you can return to individual mode at any time using the "Step out" button.',
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 40),
        AnimatedButton(
          label: 'Begin',
          onTap: () {
            // Navigate to joint chat screen
          },
          useGoldGradient: true,
        ),
      ],
    );
  }

  Widget _buildTerminatedView(JointSessionViewModel viewModel) {
    return Column(
      children: [
        const Text(
          'Session Ended',
          style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 16),
        const Text(
          'Your partner didn\'t join in time or the session was terminated.\nYour session continues individually.',
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 32),
        AnimatedButton(
          label: 'Return to Chat',
          onTap: () => Navigator.pop(context),
        ),
      ],
    );
  }
}
