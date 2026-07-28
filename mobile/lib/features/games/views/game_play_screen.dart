import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/theme/app_colors.dart';
import '../games_models.dart';
import '../games_viewmodel.dart';

/// Play a Know Your Partner pack: answer about yourself and guess your partner
/// for each question, then see the reveal once both of you have finished.
class GamePlayScreen extends StatefulWidget {
  final String gameKey;
  const GamePlayScreen({super.key, required this.gameKey});

  @override
  State<GamePlayScreen> createState() => _GamePlayScreenState();
}

class _GamePlayScreenState extends State<GamePlayScreen> {
  final Map<String, int> _self = {};
  final Map<String, int> _guess = {};
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance
        .addPostFrameCallback((_) => context.read<GamesViewModel>().loadGame(widget.gameKey));
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<GamesViewModel>();
    final detail = vm.detail;
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: Text(detail?.title ?? 'Game',
            style: const TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: AppColors.creamWhite,
        elevation: 0,
      ),
      body: vm.isLoading || detail == null
          ? const Center(child: CircularProgressIndicator())
          : !detail.isScored
              ? _ConversationDeckView(detail: detail)
              : detail.reveal != null
                  ? _RevealView(detail: detail)
                  : detail.progress.iComplete
                      ? _waiting(detail)
                      : !detail.hasPartner
                          ? _noPartner(context)
                          : _playForm(context, detail),
    );
  }

  Widget _noPartner(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('💞', style: TextStyle(fontSize: 44)),
              const SizedBox(height: 16),
              const Text('This game is for two',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              const Text('Invite your partner to play together.',
                  textAlign: TextAlign.center, style: TextStyle(color: AppColors.softCharcoal)),
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: () => Navigator.of(context).pushNamed('/relationship/invite'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.warmCoral,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: const Text('Invite my partner', style: TextStyle(color: Colors.white)),
              ),
            ],
          ),
        ),
      );

  Widget _waiting(GameDetail detail) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('⏳', style: TextStyle(fontSize: 44)),
              const SizedBox(height: 16),
              const Text('All done on your side!',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              Text(
                'Waiting for ${detail.partnerName ?? 'your partner'} to play. '
                'You\'ll both see your results the moment they finish.',
                textAlign: TextAlign.center,
                style: const TextStyle(color: AppColors.softCharcoal),
              ),
            ],
          ),
        ),
      );

  Widget _playForm(BuildContext context, GameDetail detail) {
    final isAgreement = detail.gameType == 'this_or_that';
    // Seed any previously-saved answers once.
    for (final q in detail.questions) {
      if (q.myAnswer != null) _self.putIfAbsent(q.id, () => q.myAnswer!);
      if (q.myGuess != null) _guess.putIfAbsent(q.id, () => q.myGuess!);
    }
    // Agreement games (This or That) need only your own pick, no guess.
    final allAnswered = detail.questions.every((q) =>
        _self.containsKey(q.id) && (isAgreement || _guess.containsKey(q.id)));
    final partner = detail.partnerName ?? 'them';

    return Column(
      children: [
        if (isAgreement)
          const Padding(
            padding: EdgeInsets.fromLTRB(16, 16, 16, 0),
            child: Text('Pick your side — then see how in sync you are 💫',
                style: TextStyle(color: AppColors.softCharcoal)),
          ),
        Expanded(
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              for (var i = 0; i < detail.questions.length; i++)
                _questionCard(detail.questions[i], i + 1, partner, isAgreement),
              const SizedBox(height: 8),
            ],
          ),
        ),
        SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            child: SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: (allAnswered && !_submitting) ? () => _submit(context, detail) : null,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.warmCoral,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                ),
                child: _submitting
                    ? const SizedBox(
                        height: 20, width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : Text(allAnswered ? 'Submit answers' : 'Answer every question',
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _questionCard(GameQuestionView q, int number, String partner, bool isAgreement) {
    return Card(
      elevation: 0,
      color: Colors.white,
      margin: const EdgeInsets.only(bottom: 14),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(color: AppColors.softCharcoal.withValues(alpha: 0.05)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('$number. ${q.prompt}',
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            _row(isAgreement ? 'Your pick' : 'Your answer', q, _self, AppColors.warmCoral),
            if (!isAgreement) ...[
              const SizedBox(height: 10),
              _row('What would $partner say?', q, _guess, AppColors.calmTeal),
            ],
          ],
        ),
      ),
    );
  }

  Widget _row(String label, GameQuestionView q, Map<String, int> store, Color accent) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label,
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: accent)),
        const SizedBox(height: 6),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (var i = 0; i < q.options.length; i++)
              ChoiceChip(
                label: Text(q.options[i]),
                selected: store[q.id] == i,
                selectedColor: accent.withValues(alpha: 0.2),
                onSelected: (_) => setState(() => store[q.id] = i),
              ),
          ],
        ),
      ],
    );
  }

  Future<void> _submit(BuildContext context, GameDetail detail) async {
    setState(() => _submitting = true);
    final isAgreement = detail.gameType == 'this_or_that';
    final answers = <String, ({int self, int? guess})>{
      for (final q in detail.questions)
        q.id: (self: _self[q.id]!, guess: isAgreement ? null : _guess[q.id]!),
    };
    final vm = context.read<GamesViewModel>();
    await vm.submitAnswers(widget.gameKey, answers);
    if (mounted) setState(() => _submitting = false);
    // The screen rebuilds from vm.detail: reveal if both done, else waiting.
  }
}

