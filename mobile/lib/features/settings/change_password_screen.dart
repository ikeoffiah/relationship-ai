import 'package:flutter/material.dart';

import 'package:mobile/core/api_services/settings_api_service.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_dimens.dart';
import 'package:mobile/shared/widgets/app_card.dart';

/// Change your password: the current one, then the new one.
///
/// Settings used to answer "Change password" by firing off a reset email and
/// showing a toast saying one had been sent. That is the flow for someone who
/// *cannot* sign in — using it on someone who already has means sending them out
/// of the app to their inbox to do something they were holding the credential
/// for anyway, and it lets anyone with an unlocked phone send mail to the
/// owner's address.
///
/// Asking for the current password is the substance, not a formality. A signed-in
/// session only proves someone has the phone; the current password is what
/// proves they are the account holder. The server checks it, and signs every
/// other session out on success — a password change is what someone does when
/// they think another person has access, so leaving that person's session alive
/// would make the change cosmetic.
class ChangePasswordScreen extends StatefulWidget {
  const ChangePasswordScreen({super.key});

  @override
  State<ChangePasswordScreen> createState() => _ChangePasswordScreenState();
}

class _ChangePasswordScreenState extends State<ChangePasswordScreen> {
  final _api = AccountSecurityApiService();
  final _current = TextEditingController();
  final _next = TextEditingController();
  final _confirm = TextEditingController();
  final _form = GlobalKey<FormState>();

  bool _busy = false;
  bool _showCurrent = false;
  bool _showNext = false;
  String? _error;

  @override
  void dispose() {
    _current.dispose();
    _next.dispose();
    _confirm.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!(_form.currentState?.validate() ?? false)) return;
    setState(() {
      _busy = true;
      _error = null;
    });

    final error = await _api.changePassword(
      current: _current.text,
      next: _next.text,
    );
    if (!mounted) return;
    setState(() => _busy = false);

    if (error != null) {
      setState(() => _error = error);
      return;
    }

    Navigator.of(context).pop();
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Password changed. Other devices have been signed out.'),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: Text(
          'Change password',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: SafeArea(
        top: false,
        child: Form(
          key: _form,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.xxl,
              AppSpacing.lg,
              AppSpacing.xxl,
              AppSpacing.xxxl,
            ),
            children: [
              if (_error != null) ...[
                Container(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  decoration: BoxDecoration(
                    color: AppColors.error.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(AppRadii.md),
                  ),
                  child: Text(
                    _error!,
                    style: Theme.of(
                      context,
                    ).textTheme.bodyMedium?.copyWith(color: AppColors.error),
                  ),
                ),
                const SizedBox(height: AppSpacing.lg),
              ],
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _field(
                      key: const Key('password_current'),
                      controller: _current,
                      label: 'Current password',
                      obscure: !_showCurrent,
                      onToggle: () =>
                          setState(() => _showCurrent = !_showCurrent),
                      validator: (v) => (v == null || v.isEmpty)
                          ? 'Enter your current password'
                          : null,
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    _field(
                      key: const Key('password_new'),
                      controller: _next,
                      label: 'New password',
                      obscure: !_showNext,
                      onToggle: () => setState(() => _showNext = !_showNext),
                      validator: (v) {
                        if (v == null || v.length < 8) {
                          return 'At least 8 characters';
                        }
                        if (v == _current.text) {
                          return 'Needs to be different from your current one';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    _field(
                      key: const Key('password_confirm'),
                      controller: _confirm,
                      label: 'New password again',
                      obscure: !_showNext,
                      onToggle: () => setState(() => _showNext = !_showNext),
                      // Confirmed on the client only. The server has no reason
                      // to receive it twice, and a typo is worth catching before
                      // a round trip rather than after one.
                      validator: (v) =>
                          v == _next.text ? null : 'These do not match',
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.lg),
              Text(
                'Changing your password signs you out everywhere else.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: AppSpacing.xl),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  key: const Key('password_submit'),
                  onPressed: _busy ? null : _submit,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.warmCoral,
                    foregroundColor: Colors.white,
                    elevation: 0,
                    padding: const EdgeInsets.symmetric(
                      vertical: AppSpacing.lg,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppRadii.lg),
                    ),
                  ),
                  child: Text(_busy ? 'Changing…' : 'Change password'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _field({
    required Key key,
    required TextEditingController controller,
    required String label,
    required bool obscure,
    required VoidCallback onToggle,
    required String? Function(String?) validator,
  }) {
    return TextFormField(
      key: key,
      controller: controller,
      obscureText: obscure,
      autocorrect: false,
      enableSuggestions: false,
      validator: validator,
      decoration: InputDecoration(
        labelText: label,
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadii.md),
        ),
        suffixIcon: IconButton(
          onPressed: onToggle,
          icon: Icon(
            obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined,
            size: 20,
          ),
          tooltip: obscure ? 'Show' : 'Hide',
        ),
      ),
    );
  }
}
