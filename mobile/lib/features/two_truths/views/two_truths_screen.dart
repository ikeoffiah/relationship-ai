import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/app_card.dart';
import '../two_truths_models.dart';
import '../two_truths_viewmodel.dart';

/// Two Truths & a Lie: author three statements (two true, one lie), guess your
/// partner's lie, then see who caught whom.
class TwoTruthsScreen extends StatefulWidget {
  const TwoTruthsScreen({super.key});

  @override
  State<TwoTruthsScreen> createState() => _TwoTruthsScreenState();
}

class _TwoTruthsScreenState extends State<TwoTruthsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback(
      (_) => context.read<TwoTruthsViewModel>().load(),
    );
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<TwoTruthsViewModel>();
    final state = vm.state;
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Two Truths & a Lie',
            style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: AppColors.creamWhite,
        elevation: 0,
      ),
      body: vm.isLoading && state == null
          ? const Center(child: CircularProgressIndicator())
          : state == null
              ? _error(vm.error)
              : !state.hasPartner
                  ? _noPartner(context)
                  : _phase(context, state),
    );
  }

  Widget _error(String? msg) =>
      Center(child: Text(msg ?? 'Something went wrong.'));

  Widget _noPartner(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('🕵️', style: TextStyle(fontSize: 44)),
              const SizedBox(height: 16),
              const Text('This game is for two',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              const Text('Invite your partner to play together.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: AppColors.softCharcoal)),
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: () => Navigator.of(context).pushNamed('/relationship/invite'),
                style: ElevatedButton.styleFrom(backgroundColor: AppColors.warmCoral),
                child: const Text('Invite my partner',
                    style: TextStyle(color: Colors.white)),
              ),
            ],
          ),
        ),
      );

  Widget _phase(BuildContext context, TwoTruthsState state) {
    switch (state.phase) {
      case 'author':
        return _AuthorForm(state: state);
      case 'guess':
        return _GuessView(state: state);
      case 'reveal':
        return _RevealView(state: state);
      default:
        return _waiting(state);
    }
  }

  Widget _waiting(TwoTruthsState state) {
    final partner = state.partnerName ?? 'your partner';
    final msg = !state.partnerAuthored
        ? 'Waiting for $partner to write their three statements.'
        : 'You guessed! Waiting for $partner to guess yours.';
    return Center(
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
            Text(msg,
                textAlign: TextAlign.center,
                style: const TextStyle(color: AppColors.softCharcoal)),
          ],
        ),
      ),
    );
  }
}

class _AuthorForm extends StatefulWidget {
  final TwoTruthsState state;
  const _AuthorForm({required this.state});

  @override
  State<_AuthorForm> createState() => _AuthorFormState();
}

class _AuthorFormState extends State<_AuthorForm> {
  final _controllers = List.generate(3, (_) => TextEditingController());
  int? _lie;

  @override
  void dispose() {
    for (final c in _controllers) {
      c.dispose();
    }
    super.dispose();
  }

  bool get _ready =>
      _lie != null && _controllers.every((c) => c.text.trim().isNotEmpty);

  Future<void> _submit() async {
    final statements = _controllers.map((c) => c.text.trim()).toList();
    final vm = context.read<TwoTruthsViewModel>();
    final messenger = ScaffoldMessenger.of(context);
    final ok = await vm.author(statements, _lie!);
    if (!mounted) return;
    if (!ok) {
      messenger.showSnackBar(
        SnackBar(content: Text(vm.error ?? "Couldn't save, try again.")),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<TwoTruthsViewModel>();
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text('Write three statements about yourself — two true, one a lie. '
            'Then mark the lie.',
            style: TextStyle(color: AppColors.softCharcoal)),
        const SizedBox(height: 16),
        for (var i = 0; i < 3; i++) ...[
          _statementField(i),
          const SizedBox(height: 12),
        ],
        const SizedBox(height: 8),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton(
            onPressed: (_ready && !vm.submitting) ? _submit : null,
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.warmCoral,
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            ),
            child: vm.submitting
                ? const SizedBox(
                    height: 20, width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                : Text(_ready ? 'Submit' : 'Fill all three and mark the lie',
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
          ),
        ),
      ],
    );
  }

