// File: security_settings_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/settings/viewmodels/settings_viewmodel.dart';
import 'package:mobile/shared/widgets/get_help_now_button.dart';

/// Security settings screen — biometric / PIN unlock and app lock timeout.
class SecuritySettingsScreen extends StatelessWidget {
  const SecuritySettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Security Settings'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: true,
        actions: const [GetHelpNowButton()],
      ),
      body: Consumer<SettingsViewModel>(
        builder: (context, vm, _) {
          return ListView(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
            children: [
              // Biometric toggle – placeholder (actual implementation via BiometricAuthService elsewhere)
              SwitchListTile(
                title: const Text('Biometric / PIN unlock'),
                value: vm.notificationPrefs.sessionReminders, // placeholder value
                onChanged: (v) {
                  // TODO: integrate real biometric toggle
                },
                activeThumbColor: AppColors.warmCoral,
              ),
              const SizedBox(height: 16),
              // App lock timeout selector
              ListTile(
                leading: const Icon(Icons.timer_outlined, color: AppColors.warmCoral),
                title: const Text('App lock timeout'),
                trailing: DropdownButton<int>(
                  value: vm.appLockTimeoutMinutes,
                  underline: const SizedBox(),
                  items: const [1, 5, 15, 30]
                      .map((v) => DropdownMenuItem<int>(
                            value: v,
                            child: Text(v == 1 ? '1 min' : '$v min'),
                          ))
                      .toList(),
                  onChanged: (v) {
                    if (v != null) vm.setAppLockTimeout(v);
                  },
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
