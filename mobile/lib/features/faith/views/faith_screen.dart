import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/theme/app_colors.dart';
import '../faith_models.dart';
import '../faith_viewmodel.dart';

/// The opt-in faith tab: today's reading, a private reflection, and a shared
/// checklist of daily spiritual practices. Solo-friendly — nothing here needs
/// a partner.
class FaithScreen extends StatefulWidget {
  const FaithScreen({super.key});

  @override
  State<FaithScreen> createState() => _FaithScreenState();
}

class _FaithScreenState extends State<FaithScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback(
      (_) => context.read<FaithViewModel>().loadToday(),
    );
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<FaithViewModel>();
    final today = vm.today;
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Faith', style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: AppColors.creamWhite,
        elevation: 0,
      ),
      body: RefreshIndicator(
        onRefresh: () => vm.loadToday(),
        child: vm.isLoading && today == null
            ? const Center(child: CircularProgressIndicator())
            : ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  if (vm.error != null) _errorBanner(vm.error!),
                  if (today?.reading != null) ...[
                    _ReadingCard(reading: today!.reading!),
                    const SizedBox(height: 16),
                    _ReflectionCard(reflected: today.reflected),
                    const SizedBox(height: 16),
                  ],
                  _PracticesCard(practices: today?.practices ?? const []),
                  const SizedBox(height: 24),
                  Center(
                    child: Text(
                      'A gentle daily rhythm — take what serves you, leave the rest.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: AppColors.softCharcoal.withValues(alpha: 0.6)),
                    ),
                  ),
                ],
              ),
      ),
    );
  }

  Widget _errorBanner(String message) => Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AppColors.softRose.withValues(alpha: 0.25),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(message, style: const TextStyle(color: AppColors.softCharcoal)),
      );
}

class _ReadingCard extends StatelessWidget {
  const _ReadingCard({required this.reading});
  final FaithReading reading;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(reading.title,
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            if (reading.reference.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(reading.reference,
                  style: const TextStyle(
                      color: AppColors.calmTeal, fontWeight: FontWeight.w600)),
            ],
            const SizedBox(height: 12),
            Text(reading.body,
                style: const TextStyle(fontSize: 16, height: 1.5)),
            if (reading.reflectionPrompt.isNotEmpty) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: AppColors.goldLight.withValues(alpha: 0.25),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('💬  '),
                    Expanded(
                      child: Text(reading.reflectionPrompt,
                          style: const TextStyle(
                              fontStyle: FontStyle.italic, height: 1.4)),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ReflectionCard extends StatefulWidget {
  const _ReflectionCard({required this.reflected});
  final bool reflected;

  @override
  State<_ReflectionCard> createState() => _ReflectionCardState();
}

class _ReflectionCardState extends State<_ReflectionCard> {
  final _controller = TextEditingController();
  bool _saving = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_controller.text.trim().isEmpty) return;
    setState(() => _saving = true);
    final ok = await context.read<FaithViewModel>().reflect(_controller.text);
    if (!mounted) return;
    setState(() => _saving = false);
    if (ok) {
      _controller.clear();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Reflection saved 🙏')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.reflected) {
      return Card(
        elevation: 0,
        color: AppColors.sageGreen.withValues(alpha: 0.18),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: const Padding(
          padding: EdgeInsets.all(16),
          child: Row(
            children: [
              Icon(Icons.check_circle, color: AppColors.calmTeal),
              SizedBox(width: 10),
              Expanded(child: Text('You reflected today. See you tomorrow.')),
            ],
          ),
        ),
      );
    }
    return Card(
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Your reflection',
                style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            Text('Private to you — your partner never sees it.',
                style: TextStyle(
                    fontSize: 12,
                    color: AppColors.softCharcoal.withValues(alpha: 0.6))),
            const SizedBox(height: 10),
            TextField(
              controller: _controller,
              maxLines: 3,
              maxLength: 4000,
              decoration: InputDecoration(
                hintText: 'A few words on today’s reading…',
                filled: true,
                fillColor: AppColors.creamWhite,
                border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide.none),
              ),
            ),
            Align(
              alignment: Alignment.centerRight,
              child: FilledButton(
                onPressed: _saving ? null : _save,
                style: FilledButton.styleFrom(backgroundColor: AppColors.warmCoral),
                child: _saving
                    ? const SizedBox(
                        width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Text('Save'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PracticesCard extends StatelessWidget {
  const _PracticesCard({required this.practices});
  final List<FaithPracticeItem> practices;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(16, 12, 16, 4),
              child: Text('Today’s practices',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            ),
            if (practices.isEmpty)
              const Padding(
                padding: EdgeInsets.all(16),
                child: Text('No practices available.'),
              )
            else
              ...practices.map((p) => _PracticeTile(item: p)),
          ],
        ),
      ),
    );
  }
}

class _PracticeTile extends StatelessWidget {
  const _PracticeTile({required this.item});
  final FaithPracticeItem item;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Text(item.icon.isEmpty ? '•' : item.icon,
          style: const TextStyle(fontSize: 22)),
      title: Text(item.label,
          style: TextStyle(
            decoration: item.completed ? TextDecoration.lineThrough : null,
            color: item.completed
                ? AppColors.softCharcoal.withValues(alpha: 0.5)
                : AppColors.softCharcoal,
          )),
      trailing: item.completed
          ? const Icon(Icons.check_circle, color: AppColors.calmTeal)
          : const Icon(Icons.radio_button_unchecked, color: AppColors.rosePeach),
      onTap: item.completed
          ? null
          : () => context.read<FaithViewModel>().completePractice(item.key),
    );
  }
}
