import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/theme/app_colors.dart';
import '../focus_models.dart';
import '../focus_viewmodel.dart';

/// Consensual Focus Mode: propose some undistracted time together, accept your
/// partner's invite, watch a shared countdown, and end it whenever either of you
/// wants — no locks, no monitoring.
class FocusScreen extends StatefulWidget {
  const FocusScreen({super.key});

  @override
  State<FocusScreen> createState() => _FocusScreenState();
}

class _FocusScreenState extends State<FocusScreen> {
  Timer? _tick;
  int _selectedMinutes = 20;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => context.read<FocusViewModel>().load());
    // A 1s tick just to refresh the countdown display; state sync is polled by
    // the viewmodel.
    _tick = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _tick?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<FocusViewModel>();
    final s = vm.session;
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Focus together', style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: AppColors.creamWhite,
        elevation: 0,
      ),
      body: vm.isLoading && s == null
          ? const Center(child: CircularProgressIndicator())
          : Padding(
              padding: const EdgeInsets.all(24),
              child: s == null
                  ? _propose(context, vm)
                  : s.isActive
                      ? _active(context, vm, s)
                      : s.isProposed
                          ? (s.iInitiated ? _waiting(context, vm, s) : _invite(context, vm, s))
                          : _propose(context, vm),
            ),
    );
  }

  // ── Propose ──────────────────────────────────────────────────────────
  Widget _propose(BuildContext context, FocusViewModel vm) {
    const options = [15, 20, 30, 45];
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Text('🌿', style: TextStyle(fontSize: 56)),
        const SizedBox(height: 16),
        const Text('Some undistracted time',
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        Text(
          'Invite your partner to put phones down and just be together. '
          'Either of you can end it anytime.',
          textAlign: TextAlign.center,
          style: TextStyle(color: AppColors.softCharcoal.withValues(alpha: 0.7)),
        ),
        const SizedBox(height: 24),
        Wrap(
          spacing: 10,
          children: [
            for (final m in options)
              ChoiceChip(
                label: Text('$m min'),
                selected: _selectedMinutes == m,
                selectedColor: AppColors.warmCoral.withValues(alpha: 0.2),
                onSelected: (_) => setState(() => _selectedMinutes = m),
              ),
          ],
        ),
        const SizedBox(height: 24),
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.warmCoral,
              padding: const EdgeInsets.symmetric(vertical: 16),
            ),
            onPressed: vm.busy ? null : () => _run(context, () => vm.propose(_selectedMinutes)),
            child: vm.busy ? _spinner() : const Text('Invite to focus'),
          ),
        ),
        if (vm.error != null) _err(vm.error!),
      ],
    );
  }

  // ── Waiting for partner (I proposed) ─────────────────────────────────
  Widget _waiting(BuildContext context, FocusViewModel vm, FocusSession s) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Text('⏳', style: TextStyle(fontSize: 56)),
        const SizedBox(height: 16),
        Text('Invite sent — ${s.durationMinutes} min',
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        Text('Waiting for your partner to accept.',
            textAlign: TextAlign.center,
            style: TextStyle(color: AppColors.softCharcoal.withValues(alpha: 0.7))),
        const SizedBox(height: 24),
        TextButton(
          onPressed: vm.busy ? null : () => _run(context, () => vm.end()),
          child: const Text('Cancel invite'),
        ),
      ],
    );
  }

  // ── Partner invited me ───────────────────────────────────────────────
  Widget _invite(BuildContext context, FocusViewModel vm, FocusSession s) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Text('🌿', style: TextStyle(fontSize: 56)),
        const SizedBox(height: 16),
        Text('Focus together for ${s.durationMinutes} min?',
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            textAlign: TextAlign.center),
        const SizedBox(height: 8),
        Text('Your partner would love some undistracted time with you.',
            textAlign: TextAlign.center,
            style: TextStyle(color: AppColors.softCharcoal.withValues(alpha: 0.7))),
        const SizedBox(height: 28),
        Row(
          children: [
            Expanded(
              child: OutlinedButton(
                onPressed: vm.busy ? null : () => _run(context, () => vm.decline()),
                child: const Text('Maybe later'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: FilledButton(
                style: FilledButton.styleFrom(backgroundColor: AppColors.warmCoral),
                onPressed: vm.busy ? null : () => _run(context, () => vm.accept()),
                child: vm.busy ? _spinner() : const Text('Let\'s do it'),
              ),
            ),
          ],
        ),
      ],
    );
  }

  // ── Active countdown ─────────────────────────────────────────────────
  Widget _active(BuildContext context, FocusViewModel vm, FocusSession s) {
    final remaining = s.liveRemaining(DateTime.now());
    final mm = (remaining ~/ 60).toString().padLeft(2, '0');
    final ss = (remaining % 60).toString().padLeft(2, '0');
    final done = remaining <= 0;
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text(done ? '💛' : '🌿', style: const TextStyle(fontSize: 56)),
        const SizedBox(height: 20),
        Text(done ? 'Time together, well spent' : 'Phones down — be here',
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 20),
        Text(done ? 'Done' : '$mm:$ss',
            style: const TextStyle(fontSize: 56, fontWeight: FontWeight.bold, color: AppColors.warmCoral)),
        const SizedBox(height: 28),
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: done ? AppColors.calmTeal : AppColors.warmCoral,
              padding: const EdgeInsets.symmetric(vertical: 16),
            ),
            onPressed: vm.busy ? null : () => _run(context, () => vm.end()),
            child: vm.busy ? _spinner() : Text(done ? 'Finish' : 'End now'),
          ),
        ),
        const SizedBox(height: 8),
        Text('Either of you can end this anytime.',
            style: TextStyle(fontSize: 12, color: AppColors.softCharcoal.withValues(alpha: 0.6))),
      ],
    );
  }

  Future<void> _run(BuildContext context, Future<bool> Function() action) async {
    final vm = context.read<FocusViewModel>();
    final messenger = ScaffoldMessenger.of(context);
    final ok = await action();
    if (!ok && mounted) {
      messenger.showSnackBar(SnackBar(content: Text(vm.error ?? 'Something went wrong.')));
    }
  }

  Widget _spinner() => const SizedBox(
      height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white));

  Widget _err(String message) => Padding(
        padding: const EdgeInsets.only(top: 12),
        child: Text(message,
            textAlign: TextAlign.center,
            style: const TextStyle(color: AppColors.warmCoral, fontSize: 13)),
      );
}
