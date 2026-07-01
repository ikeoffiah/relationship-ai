import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/onboarding/onboarding_viewmodel.dart';

/// Screen 2: Relationship context — stage, duration, cohabitation, children, reason.
class RelationshipContextScreen extends StatelessWidget {
  final VoidCallback onNext;

  const RelationshipContextScreen({required this.onNext, super.key});

  static const List<Map<String, String>> _stageOptions = [
    {'value': 'dating', 'label': 'Dating', 'icon': '💐'},
    {'value': 'committed', 'label': 'Committed', 'icon': '💑'},
    {'value': 'engaged', 'label': 'Engaged', 'icon': '💍'},
    {'value': 'married', 'label': 'Married', 'icon': '💒'},
    {'value': 'long_distance', 'label': 'Long Distance', 'icon': '🌍'},
    {'value': 'reconnecting', 'label': 'Reconnecting', 'icon': '🔄'},
  ];

  static const List<String> _reasons = [
    'Improve communication',
    'Strengthen our bond',
    'Navigate a conflict',
    'Deepen understanding',
    'Prepare for a milestone',
    'General wellness',
  ];

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<OnboardingViewModel>();

    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Intro ──────────────────────────────────────────────
            Text(
              'Tell us about your relationship',
              style: Theme.of(context).textTheme.displaySmall,
            ),
            const SizedBox(height: 6),
            Text(
              'This helps us personalize guidance to where you are right now.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.softCharcoal.withValues(alpha: 0.6),
                  ),
            ),
            const SizedBox(height: 24),

            // ── Relationship stage chips ───────────────────────────
            Text(
              'Relationship stage',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: _stageOptions.map((opt) {
                final isSelected = vm.relationshipStage == opt['value'];
                return GestureDetector(
                  onTap: () => vm.setRelationshipStage(opt['value']!),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 12),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(20),
                      gradient: isSelected
                          ? const LinearGradient(
                              colors: [AppColors.warmCoral, AppColors.softRose])
                          : null,
                      color: isSelected
                          ? null
                          : AppColors.softRose.withValues(alpha: 0.18),
                      border: Border.all(
                        color: isSelected
                            ? Colors.transparent
                            : AppColors.softCharcoal.withValues(alpha: 0.1),
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(opt['icon']!, style: const TextStyle(fontSize: 18)),
                        const SizedBox(width: 6),
                        Text(
                          opt['label']!,
                          style: Theme.of(context)
                              .textTheme
                              .bodyMedium
                              ?.copyWith(
                                color: isSelected
                                    ? Colors.white
                                    : AppColors.softCharcoal,
                                fontWeight: isSelected
                                    ? FontWeight.w600
                                    : FontWeight.w400,
                              ),
                        ),
                      ],
                    ),
                  ),
                );
              }).toList(),
            ),
            const SizedBox(height: 28),

            // ── Duration slider ────────────────────────────────────
            Text(
              'How long have you been together?',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: SliderTheme(
                    data: SliderThemeData(
                      activeTrackColor: AppColors.warmCoral,
                      inactiveTrackColor:
                          AppColors.softRose.withValues(alpha: 0.3),
                      thumbColor: AppColors.warmCoral,
                      overlayColor: AppColors.warmCoral.withValues(alpha: 0.15),
                      trackHeight: 4,
                    ),
                    child: Slider(
                      min: 0,
                      max: 240,
                      divisions: 48,
                      value:
                          (vm.relationshipDurationMonths ?? 0).toDouble(),
                      onChanged: (v) =>
                          vm.setRelationshipDuration(v.round()),
                    ),
                  ),
                ),
                SizedBox(
                  width: 70,
                  child: Text(
                    _durationLabel(vm.relationshipDurationMonths ?? 0),
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          fontWeight: FontWeight.w600,
                          color: AppColors.warmCoral,
                        ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // ── Cohabitation toggle ────────────────────────────────
            _ToggleRow(
              label: 'Do you live together?',
              value: vm.cohabiting,
              onChanged: vm.setCohabiting,
            ),
            const SizedBox(height: 20),

            // ── Children counter ───────────────────────────────────
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Children',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                ),
                _CounterButton(
                  icon: Icons.remove,
                  onPressed: vm.childrenCount > 0
                      ? () => vm.setChildrenCount(vm.childrenCount - 1)
                      : null,
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  child: Text(
                    vm.childrenCount.toString(),
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                  ),
                ),
                _CounterButton(
                  icon: Icons.add,
                  onPressed: () =>
                      vm.setChildrenCount(vm.childrenCount + 1),
                ),
              ],
            ),
            const SizedBox(height: 28),

            // ── Reason for using ───────────────────────────────────
            Text(
              'What brings you here?',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _reasons.map((r) {
                final isSelected = vm.reasonForUsing == r;
                return ChoiceChip(
                  label: Text(r),
                  selected: isSelected,
                  onSelected: (_) => vm.setReasonForUsing(r),
                  selectedColor: AppColors.calmTeal,
                  backgroundColor:
                      AppColors.sageGreen.withValues(alpha: 0.2),
                  labelStyle: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(
                        color: isSelected
                            ? Colors.white
                            : AppColors.softCharcoal,
                      ),
                );
              }).toList(),
            ),
            const SizedBox(height: 32),

            // ── Continue ───────────────────────────────────────────
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: vm.isRelationshipContextComplete ? onNext : null,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.warmCoral,
                  disabledBackgroundColor:
                      AppColors.warmCoral.withValues(alpha: 0.4),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(24)),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
                child: Text(
                  'Continue',
                  style: Theme.of(context)
                      .textTheme
                      .bodyLarge
                      ?.copyWith(color: Colors.white),
                ),
              ),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  String _durationLabel(int months) {
    if (months < 12) return '$months mo';
    final years = months ~/ 12;
    final rem = months % 12;
    if (rem == 0) return '$years yr';
    return '$years yr $rem mo';
  }
}

// ── Helper widgets ───────────────────────────────────────────────────────────

class _ToggleRow extends StatelessWidget {
  final String label;
  final bool? value;
  final ValueChanged<bool?> onChanged;

  const _ToggleRow({
    required this.label,
    required this.value,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Text(label,
              style: Theme.of(context).textTheme.headlineSmall),
        ),
        _pill(context, 'Yes', true),
        const SizedBox(width: 8),
        _pill(context, 'No', false),
      ],
    );
  }

  Widget _pill(BuildContext ctx, String text, bool val) {
    final isActive = value == val;
    return GestureDetector(
      onTap: () => onChanged(val),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          color: isActive
              ? AppColors.calmTeal
              : AppColors.sageGreen.withValues(alpha: 0.2),
        ),
        child: Text(
          text,
          style: Theme.of(ctx).textTheme.bodyMedium?.copyWith(
                color: isActive ? Colors.white : AppColors.softCharcoal,
                fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
              ),
        ),
      ),
    );
  }
}

class _CounterButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback? onPressed;

  const _CounterButton({required this.icon, this.onPressed});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onPressed,
      child: Container(
        width: 36,
        height: 36,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: onPressed != null
              ? AppColors.warmCoral.withValues(alpha: 0.15)
              : AppColors.softCharcoal.withValues(alpha: 0.06),
        ),
        child: Icon(
          icon,
          size: 18,
          color: onPressed != null
              ? AppColors.warmCoral
              : AppColors.softCharcoal.withValues(alpha: 0.3),
        ),
      ),
    );
  }
}
