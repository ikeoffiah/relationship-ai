// File: security_settings_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/settings/viewmodels/settings_viewmodel.dart';
import 'package:mobile/shared/widgets/support_action.dart';

/// Security settings screen — biometric / PIN unlock and app lock timeout.
class SecuritySettingsScreen extends StatefulWidget {
  const SecuritySettingsScreen({super.key});

  @override
  State<SecuritySettingsScreen> createState() => _SecuritySettingsScreenState();
}

class _SecuritySettingsScreenState extends State<SecuritySettingsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback(
      (_) => context.read<SettingsViewModel>().loadBiometricPref(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Security Settings'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: true,
        actions: const [SupportAction()],
      ),
      body: Consumer<SettingsViewModel>(
        builder: (context, vm, _) {
          return ListView(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
            children: [
              // Biometric / device-credential unlock. Enabling requires a
              // successful biometric prompt (handled in the view model), so a
              // user can't enable a lock they can't pass.
              SwitchListTile(
                title: const Text('Biometric / PIN unlock'),
                subtitle: const Text('Require Face ID / fingerprint to open the app'),
                value: vm.biometricEnabled,
                onChanged: (v) => vm.setBiometricEnabled(v),
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
