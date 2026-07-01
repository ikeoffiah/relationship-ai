import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/onboarding/onboarding_viewmodel.dart';

/// Screen 3: Cultural context — background, religious values,
/// communication style preference, family/community orientation.
class CulturalContextScreen extends StatelessWidget {
  final VoidCallback onNext;

  const CulturalContextScreen({required this.onNext, super.key});

  static const List<String> _backgrounds = [
    'East Asian',
    'South Asian',
    'Southeast Asian',
    'Middle Eastern',
    'African',
    'Latin American',
    'European',
    'North American',
    'Caribbean',
    'Pacific Islander',
    'Mixed / Multicultural',
    'Prefer not to say',
  ];

  static const List<String> _religiousOptions = [
    'Christianity',
    'Islam',
    'Judaism',
    'Hinduism',
    'Buddhism',
    'Sikhism',
    'Spiritual but not religious',
    'Non-religious / Secular',
    'Other',
    'Prefer not to say',
  ];

  static const List<Map<String, String>> _commStyles = [
    {
      'value': 'direct',
      'label': 'Direct',
      'desc': 'I say exactly what I mean',
      'icon': '🎯',
    },
    {
      'value': 'indirect',
      'label': 'Indirect',
      'desc': 'I prefer subtle hints and context',
      'icon': '🌊',
    },
    {
      'value': 'mixed',
      'label': 'It Depends',
      'desc': 'Depends on the situation',
      'icon': '🔄',
    },
  ];

  static const List<Map<String, String>> _familyOrientations = [
    {
      'value': 'individual',
      'label': 'Individual',
      'desc': 'My partner and I decide together',
      'icon': '👤',
    },
    {
      'value': 'family_oriented',
      'label': 'Family-Oriented',
      'desc': 'Extended family plays a key role',
      'icon': '👨‍👩‍👧‍👦',
    },
    {
      'value': 'community',
      'label': 'Community',
      'desc': 'Community and elders guide us',
      'icon': '🏘️',
    },
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
              'Your cultural context',
              style: Theme.of(context).textTheme.displaySmall,
            ),
            const SizedBox(height: 6),
            Text(
              'Understanding your background helps us communicate in a way that feels right for you.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.softCharcoal.withValues(alpha: 0.6),
                  ),
            ),
            const SizedBox(height: 24),

            // ── Cultural background ────────────────────────────────
            Text(
              'Cultural background',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _backgrounds.map((b) {
                final isSelected = vm.culturalBackground == b;
                return ChoiceChip(
                  label: Text(b),
                  selected: isSelected,
                  onSelected: (_) => vm.setCulturalBackground(b),
                  selectedColor: AppColors.calmTeal,
                  backgroundColor:
                      AppColors.sageGreen.withValues(alpha: 0.18),
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
            const SizedBox(height: 28),

            // ── Religious / spiritual values ───────────────────────
            Text(
              'Religious or spiritual values',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _religiousOptions.map((r) {
                final isSelected = vm.religiousValues == r;
                return ChoiceChip(
                  label: Text(r),
                  selected: isSelected,
                  onSelected: (_) => vm.setReligiousValues(r),
                  selectedColor: AppColors.goldMedium,
                  backgroundColor:
                      AppColors.goldLight.withValues(alpha: 0.2),
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
            const SizedBox(height: 28),

            // ── Communication style preference ─────────────────────
            Text(
              'Communication style preference',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 10),
            ..._commStyles.map((opt) => _OptionCard(
                  icon: opt['icon']!,
                  label: opt['label']!,
                  description: opt['desc']!,
                  isSelected:
                      vm.communicationStylePreference == opt['value'],
                  onTap: () =>
                      vm.setCommunicationStylePreference(opt['value']!),
                )),
            const SizedBox(height: 28),

            // ── Family / community orientation ─────────────────────
            Text(
              'Family & community orientation',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 10),
            ..._familyOrientations.map((opt) => _OptionCard(
                  icon: opt['icon']!,
                  label: opt['label']!,
                  description: opt['desc']!,
                  isSelected:
                      vm.familyCommunityOrientation == opt['value'],
                  onTap: () =>
                      vm.setFamilyCommunityOrientation(opt['value']!),
                )),
            const SizedBox(height: 32),

            // ── Continue ───────────────────────────────────────────
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: vm.isCulturalContextComplete ? onNext : null,
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
}

// ── Reusable option card ─────────────────────────────────────────────────────

class _OptionCard extends StatelessWidget {
  final String icon;
  final String label;
  final String description;
  final bool isSelected;
  final VoidCallback onTap;

  const _OptionCard({
    required this.icon,
    required this.label,
    required this.description,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            gradient: isSelected
                ? const LinearGradient(
                    colors: [AppColors.warmCoral, AppColors.softRose])
                : null,
            color: isSelected
                ? null
                : AppColors.softRose.withValues(alpha: 0.12),
            border: Border.all(
              color: isSelected
                  ? Colors.transparent
                  : AppColors.softCharcoal.withValues(alpha: 0.08),
            ),
          ),
          child: Row(
            children: [
              Text(icon, style: const TextStyle(fontSize: 24)),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      style: Theme.of(context)
                          .textTheme
                          .bodyLarge
                          ?.copyWith(
                            fontWeight: FontWeight.w600,
                            color: isSelected
                                ? Colors.white
                                : AppColors.softCharcoal,
                          ),
                    ),
                    Text(
                      description,
                      style: Theme.of(context)
                          .textTheme
                          .bodySmall
                          ?.copyWith(
                            color: isSelected
                                ? Colors.white.withValues(alpha: 0.85)
                                : AppColors.softCharcoal
                                    .withValues(alpha: 0.6),
                          ),
                    ),
                  ],
                ),
              ),
              if (isSelected)
                const Icon(Icons.check_circle_rounded,
                    color: Colors.white, size: 22),
            ],
          ),
        ),
      ),
    );
  }
}
