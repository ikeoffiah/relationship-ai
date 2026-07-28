import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/theme/app_colors.dart';
import '../games_models.dart';
import '../games_viewmodel.dart';
import 'game_play_screen.dart';

/// The games hub: a list of playable packs with the couple's progress on each.
class GamesListScreen extends StatefulWidget {
  const GamesListScreen({super.key});

  @override
  State<GamesListScreen> createState() => _GamesListScreenState();
}

class _GamesListScreenState extends State<GamesListScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance
        .addPostFrameCallback((_) => context.read<GamesViewModel>().loadGames());
  }

  static const _categoryEmoji = {
    'relationship': '💞',
    'fun': '🎉',
    'spiritual': '🙏',
    'financial': '💰',
    'spicy': '🌶️',
  };

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<GamesViewModel>();
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Games', style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: AppColors.creamWhite,
        elevation: 0,
        actions: [
          IconButton(
            tooltip: 'Spicy games',
            icon: const Text('🌶️', style: TextStyle(fontSize: 18)),
            onPressed: () => _openSpicySheet(context),
          ),
        ],
      ),
      body: vm.isLoading && vm.games.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : vm.games.isEmpty
              ? _empty(vm.error)
              : RefreshIndicator(
                  onRefresh: () => vm.loadGames(),
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      const Text(
                        'Play together — answer about yourself, then guess your partner.',
                        style: TextStyle(color: AppColors.softCharcoal),
                      ),
                      const SizedBox(height: 16),
                      // Two Truths & a Lie isn't a fixed-catalog pack — it's its
                      // own authored-content flow, so it gets a dedicated entry.
                      _SpecialGameCard(
                        emoji: '🕵️',
                        title: 'Two Truths & a Lie',
                        subtitle: 'Write two truths and a lie — can they spot it?',
                        onTap: () => Navigator.of(context).pushNamed('/engagement/two-truths'),
                      ),
                      const SizedBox(height: 12),
                      for (final g in vm.games) ...[
                        _GameCard(game: g, emoji: _categoryEmoji[g.category] ?? '🎮'),
                        const SizedBox(height: 12),
                      ],
                    ],
                  ),
                ),
    );
  }

  void _openSpicySheet(BuildContext context) {
    final vm = context.read<GamesViewModel>();
    vm.loadSpicyConsent();
    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.creamWhite,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (sheetCtx) => Consumer<GamesViewModel>(
        builder: (_, m, _) {
          final c = m.spicyConsent;
          return Padding(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(children: [
                  Text('🌶️ ', style: TextStyle(fontSize: 20)),
                  Text('Spicy games',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                ]),
                const SizedBox(height: 8),
                const Text(
                  'Both of you turn these on. Either of you can turn them off, anytime.',
                  style: TextStyle(color: AppColors.softCharcoal),
                ),
                const SizedBox(height: 16),
                if (c == null)
                  const Center(child: Padding(
                    padding: EdgeInsets.all(12), child: CircularProgressIndicator()))
                else if (!c.bothAgeVerified)
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: AppColors.goldMedium.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Text(
                      'Both partners need to verify their age first (Settings → Verify age).',
                      style: TextStyle(color: AppColors.softCharcoal),
                    ),
                  )
                else ...[
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    activeThumbColor: AppColors.warmCoral,
                    title: const Text('Turn these on for me'),
                    value: c.you,
                    onChanged: (v) => m.toggleSpicy(v),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    c.unlocked
                        ? 'Done — these are in your list now.'
                        : c.partner
                            ? "They're in. Turn it on and these appear."
                            : 'Waiting for them to turn it on too.',
                    style: TextStyle(
                        color: c.unlocked ? AppColors.warmCoral : AppColors.softCharcoal,
                        fontWeight: FontWeight.w600),
                  ),
                ],
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _empty(String? error) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('🎮', style: TextStyle(fontSize: 44)),
              const SizedBox(height: 16),
              Text(
                error ?? 'No games available yet — check back soon.',
                textAlign: TextAlign.center,
                style: const TextStyle(color: AppColors.softCharcoal),
              ),
            ],
          ),
        ),
      );
}

class _GameCard extends StatelessWidget {
  final GameSummary game;
  final String emoji;
  const _GameCard({required this.game, required this.emoji});

  ({String label, Color color}) get _status {
    if (game.revealed) return (label: 'Results ready 🎉', color: AppColors.warmCoral);
    if (game.iComplete) return (label: 'Waiting for partner', color: AppColors.calmTeal);
    if (game.partnerComplete) return (label: 'Your partner played — your turn!', color: AppColors.goldMedium);
    return (label: '${game.questionCount} questions', color: AppColors.softCharcoal);
  }

  @override
  Widget build(BuildContext context) {
    final s = _status;
    return Card(
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(color: AppColors.softCharcoal.withValues(alpha: 0.05)),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => GamePlayScreen(gameKey: game.key)),
        ),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Row(
            children: [
              Text(emoji, style: const TextStyle(fontSize: 30)),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(game.title,
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    Text(game.description,
                        style: TextStyle(
                            color: AppColors.softCharcoal.withValues(alpha: 0.7), fontSize: 13)),
                    const SizedBox(height: 8),
                    Text(s.label,
                        style: TextStyle(
                            color: s.color, fontSize: 12, fontWeight: FontWeight.w600)),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: AppColors.softCharcoal),
            ],
          ),
        ),
      ),
    );
  }
}

/// A dedicated entry for a game that isn't a fixed-catalog [GamePack]
/// (e.g. Two Truths & a Lie), navigating by route rather than pack key.
class _SpecialGameCard extends StatelessWidget {
  final String emoji;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  const _SpecialGameCard({
    required this.emoji,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(color: AppColors.softCharcoal.withValues(alpha: 0.05)),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Text(emoji, style: const TextStyle(fontSize: 28)),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title,
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    Text(subtitle,
                        style: TextStyle(
                            color: AppColors.softCharcoal.withValues(alpha: 0.7), fontSize: 13)),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: AppColors.softCharcoal),
            ],
          ),
        ),
      ),
    );
  }
}
