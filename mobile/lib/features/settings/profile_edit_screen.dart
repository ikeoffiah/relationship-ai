import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/features/settings/viewmodels/settings_viewmodel.dart';

/// Profile editing screen — display name + read-only email.
class ProfileEditScreen extends StatefulWidget {
  const ProfileEditScreen({super.key});

  @override
  State<ProfileEditScreen> createState() => _ProfileEditScreenState();
}

class _ProfileEditScreenState extends State<ProfileEditScreen> {
  final _nameController = TextEditingController();
  bool _hasChanges = false;

  @override
  void initState() {
    super.initState();
    final vm = context.read<SettingsViewModel>();
    _nameController.text = vm.displayName;
    _nameController.addListener(() {
      setState(() {
        _hasChanges = _nameController.text.trim() != vm.displayName;
      });
    });
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Edit Profile'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: true,
        actions: [
          if (_hasChanges)
            TextButton(
              onPressed: _save,
              child: const Text('Save'),
            ),
        ],
      ),
      body: Consumer2<SettingsViewModel, AuthViewModel>(
        builder: (context, settingsVM, authVM, _) {
          return Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Avatar placeholder
                Center(
                  child: CircleAvatar(
                    radius: 48,
                    backgroundColor: AppColors.warmCoral.withValues(alpha: 0.15),
                    child: Text(
                      settingsVM.displayName.isNotEmpty
                          ? settingsVM.displayName[0].toUpperCase()
                          : '?',
                      style: const TextStyle(
                        fontSize: 36,
                        fontWeight: FontWeight.bold,
                        color: AppColors.warmCoral,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                Center(
                  child: Text(
                    'Profile photo stored locally only',
                    style: TextStyle(
                      fontSize: 12,
                      color: AppColors.softCharcoal.withValues(alpha: 0.5),
                    ),
                  ),
                ),
                const SizedBox(height: 32),

                // Display name
                const Text(
                  'Display name',
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: AppColors.softCharcoal,
                  ),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _nameController,
                  decoration: InputDecoration(
                    hintText: 'First name (shown to partner)',
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    filled: true,
                    fillColor: Colors.white,
                  ),
                ),
                const SizedBox(height: 24),

                // Email (read-only)
                const Text(
                  'Email address',
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: AppColors.softCharcoal,
                  ),
                ),
                const SizedBox(height: 8),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 16,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.grey[100],
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          settingsVM.email.isNotEmpty
                              ? settingsVM.email
                              : 'Not set',
                          style: TextStyle(
                            color: AppColors.softCharcoal.withValues(alpha: 0.7),
                          ),
                        ),
                      ),
                      GestureDetector(
                        onTap: () =>
                            Navigator.pushNamed(context, '/settings/email'),
                        child: const Text(
                          'Change email',
                          style: TextStyle(
                            color: AppColors.warmCoral,
                            fontWeight: FontWeight.w600,
                            fontSize: 13,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

                if (settingsVM.errorMessage != null) ...[
                  const SizedBox(height: 16),
                  Text(
                    settingsVM.errorMessage!,
                    style: const TextStyle(color: Colors.red, fontSize: 13),
                  ),
                ],
                if (settingsVM.successMessage != null) ...[
                  const SizedBox(height: 16),
                  Text(
                    settingsVM.successMessage!,
                    style: const TextStyle(color: AppColors.calmTeal, fontSize: 13),
                  ),
                ],
              ],
            ),
          );
        },
      ),
    );
  }

  Future<void> _save() async {
    final userId = context.read<AuthViewModel>().user?.id;
    if (userId == null) return;
    final vm = context.read<SettingsViewModel>();
    final success = await vm.updateDisplayName(userId, _nameController.text);
    if (success && mounted) {
      setState(() => _hasChanges = false);
    }
  }
}
