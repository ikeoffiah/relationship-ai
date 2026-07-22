import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/features/relay/relay_compose_screen.dart';
import 'package:mobile/features/relay/relay_models.dart';
import 'package:mobile/features/relay/relay_viewmodel.dart';

/// Relays waiting for this user. For each, the recipient reads the original or
/// the AI-assisted version and takes delivery.
class RelayInboxScreen extends StatefulWidget {
  const RelayInboxScreen({super.key});

  @override
  State<RelayInboxScreen> createState() => _RelayInboxScreenState();
}

class _RelayInboxScreenState extends State<RelayInboxScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  void _load() {
    final userId = context.read<AuthViewModel>().user?.id;
    if (userId != null) {
      context.read<RelayViewModel>().loadPending(userId);
    }
  }

  Future<void> _deliver(RelayDetail relay, String version) async {
    final ok = await context.read<RelayViewModel>().deliver(relay.relayId, version);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(ok ? 'Message opened.' : 'Could not open message.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<RelayViewModel>();
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Relay Inbox',
            style: TextStyle(color: AppColors.softCharcoal)),
        backgroundColor: Colors.transparent,
        elevation: 0,
        iconTheme: const IconThemeData(color: AppColors.softCharcoal),
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: AppColors.warmCoral,
        onPressed: () => Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => const RelayComposeScreen()),
        ),
        icon: const Icon(Icons.edit, color: Colors.white),
        label: const Text('Compose', style: TextStyle(color: Colors.white)),
      ),
      body: RefreshIndicator(
        onRefresh: () async => _load(),
        child: _buildBody(vm),
      ),
    );
  }

  Widget _buildBody(RelayViewModel vm) {
    if (vm.isLoading && vm.pending.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (vm.pending.isEmpty) {
      return ListView(
        children: const [
          SizedBox(height: 120),
          Icon(Icons.mail_outline, size: 56, color: AppColors.warmCoral),
          SizedBox(height: 16),
          Center(
            child: Text('No messages waiting',
                style: TextStyle(color: AppColors.softCharcoal)),
          ),
        ],
      );
    }
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: vm.pending.length,
      itemBuilder: (context, i) => _RelayCard(
        relay: vm.pending[i],
        onDeliver: _deliver,
      ),
    );
  }
}

class _RelayCard extends StatelessWidget {
  const _RelayCard({required this.relay, required this.onDeliver});

  final RelayDetail relay;
  final Future<void> Function(RelayDetail, String) onDeliver;

  @override
  Widget build(BuildContext context) {
    final hasTranslation = (relay.translatedContent ?? '').isNotEmpty;
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Your partner sent you a message',
                style: TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 12),
            if (hasTranslation) ...[
              const Text('AI-assisted version',
                  style: TextStyle(fontSize: 12, color: AppColors.calmTeal)),
              Text(relay.translatedContent!),
              const SizedBox(height: 8),
            ],
            Row(
              children: [
                if (hasTranslation)
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () =>
                          onDeliver(relay, RelayVersion.aiTranslated),
                      child: const Text('Read AI version'),
                    ),
                  ),
                if (hasTranslation) const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.warmCoral),
                    onPressed: () => onDeliver(relay, RelayVersion.original),
                    child: const Text('Read original',
                        style: TextStyle(color: Colors.white)),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
