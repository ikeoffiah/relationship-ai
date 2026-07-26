import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/theme/app_colors.dart';
import '../engagement_viewmodel.dart';
import '../engagement_models.dart';

/// The daily-ritual hub: the one place a couple opens each day. Surfaces the
/// streak/points header, today's checklist, the daily question (with two-sided
/// reveal), a 10-second check-in, and the micro-action of the day.
class DailyRitualScreen extends StatefulWidget {
  const DailyRitualScreen({super.key});

  @override
  State<DailyRitualScreen> createState() => _DailyRitualScreenState();
}

class _DailyRitualScreenState extends State<DailyRitualScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback(
      (_) => context.read<EngagementViewModel>().loadRitual(),
    );
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<EngagementViewModel>();
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Today', style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: AppColors.creamWhite,
        elevation: 0,
        actions: [
          IconButton(
            onPressed: () => Navigator.of(context).pushNamed('/engagement/games'),
            icon: const Icon(Icons.videogame_asset_outlined, color: AppColors.warmCoral),
            tooltip: 'Games',
          ),
          IconButton(
            onPressed: () => Navigator.of(context).pushNamed('/engagement/faith'),
            icon: const Icon(Icons.self_improvement_outlined, color: AppColors.calmTeal),
            tooltip: 'Faith',
          ),
          TextButton.icon(
            onPressed: () => Navigator.of(context).pushNamed('/engagement/goals'),
            icon: const Icon(Icons.flag_outlined, color: AppColors.calmTeal),
            label: const Text('Goals', style: TextStyle(color: AppColors.calmTeal)),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => vm.loadRitual(),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _StreakHeader(summary: vm.summary),
            const SizedBox(height: 16),
            if (!vm.summary.hasPartner) _noPartnerBanner(context),
            if (vm.error != null) _errorBanner(vm.error!),
            _DailyQuestionCard(question: vm.question, loading: vm.isLoading),
            const SizedBox(height: 16),
            _CheckInCard(alreadyDone: vm.summary.didCheckIn),
            const SizedBox(height: 16),
            _MicroActionCard(action: vm.microAction),
            const SizedBox(height: 16),
            _GratitudeCard(),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Widget _noPartnerBanner(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 16),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.goldMedium.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(
          children: [
            const Icon(Icons.favorite_border, color: AppColors.warmCoral),
            const SizedBox(width: 12),
            const Expanded(
              child: Text(
                'You\'re all set solo. Invite your partner to compare answers and share your goals.',
                style: TextStyle(color: AppColors.softCharcoal),
              ),
            ),
            TextButton(
              onPressed: () => Navigator.of(context).pushNamed('/relationship/invite'),
              child: const Text('Invite'),
            ),
          ],
        ),
      );

  Widget _errorBanner(String message) => Container(
        margin: const EdgeInsets.only(bottom: 16),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AppColors.error.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(message, style: const TextStyle(color: AppColors.error)),
      );
}

// ── Streak / points header ────────────────────────────────────────────

class _StreakHeader extends StatelessWidget {
  final EngagementSummary summary;
  const _StreakHeader({required this.summary});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: AppColors.goldGradient,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _stat('🔥', '${summary.currentStreak}', 'day streak'),
          Container(width: 1, height: 40, color: Colors.white.withValues(alpha: 0.4)),
          _stat('⭐', '${summary.pointsBalance}', 'points'),
          Container(width: 1, height: 40, color: Colors.white.withValues(alpha: 0.4)),
          _stat('🏆', '${summary.longestStreak}', 'best streak'),
        ],
      ),
    );
  }

  Widget _stat(String emoji, String value, String label) => Column(
        children: [
          Text(emoji, style: const TextStyle(fontSize: 22)),
          const SizedBox(height: 4),
          Text(value,
              style: const TextStyle(
                  fontSize: 22, fontWeight: FontWeight.bold, color: Colors.white)),
          Text(label, style: const TextStyle(color: Colors.white, fontSize: 12)),
        ],
      );
}