  Widget _statementField(int i) {
    final isLie = _lie == i;
    return AppCard(
      borderColor: (isLie ? AppColors.warmCoral : AppColors.softCharcoal.withValues(alpha: 0.08)),
      padding: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: _controllers[i],
              maxLength: 200,
              onChanged: (_) => setState(() {}),
              decoration: InputDecoration(
                hintText: 'Statement ${i + 1}',
                counterText: '',
                border: InputBorder.none,
              ),
            ),
            InkWell(
              onTap: () => setState(() => _lie = i),
              borderRadius: BorderRadius.circular(8),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 4),
                child: Row(
                  children: [
                    Icon(
                      isLie ? Icons.radio_button_checked : Icons.radio_button_unchecked,
                      size: 20,
                      color: isLie ? AppColors.warmCoral : AppColors.softCharcoal.withValues(alpha: 0.4),
                    ),
                    const SizedBox(width: 8),
                    Text('This one\'s the lie',
                        style: TextStyle(
                            color: isLie ? AppColors.warmCoral : AppColors.softCharcoal,
                            fontWeight: isLie ? FontWeight.bold : FontWeight.normal)),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _GuessView extends StatefulWidget {
  final TwoTruthsState state;
  const _GuessView({required this.state});

  @override
  State<_GuessView> createState() => _GuessViewState();
}

class _GuessViewState extends State<_GuessView> {
  int? _guess;

  Future<void> _submit() async {
    final vm = context.read<TwoTruthsViewModel>();
    await vm.guess(_guess!);
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<TwoTruthsViewModel>();
    final statements = widget.state.partnerStatements ?? const [];
    final partner = widget.state.partnerName ?? 'Your partner';
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('$partner wrote three statements. Which one is the lie? 🕵️',
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        const SizedBox(height: 16),
        for (var i = 0; i < statements.length; i++) ...[
          AppCard(
            color: _guess == i ? AppColors.warmCoral.withValues(alpha: 0.12) : Colors.white,
            borderColor: _guess == i ? AppColors.warmCoral : AppColors.softCharcoal.withValues(alpha: 0.08),
            padding: EdgeInsets.zero,
            child: ListTile(
              title: Text(statements[i]),
              leading: Icon(
                  _guess == i ? Icons.radio_button_checked : Icons.radio_button_unchecked,
                  color: AppColors.warmCoral),
              onTap: () => setState(() => _guess = i),
            ),
          ),
          const SizedBox(height: 12),
        ],
        const SizedBox(height: 8),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton(
            onPressed: (_guess != null && !vm.submitting) ? _submit : null,
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.warmCoral,
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            ),
            child: vm.submitting
                ? const SizedBox(
                    height: 20, width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                : const Text('Lock in my guess',
                    style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
          ),
        ),
      ],
    );
  }
}

class _RevealView extends StatelessWidget {
  final TwoTruthsState state;
  const _RevealView({required this.state});

  @override
  Widget build(BuildContext context) {
    final r = state.reveal!;
    final partner = state.partnerName ?? 'Partner';
    final myStatements = state.myStatements ?? const [];
    final partnerStatements = state.partnerStatements ?? const [];
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
              const Text('The results are in 🕵️',
                  style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
              const SizedBox(height: 8),
              Text(
                r.iCaughtThem
                    ? 'You spotted $partner\'s lie!'
                    : "$partner fooled you this time.",
                style: const TextStyle(color: Colors.white),
              ),
              Text(
                r.theyCaughtMe
                    ? '$partner spotted yours too.'
                    : 'But your lie got past them 😏',
                style: const TextStyle(color: Colors.white),
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),
        _block("$partner's statements", partnerStatements, r.partnerLieIndex,
            guess: r.partnerGuess),
        const SizedBox(height: 16),
        _block('Your statements', myStatements, r.myLieIndex),
        const SizedBox(height: 20),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton(
            onPressed: () => context.read<TwoTruthsViewModel>().reset(),
            child: const Text('Play again'),
          ),
        ),
      ],
    );
  }

  Widget _block(String title, List<String> statements, int lieIndex, {int? guess}) {
    return AppCard(
      padding: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 10),
            for (var i = 0; i < statements.length; i++)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      i == lieIndex ? Icons.close : Icons.check,
                      size: 18,
                      color: i == lieIndex ? AppColors.warmCoral : AppColors.calmTeal,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        statements[i],
                        style: TextStyle(
                          fontWeight: i == lieIndex ? FontWeight.bold : FontWeight.normal,
                        ),
                      ),
                    ),
                    if (guess != null && guess == i)
                      const Padding(
                        padding: EdgeInsets.only(left: 6),
                        child: Text('👈 your guess', style: TextStyle(fontSize: 12)),
                      ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}
