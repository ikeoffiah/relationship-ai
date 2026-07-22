import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/features/settings/viewmodels/settings_viewmodel.dart';
import 'package:mobile/features/settings/profile_edit_screen.dart';
import 'package:mobile/features/settings/security_settings_screen.dart';
import 'package:mobile/features/settings/about_screen.dart';
import 'package:mobile/shared/widgets/get_help_now_button.dart';

/// Main Settings screen — account management hub (bottom-nav tab 4).
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadData();
    });
  }

  Future<void> _loadData() async {
    final userId = context.read<AuthViewModel>().user?.id;
    if (userId == null) return;
    final vm = context.read<SettingsViewModel>();
    await Future.wait([
      vm.loadProfile(userId),
      vm.loadNotificationPreferences(userId),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Settings'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: true,
      ),
      body: Consumer2<SettingsViewModel, AuthViewModel>(
        builder: (context, settingsVM, authVM, _) {
          final userId = authVM.user?.id ?? '';

          return ListView(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
            children: [
              const GetHelpNowButton(),
              const SizedBox(height: 20),

              // ── Account ─────────────────────────────────────────────────
              _buildSectionHeader('ACCOUNT'),
              _buildSettingsTile(
                icon: Icons.person_outline_rounded,
                title: 'Profile & display name',
                subtitle: settingsVM.displayName.isNotEmpty
                    ? settingsVM.displayName
                    : null,
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => const ProfileEditScreen(),
                  ),
                ),
              ),
              _buildSettingsTile(
                icon: Icons.email_outlined,
                title: 'Email address',
                subtitle: settingsVM.email.isNotEmpty
                    ? settingsVM.email
                    : null,
                onTap: () => Navigator.pushNamed(context, '/settings/email'),
              ),
              _buildSettingsTile(
                icon: Icons.lock_outline_rounded,
                title: 'Change password',
                onTap: () {
                  // Re-use existing forgot-password flow
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('A password reset email will be sent.'),
                    ),
                  );
                  authVM.sendPasswordResetEmail();
                },
              ),
              const SizedBox(height: 24),

              // ── Security ────────────────────────────────────────────────
              _buildSectionHeader('SECURITY'),
              _buildSettingsTile(
                icon: Icons.fingerprint_rounded,
                title: 'Biometric / PIN unlock',
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => const SecuritySettingsScreen(),
                  ),
                ),
              ),
              _buildDropdownTile(
                icon: Icons.timer_outlined,
                title: 'App lock timeout',
                value: settingsVM.appLockTimeoutMinutes,
                options: const [1, 5, 15, 30],
                formatLabel: (v) => v == 1 ? '1 min' : '$v min',
                onChanged: (v) => settingsVM.setAppLockTimeout(v),
              ),
              const SizedBox(height: 24),

              // ── Relationship ────────────────────────────────────────────
              _buildSectionHeader('RELATIONSHIP'),
              _buildSettingsTile(
                icon: Icons.favorite_outline_rounded,
                title: 'Partner connection',
                onTap: () =>
                    Navigator.pushNamed(context, '/relationship/invite'),
              ),
              _buildSettingsTile(
                icon: Icons.auto_stories_outlined,
                title: 'Our story',
                subtitle: 'Shared goals and repair moments',
                onTap: () => Navigator.pushNamed(context, '/our-story'),
              ),
              const SizedBox(height: 24),

              // ── Notifications ───────────────────────────────────────────
              _buildSectionHeader('NOTIFICATIONS'),
              _buildToggleTile(
                title: 'Session reminders',
                value: settingsVM.notificationPrefs.sessionReminders,
                onChanged: (v) => settingsVM.toggleNotificationPref(
                    userId, 'session_reminders', v),
              ),
              _buildToggleTile(
                title: 'Partner joined session',
                value: settingsVM.notificationPrefs.partnerJoinedSession,
                onChanged: (v) => settingsVM.toggleNotificationPref(
                    userId, 'partner_joined_session', v),
              ),
              _buildToggleTile(
                title: 'Relay message received',
                value: settingsVM.notificationPrefs.relayMessageReceived,
                onChanged: (v) => settingsVM.toggleNotificationPref(
                    userId, 'relay_message_received', v),
              ),
              _buildToggleTile(
                title: 'Insight detected',
                value: settingsVM.notificationPrefs.insightDetected,
                onChanged: (v) => settingsVM.toggleNotificationPref(
                    userId, 'insight_detected', v),
              ),
              const SizedBox(height: 24),

              // ── Data & Privacy ──────────────────────────────────────────
              _buildSectionHeader('DATA & PRIVACY'),
              _buildSettingsTile(
                icon: Icons.lock_outline_rounded,
                title: 'Privacy settings (consent)',
                onTap: () => Navigator.pushNamed(context, '/consent'),
              ),
              _buildSettingsTile(
                icon: Icons.download_outlined,
                title: 'Download my data',
                onTap: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text(
                        'Data export will be available soon.',
                      ),
                    ),
                  );
                },
              ),
              _buildSettingsTile(
                icon: Icons.delete_outline_rounded,
                title: 'Delete my data',
                onTap: () => Navigator.pushNamed(context, '/consent'),
              ),
              const SizedBox(height: 24),

              // ── Support ─────────────────────────────────────────────────
              _buildSectionHeader('SUPPORT'),
              _buildSettingsTile(
                icon: Icons.info_outline_rounded,
                title: 'About RelationshipAI',
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const AboutScreen()),
                ),
              ),
              _buildSettingsTile(
                icon: Icons.description_outlined,
                title: 'Terms of Service',
                onTap: () {
                  // TODO: open in-app browser
                },
              ),
              _buildSettingsTile(
                icon: Icons.privacy_tip_outlined,
                title: 'Privacy Policy',
                onTap: () {
                  // TODO: open in-app browser
                },
              ),
              _buildSettingsTile(
                icon: Icons.feedback_outlined,
                title: 'Send feedback',
                onTap: () {
                  // TODO: open feedback form
                },
              ),
              const SizedBox(height: 24),

              // ── Danger Zone ─────────────────────────────────────────────
              _buildSectionHeader('DANGER ZONE'),
              _buildSettingsTile(
                icon: Icons.delete_forever_rounded,
                title: 'Delete account',
                titleColor: Colors.red[700],
                onTap: () => _showDeleteAccountSheet(context, settingsVM, userId),
              ),
              const SizedBox(height: 16),

              // ── Sign Out ────────────────────────────────────────────────
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: () async {
                    await authVM.logout();
                    if (context.mounted) {
                      Navigator.of(context)
                          .pushNamedAndRemoveUntil('/', (_) => false);
                    }
                  },
                  icon: const Icon(Icons.logout_rounded),
                  label: const Text('Sign out'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.softCharcoal,
                    side: BorderSide(
                      color: AppColors.softCharcoal.withValues(alpha: 0.3),
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                ),
              ),
              const SizedBox(height: 100), // room for bottom nav
            ],
          );
        },
      ),
    );
  }

  // ── Widget helpers ────────────────────────────────────────────────────

  Widget _buildSectionHeader(String label) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w700,
          letterSpacing: 1.2,
          color: AppColors.softCharcoal.withValues(alpha: 0.45),
        ),
      ),
    );
  }

  Widget _buildSettingsTile({
    required IconData icon,
    required String title,
    String? subtitle,
    Color? titleColor,
    required VoidCallback onTap,
  }) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: ListTile(
        leading: Icon(icon, color: titleColor ?? AppColors.warmCoral),
        title: Text(
          title,
          style: TextStyle(
            fontWeight: FontWeight.w600,
            color: titleColor ?? AppColors.softCharcoal,
          ),
        ),
        subtitle: subtitle != null
            ? Text(
                subtitle,
                style: TextStyle(
                  fontSize: 13,
                  color: AppColors.softCharcoal.withValues(alpha: 0.6),
                ),
              )
            : null,
        trailing: Icon(
          Icons.chevron_right_rounded,
          color: AppColors.softCharcoal.withValues(alpha: 0.3),
        ),
        onTap: onTap,
      ),
    );
  }

  Widget _buildToggleTile({
    required String title,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: SwitchListTile(
        title: Text(
          title,
          style: const TextStyle(
            fontWeight: FontWeight.w600,
            color: AppColors.softCharcoal,
          ),
        ),
        value: value,
        onChanged: onChanged,
        activeThumbColor: AppColors.warmCoral,
      ),
    );
  }

  Widget _buildDropdownTile({
    required IconData icon,
    required String title,
    required int value,
    required List<int> options,
    required String Function(int) formatLabel,
    required ValueChanged<int> onChanged,
  }) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: ListTile(
        leading: Icon(icon, color: AppColors.warmCoral),
        title: Text(
          title,
          style: const TextStyle(
            fontWeight: FontWeight.w600,
            color: AppColors.softCharcoal,
          ),
        ),
        trailing: DropdownButton<int>(
          value: value,
          underline: const SizedBox(),
          items: options
              .map((o) => DropdownMenuItem(value: o, child: Text(formatLabel(o))))
              .toList(),
          onChanged: (v) {
            if (v != null) onChanged(v);
          },
        ),
      ),
    );
  }

  // ── Delete account bottom sheet ───────────────────────────────────────

  void _showDeleteAccountSheet(
    BuildContext context,
    SettingsViewModel vm,
    String userId,
  ) {
    final passwordController = TextEditingController();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
          left: 24,
          right: 24,
          top: 24,
          bottom: MediaQuery.of(ctx).viewInsets.bottom + 24,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Delete your account?',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            Text(
              'This will permanently delete:\n'
              '• Your profile and all sessions\n'
              '• All stored memories\n'
              '• Your connection with your partner\n'
              '• All your data from our servers\n\n'
              'This cannot be undone.',
              style: TextStyle(
                fontSize: 14,
                color: AppColors.softCharcoal.withValues(alpha: 0.7),
                height: 1.6,
              ),
            ),
            const SizedBox(height: 20),
            TextField(
              controller: passwordController,
              obscureText: true,
              decoration: InputDecoration(
                labelText: 'Enter your password to confirm',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
            const SizedBox(height: 20),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => Navigator.pop(ctx),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: const Text('Cancel'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () async {
                      final success = await vm.deleteAccount(
                        userId,
                        passwordController.text,
                      );
                      if (ctx.mounted && success) {
                        Navigator.of(ctx).pop();
                        if (context.mounted) {
                          Navigator.of(context)
                              .pushNamedAndRemoveUntil('/', (_) => false);
                        }
                      } else if (ctx.mounted) {
                        ScaffoldMessenger.of(ctx).showSnackBar(
                          SnackBar(
                            content: Text(
                              vm.errorMessage ?? 'Failed to delete account',
                            ),
                          ),
                        );
                      }
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.red[700],
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: const Text('Delete my account'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
