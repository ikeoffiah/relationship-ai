import 'package:flutter/material.dart';

import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_dimens.dart';
import 'package:mobile/features/settings/legal_documents.dart';

/// Renders a [LegalDocument].
///
/// Plain and readable rather than styled: nobody skims a privacy policy for
/// pleasure, and the job here is that someone who does decide to read it can.
/// So a comfortable measure, real paragraph spacing, and headings that are
/// findable — not a wall of 11pt grey.
class LegalDocumentScreen extends StatelessWidget {
  final LegalDocument document;

  const LegalDocumentScreen({required this.document, super.key});

  @override
  Widget build(BuildContext context) {
    final muted = AppColors.softCharcoal.withValues(alpha: 0.6);

    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: Text(
          document.title,
          style: Theme.of(context).textTheme.titleLarge,
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: SafeArea(
        top: false,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.xxl,
            AppSpacing.lg,
            AppSpacing.xxl,
            AppSpacing.xxxl,
          ),
          children: [
            Text(
              'Effective ${document.effectiveDate}',
              style: Theme.of(
                context,
              ).textTheme.labelSmall?.copyWith(color: muted),
            ),
            const SizedBox(height: AppSpacing.lg),
            Text(
              document.preamble,
              style: Theme.of(
                context,
              ).textTheme.bodyLarge?.copyWith(height: 1.5),
            ),
            const SizedBox(height: AppSpacing.xxl),
            for (final section in document.sections) ...[
              Text(
                section.heading,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: AppSpacing.sm),
              Text(
                section.body,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  height: 1.55,
                  color: AppColors.softCharcoal.withValues(alpha: 0.85),
                ),
              ),
              const SizedBox(height: AppSpacing.xxl),
            ],
          ],
        ),
      ),
    );
  }
}
