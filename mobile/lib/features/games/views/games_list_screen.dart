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
                      for (final g in vm.games) ...[
                        _GameCard(game: g, emoji: _categoryEmoji[g.category] ?? '🎮'),
                        const SizedBox(height: 12),
                      ],
                    ],
                  ),
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