// ── Reusable card shell ───────────────────────────────────────────────

class _RitualCard extends StatelessWidget {
  final Widget child;
  const _RitualCard({required this.child});

  @override
  Widget build(BuildContext context) => Card(
        elevation: 0,
        color: Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(color: AppColors.softCharcoal.withValues(alpha: 0.05)),
        ),
        child: Padding(padding: const EdgeInsets.all(20), child: child),
      );
}

// ── Daily question ────────────────────────────────────────────────────

class _DailyQuestionCard extends StatelessWidget {
  final DailyQuestionState question;
  final bool loading;
  const _DailyQuestionCard({required this.question, required this.loading});

  @override
  Widget build(BuildContext context) {
    if (!question.hasQuestion) {
      return _RitualCard(
        child: Text(loading ? 'Loading today\'s question…' : 'No question today.',
            style: const TextStyle(color: Colors.grey)),
      );
    }
    return _RitualCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(children: [
            Icon(Icons.chat_bubble_outline_rounded, color: AppColors.warmCoral),
            SizedBox(width: 8),
            Text('💬 Daily question',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          ]),
          const SizedBox(height: 12),
          Text(question.promptText!,
              style: const TextStyle(fontSize: 17, height: 1.3)),
          const SizedBox(height: 16),
          if (question.revealed)
            _revealed(context)
          else if (question.iAnswered)
            _waiting()
          else
            _answerButton(context),
        ],
      ),
    );
  }

  Widget _answerButton(BuildContext context) => SizedBox(
        width: double.infinity,
        child: ElevatedButton(
          onPressed: () => _openAnswerSheet(context),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.warmCoral,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
          child: const Text('Answer', style: TextStyle(color: Colors.white)),
        ),
      );

  Widget _waiting() => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AppColors.calmTeal.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(children: [
          const Icon(Icons.lock_clock, color: AppColors.calmTeal, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              question.hasPartner
                  ? 'Answered! Your answers unlock once ${question.partnerName ?? 'your partner'} answers too.'
                  : 'Answered! Invite your partner to compare answers.',
              style: const TextStyle(color: AppColors.softCharcoal),
            ),
          ),
        ]),
      );

  Widget _revealed(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _answerBubble('You', question.myAnswer ?? '', AppColors.warmCoral),
          const SizedBox(height: 8),
          _answerBubble(question.partnerName ?? 'Partner', question.partnerAnswer ?? '',
              AppColors.calmTeal),
        ],
      );

  Widget _answerBubble(String who, String text, Color accent) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: accent.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(12),
          border: Border(left: BorderSide(color: accent, width: 3)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(who,
                style: TextStyle(fontWeight: FontWeight.bold, color: accent, fontSize: 12)),
            const SizedBox(height: 4),
            Text(text),
          ],
        ),
      );

  void _openAnswerSheet(BuildContext context) {
    final controller = TextEditingController();
    final vm = context.read<EngagementViewModel>();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.creamWhite,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (sheetCtx) => Padding(
        padding: EdgeInsets.only(
          left: 20,
          right: 20,
          top: 20,
          bottom: MediaQuery.of(sheetCtx).viewInsets.bottom + 20,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(question.promptText!,
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              maxLines: 4,
              autofocus: true,
              decoration: InputDecoration(
                hintText: 'Write your answer…',
                filled: true,
                fillColor: Colors.white,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.warmCoral,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onPressed: () async {
                  final text = controller.text.trim();
                  if (text.isEmpty) return;
                  final ok = await vm.answerQuestion(text);
                  if (sheetCtx.mounted && ok) Navigator.of(sheetCtx).pop();
                },
                child: const Text('Send answer', style: TextStyle(color: Colors.white)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Daily check-in ────────────────────────────────────────────────────

class _CheckInCard extends StatelessWidget {
  final bool alreadyDone;
  const _CheckInCard({required this.alreadyDone});

  static const _emojis = ['😞', '😕', '😐', '🙂', '😍'];

  @override
  Widget build(BuildContext context) {
    return _RitualCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(children: [
            Icon(Icons.favorite_outline, color: AppColors.calmTeal),
            SizedBox(width: 8),
            Text('How connected do you feel today?',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          ]),
          const SizedBox(height: 16),
          if (alreadyDone)
            const Row(children: [
              Icon(Icons.check_circle, color: AppColors.calmTeal, size: 18),
              SizedBox(width: 8),
              Text('Checked in for today ✓', style: TextStyle(color: AppColors.softCharcoal)),
            ])
          else
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                for (var i = 0; i < 5; i++)
                  InkWell(
                    borderRadius: BorderRadius.circular(24),
                    onTap: () => _submit(context, i + 1),
                    child: Padding(
                      padding: const EdgeInsets.all(4),
                      child: Text(_emojis[i], style: const TextStyle(fontSize: 30)),
                    ),
                  ),
              ],
            ),
        ],
      ),
    );
  }

  Future<void> _submit(BuildContext context, int score) async {
    final vm = context.read<EngagementViewModel>();
    final ok = await vm.checkIn(score: score);
    if (context.mounted && ok) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Checked in — nice 💛')),
      );
    }
  }
}