class _RevealView extends StatelessWidget {
  final GameDetail detail;
  const _RevealView({required this.detail});

  @override
  Widget build(BuildContext context) {
    final reveal = detail.reveal!;
    final partner = detail.partnerName ?? 'Partner';
    if (reveal.isAgreement) return _agreementView(reveal, partner);
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: AppColors.goldGradient,
            borderRadius: BorderRadius.circular(20),
          ),
          child: Column(
            children: [
              const Text('How well do you know each other? 💛',
                  style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _score('You guessed', reveal.myScore, reveal.outOf),
                  _score('$partner guessed', reveal.partnerScore, reveal.outOf),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Text(
          reveal.questions.any((q) => q.surprise)
              ? 'A few surprises to talk about 👇'
              : 'You two really get each other 👇',
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        for (final item in reveal.questions) _revealCard(item, partner),
      ],
    );
  }

  Widget _score(String label, int value, int outOf) => Column(
        children: [
          Text('$value/$outOf',
              style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold)),
          Text(label, style: const TextStyle(color: Colors.white, fontSize: 12)),
        ],
      );

  Widget _revealCard(RevealItem item, String partner) {
    final hit = item.iGuessedThem;
    return Card(
      elevation: 0,
      color: Colors.white,
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(
          color: (hit ? AppColors.calmTeal : AppColors.warmCoral).withValues(alpha: 0.25),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(item.prompt,
                      style: const TextStyle(fontWeight: FontWeight.bold)),
                ),
                Icon(hit ? Icons.check_circle : Icons.chat_bubble_outline,
                    color: hit ? AppColors.calmTeal : AppColors.warmCoral, size: 20),
              ],
            ),
            const SizedBox(height: 10),
            _line('$partner actually chose', item.label(item.partnerAnswer), AppColors.calmTeal),
            _line('You guessed', item.label(item.myGuess), AppColors.warmCoral),
            if (item.surprise) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.warmCoral.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text('Worth a chat 💬',
                    style: TextStyle(fontSize: 12, color: AppColors.warmCoral)),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _line(String label, String value, Color accent) => Padding(
        padding: const EdgeInsets.only(bottom: 4),
        child: RichText(
          text: TextSpan(
            style: const TextStyle(color: AppColors.softCharcoal, fontSize: 14),
            children: [
              TextSpan(text: '$label: ', style: TextStyle(color: accent, fontWeight: FontWeight.w600)),
              TextSpan(text: value),
            ],
          ),
        ),
      );

