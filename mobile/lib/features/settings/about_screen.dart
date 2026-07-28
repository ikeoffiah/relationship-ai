// File: about_screen.dart
import 'package:flutter/material.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/utils/external_links.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:mobile/shared/widgets/support_action.dart';

/// About screen – displays app version and informational links.
class AboutScreen extends StatefulWidget {
  const AboutScreen({super.key});

  @override
  State<AboutScreen> createState() => _AboutScreenState();
}

class _AboutScreenState extends State<AboutScreen> {
  String _version = '';

  @override
  void initState() {
    super.initState();
    _loadVersion();
  }

  Future<void> _loadVersion() async {
    final info = await PackageInfo.fromPlatform();
    setState(() => _version = info.version);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('About Bliss'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: true,
        actions: const [SupportAction()],
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: ListView(
          children: [
            Text('Version: $_version', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            const SizedBox(height: 24),
            const Text(
              'Bliss is an AI-powered support tool, not a licensed therapist or medical service.',
              style: TextStyle(fontSize: 14),
            ),
            const SizedBox(height: 24),
            _buildLinkTile(context, 'Terms of Service', () => openUrl(context, AppLinks.terms)),
            _buildLinkTile(context, 'Privacy Policy', () => openUrl(context, AppLinks.privacy)),
            _buildLinkTile(context, 'Crisis Resources',
                () => Navigator.of(context).pushNamed('/safety')),
            const SizedBox(height: 24),
            const Text('Acknowledgements', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
            const SizedBox(height: 12),
            const Text('• Flutter\n• Provider\n• Riverpod\n• Sentry\n• ...', style: TextStyle(fontSize: 14)),
          ],
        ),
      ),
    );
  }

  Widget _buildLinkTile(BuildContext context, String title, VoidCallback onTap) {
    return ListTile(
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.warmCoral)),
      trailing: const Icon(Icons.chevron_right_rounded, color: AppColors.softCharcoal),
      onTap: onTap,
    );
  }
}