// ── Micro-action of the day ───────────────────────────────────────────

class _MicroActionCard extends StatelessWidget {
  final MicroActionState action;
  const _MicroActionCard({required this.action});

  @override
  Widget build(BuildContext context) {
    if (!action.hasAction) return const SizedBox.shrink();
    return _RitualCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(children: [
            Icon(Icons.bolt_outlined, color: AppColors.goldMedium),
            SizedBox(width: 8),
            Text('One small thing',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          ]),
          const SizedBox(height: 12),
          Text(action.text!, style: const TextStyle(fontSize: 15, height: 1.3)),
          const SizedBox(height: 16),
          if (action.completed)
            const Row(children: [
              Icon(Icons.check_circle, color: AppColors.goldMedium, size: 18),
              SizedBox(width: 8),
              Text('Done today ✓', style: TextStyle(color: AppColors.softCharcoal)),
            ])
          else
            SizedBox(
              width: double.infinity,
              child: OutlinedButton(
                onPressed: () => context.read<EngagementViewModel>().completeMicroAction(),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: AppColors.goldMedium),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: const Text('Mark done', style: TextStyle(color: AppColors.softCharcoal)),
              ),
            ),
        ],
      ),
    );
  }
}

// ── Gratitude / repair quick-capture ──────────────────────────────────

class _GratitudeCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return _RitualCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Capture a moment',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => _capture(context, 'gratitude'),
                icon: const Text('🙏'),
                label: const Text('Gratitude'),
                style: OutlinedButton.styleFrom(
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => _capture(context, 'repair'),
                icon: const Text('🤝'),
                label: const Text('Repair'),
                style: OutlinedButton.styleFrom(
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ),
          ]),
        ],
      ),
    );
  }

  void _capture(BuildContext context, String kind) {
    final controller = TextEditingController();
    final vm = context.read<EngagementViewModel>();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.creamWhite,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (sheetCtx) => Padding(
        padding: EdgeInsets.only(
          left: 20,
          right: 20,
          top: 20,
          bottom: MediaQuery.of(sheetCtx).viewInsets.bottom + 20,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(kind == 'repair' ? 'Log a repair moment' : 'What are you grateful for?',
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              maxLines: 3,
              autofocus: true,
              decoration: InputDecoration(
                hintText: kind == 'repair'
                    ? 'How did you reconnect after a rough patch?'
                    : 'Something your partner did…',
                filled: true,
                fillColor: Colors.white,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.calmTeal,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onPressed: () async {
                  final text = controller.text.trim();
                  if (text.isEmpty) return;
                  final ok = await vm.logGratitude(kind: kind, text: text);
                  if (sheetCtx.mounted && ok) Navigator.of(sheetCtx).pop();
                },
                child: const Text('Save', style: TextStyle(color: Colors.white)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
