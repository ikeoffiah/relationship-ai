import 'package:flutter/material.dart';
import 'package:package_info_plus/package_info_plus.dart';

import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_dimens.dart';
import 'package:mobile/features/settings/legal_document_screen.dart';
import 'package:mobile/features/settings/legal_documents.dart';
import 'package:mobile/shared/widgets/app_card.dart';
import 'package:mobile/shared/widgets/support_action.dart';

/// What Bliss is, what it is not, and where the policies are.
///
/// This screen used to be a version number, one sentence, two links to a domain
/// the product no longer uses, and a list reading "Flutter, Provider, Riverpod,
/// Sentry, …". Nobody opens About to learn which state-management package was
/// chosen; the acknowledgements were placeholder text that shipped.
///
/// What someone actually comes here for is the honest version of what they are
/// using — particularly the two things worth knowing before you type something
/// difficult into it: Bliss is not a therapist, and it can read your
/// conversation.
class AboutScreen extends StatefulWidget {
  const AboutScreen({super.key});

  @override
  State<AboutScreen> createState() => _AboutScreenState();
}

class _AboutScreenState extends State<AboutScreen> {
  String _version = '';
  String _build = '';

  @override
  void initState() {
    super.initState();
    _loadVersion();
  }

  Future<void> _loadVersion() async {
    try {
      final info = await PackageInfo.fromPlatform();
      if (!mounted) return;
      setState(() {
        _version = info.version;
        _build = info.buildNumber;
      });
    } catch (_) {
      // Not worth an error state. A missing version number is a cosmetic gap
      // on a screen whose real content is everything below it.
    }
  }

  void _open(LegalDocument document) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => LegalDocumentScreen(document: document),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final muted = AppColors.softCharcoal.withValues(alpha: 0.7);

    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: Text(
          'About Bliss',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: const [SupportAction()],
      ),
      body: SafeArea(
        top: false,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.xxl,
            AppSpacing.sm,
            AppSpacing.xxl,
            AppSpacing.xxxl,
          ),
          children: [
            Text(
              'Bliss helps two people say the hard things well.',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              'It sits alongside your conversation rather than in the middle '
              'of it: a rewrite when you cannot find the words, a pause before '
              'a message that will land harder than you mean, a private word '
              'when something difficult arrives. It never sends for you, and '
              'it never stops you sending.',
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(height: 1.5, color: muted),
            ),
            const SizedBox(height: AppSpacing.xl),

            // The two things worth knowing before typing something difficult
            // into this app. Given prominence rather than buried in the policy,
            // because someone who reads only this screen should still leave
            // with both.
            AppCard(
              borderColor: AppColors.noticeInk.withValues(alpha: 0.25),
              color: AppColors.noticeSurface,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Two things to know',
                    style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: AppColors.noticeInk,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    'Bliss is not a therapist. It is a self-help tool, not a '
                    'licensed professional, and it cannot handle an emergency. '
                    'If someone is in danger, use your local emergency number '
                    '— the Support screen lists services and works without an '
                    'account.\n\n'
                    'Bliss can read your conversation. Your messages are '
                    'encrypted where they are stored, but not end-to-end: the '
                    'key belongs to your relationship, so both of you can read '
                    'the thread on any device — and so can Bliss, which is how '
                    'it helps at all. You can switch assistance off in chat '
                    'settings and it becomes an ordinary chat.',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      height: 1.5,
                      color: AppColors.softCharcoal,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.xl),

            Text(
              'What your partner sees',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              'Your shared conversation, your plans and calendar, your goals, '
              'and game answers once you have both answered.\n\n'
              'Not your private sessions with Bliss, or that you had one. Not '
              'the private guidance Bliss gives you about a message they sent. '
              'Not what it has noticed about your own patterns. And not when '
              'you were last online — that is not recorded for display at all.',
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(height: 1.5, color: muted),
            ),
            const SizedBox(height: AppSpacing.xl),

            _LinkRow(
              icon: Icons.description_outlined,
              label: 'Terms of Service',
              onTap: () => _open(termsOfService),
            ),
            _LinkRow(
              icon: Icons.lock_outline_rounded,
              label: 'Privacy Policy',
              onTap: () => _open(privacyPolicy),
            ),
            _LinkRow(
              icon: Icons.favorite_border_rounded,
              label: 'Get support now',
              onTap: () => Navigator.of(context).pushNamed('/safety'),
            ),

            const SizedBox(height: AppSpacing.xxl),
            Center(
              child: Text(
                _version.isEmpty
                    ? 'Bliss'
                    : 'Bliss $_version${_build.isEmpty ? '' : ' ($_build)'}',
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: AppColors.softCharcoal.withValues(alpha: 0.45),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _LinkRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _LinkRow({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: AppCard(
        onTap: onTap,
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Row(
          children: [
            Icon(icon, size: 19, color: AppColors.warmCoral),
            const SizedBox(width: AppSpacing.lg),
            Expanded(
              child: Text(
                label,
                style: Theme.of(context).textTheme.bodyLarge,
              ),
            ),
            Icon(
              Icons.chevron_right_rounded,
              color: AppColors.softCharcoal.withValues(alpha: 0.35),
            ),
          ],
        ),
      ),
    );
  }
}