  // ── Agreement reveal (This or That) ────────────────────────────────────

  Widget _agreementView(GameReveal reveal, String partner) {
    final pct = reveal.outOf == 0 ? 0 : (reveal.agreeCount * 100 / reveal.outOf).round();
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            gradient: AppColors.goldGradient,
            borderRadius: BorderRadius.circular(20),
          ),
          child: Column(
            children: [
              const Text('How in sync are you? 💫',
                  style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
              const SizedBox(height: 12),
              Text('$pct%',
                  style: const TextStyle(color: Colors.white, fontSize: 40, fontWeight: FontWeight.bold)),
              Text('${reveal.agreeCount} of ${reveal.outOf} matched',
                  style: const TextStyle(color: Colors.white, fontSize: 13)),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Text(
          reveal.agreeCount == reveal.outOf
              ? 'Total sync — you two are on the same page 💛'
              : 'Where you differ is worth a chat 👇',
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        for (final item in reveal.questions) _agreementCard(item, partner),
      ],
    );
  }

  Widget _agreementCard(RevealItem item, String partner) {
    final matched = item.matched;
    final accent = matched ? AppColors.calmTeal : AppColors.warmCoral;
    return Card(
      elevation: 0,
      color: Colors.white,
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: accent.withValues(alpha: 0.25)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(item.prompt,
                      style: const TextStyle(fontWeight: FontWeight.bold)),
                ),
                Icon(matched ? Icons.favorite : Icons.compare_arrows,
                    color: accent, size: 20),
              ],
            ),
            const SizedBox(height: 10),
            _line('You picked', item.label(item.myAnswer), AppColors.warmCoral),
            _line('$partner picked', item.label(item.partnerAnswer), AppColors.calmTeal),
            if (!matched) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.warmCoral.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text('Different takes 💬',
                    style: TextStyle(fontSize: 12, color: AppColors.warmCoral)),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Conversation Deck: swipe through open prompts to discuss together. No
/// scoring, no guessing — just a shared cue to talk.
class _ConversationDeckView extends StatefulWidget {
  final GameDetail detail;
  const _ConversationDeckView({required this.detail});

  @override
  State<_ConversationDeckView> createState() => _ConversationDeckViewState();
}

class _ConversationDeckViewState extends State<_ConversationDeckView> {
  final _controller = PageController();
  int _index = 0;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final questions = widget.detail.questions;
    if (questions.isEmpty) {
      return const Center(child: Text('No prompts yet.'));
    }
    return Column(
      children: [
        const Padding(
          padding: EdgeInsets.fromLTRB(16, 16, 16, 0),
          child: Text('Take turns answering — no scores, just talk 💬',
              style: TextStyle(color: AppColors.softCharcoal)),
        ),
        Expanded(
          child: PageView.builder(
            controller: _controller,
            itemCount: questions.length,
            onPageChanged: (i) => setState(() => _index = i),
            itemBuilder: (_, i) => Padding(
              padding: const EdgeInsets.all(24),
              child: Container(
                alignment: Alignment.center,
                padding: const EdgeInsets.all(28),
                decoration: BoxDecoration(
                  gradient: AppColors.goldGradient,
                  borderRadius: BorderRadius.circular(24),
                ),
                child: Text(
                  questions[i].prompt,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                      color: Colors.white, fontSize: 22, height: 1.35, fontWeight: FontWeight.w600),
                ),
              ),
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('${_index + 1} / ${questions.length}',
                  style: const TextStyle(color: AppColors.softCharcoal)),
              ElevatedButton(
                onPressed: _index < questions.length - 1
                    ? () => _controller.nextPage(
                          duration: const Duration(milliseconds: 250),
                          curve: Curves.easeOut,
                        )
                    : () => Navigator.of(context).pop(),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.warmCoral,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: Text(_index < questions.length - 1 ? 'Next' : 'Done',
                    style: const TextStyle(color: Colors.white)),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
