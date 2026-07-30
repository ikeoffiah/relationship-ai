import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'package:mobile/core/api_services/settings_api_service.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_dimens.dart';
import 'package:mobile/shared/widgets/app_card.dart';

/// Your email address: verify it, and change it only while you still can.
///
/// The order is the point, and it is the opposite of what this screen used to
/// do — it opened straight onto a change form. Verifying comes first because
/// this address is what a partner invitation is sent to, so an unverified one
/// means an invitation can be delivered to somebody who never signed up, and
/// because it is what the other person recognises you by.
///
/// Changing stays open while unverified, since the likeliest reason someone
/// cannot verify is a typo. It closes once verified: moving it afterwards would
/// turn a verified account into an unverified one with nothing looking
/// different. The server enforces that; this screen reads `canChange` from the
/// server rather than deciding for itself, so the two cannot disagree.
class EmailChangeScreen extends StatefulWidget {
  const EmailChangeScreen({super.key});

  @override
  State<EmailChangeScreen> createState() => _EmailChangeScreenState();
}

class _EmailChangeScreenState extends State<EmailChangeScreen> {
  final _api = AccountSecurityApiService();
  final _code = TextEditingController();
  final _newEmail = TextEditingController();

  String _email = '';
  bool _verified = false;
  bool _canChange = false;
  bool _loading = true;
  bool _busy = false;
  bool _codeSent = false;
  String? _message;
  bool _messageIsError = false;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  @override
  void dispose() {
    _code.dispose();
    _newEmail.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final status = await _api.emailStatus();
      if (!mounted) return;
      setState(() {
        _email = status.email;
        _verified = status.verified;
        _canChange = status.canChange;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _message = 'Could not load your email settings.';
        _messageIsError = true;
      });
    }
  }

  void _say(String? error, String success) {
    setState(() {
      _message = error ?? success;
      _messageIsError = error != null;
    });
  }

  Future<void> _send() async {
    setState(() => _busy = true);
    final error = await _api.sendVerificationCode();
    if (!mounted) return;
    setState(() {
      _busy = false;
      _codeSent = error == null;
    });
    _say(error, 'We sent a six-digit code to $_email.');
  }

  Future<void> _confirm() async {
    if (_code.text.trim().length < 6) return;
    setState(() => _busy = true);
    final error = await _api.confirmCode(_code.text.trim());
    if (!mounted) return;
    setState(() => _busy = false);
    if (error != null) {
      _say(error, '');
      return;
    }
    _code.clear();
    await _refresh();
    if (!mounted) return;
    _say(null, 'Your email is verified.');
  }

  Future<void> _change() async {
    final next = _newEmail.text.trim();
    if (next.isEmpty || !next.contains('@')) {
      _say('Enter a valid email address.', '');
      return;
    }
    setState(() => _busy = true);
    final error = await _api.changeEmail(next);
    if (!mounted) return;
    setState(() => _busy = false);
    if (error != null) {
      _say(error, '');
      return;
    }
    _newEmail.clear();
    _codeSent = false;
    await _refresh();
    if (!mounted) return;
    _say(null, 'Updated. Verify it when you are ready.');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: Text(
          'Email address',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: _loading
          ? const Center(
              child: CircularProgressIndicator(color: AppColors.warmCoral),
            )
          : SafeArea(
              top: false,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.xxl,
                  AppSpacing.lg,
                  AppSpacing.xxl,
                  AppSpacing.xxxl,
                ),
                children: [
                  _CurrentAddress(email: _email, verified: _verified),
                  const SizedBox(height: AppSpacing.xl),
                  if (_message != null) ...[
                    _Message(text: _message!, isError: _messageIsError),
                    const SizedBox(height: AppSpacing.lg),
                  ],
                  if (!_verified) _verifySection(),
                  if (_canChange) ...[
                    const SizedBox(height: AppSpacing.xl),
                    _changeSection(),
                  ],
                  if (_verified) ...[
                    const SizedBox(height: AppSpacing.md),
                    Text(
                      'A verified address is fixed. It is what your partner was '
                      'invited by, so changing it is a support conversation '
                      'rather than a form — write to support@owjar.co if you '
                      'need to move it.',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ],
              ),
            ),
    );
  }

  Widget _verifySection() {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Verify this address',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            'Your partner will be invited using this address, so it needs to be '
            'one you can read.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: AppSpacing.lg),
          if (_codeSent) ...[
            TextField(
              key: const Key('email_code_field'),
              controller: _code,
              keyboardType: TextInputType.number,
              maxLength: 6,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              decoration: InputDecoration(
                labelText: 'Six-digit code',
                counterText: '',
                filled: true,
                fillColor: Colors.white,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(AppRadii.md),
                ),
              ),
              onSubmitted: (_) => _confirm(),
            ),
            const SizedBox(height: AppSpacing.md),
            _PrimaryButton(
              key: const Key('email_confirm_button'),
              label: 'Verify',
              busy: _busy,
              onPressed: _confirm,
            ),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton(
                key: const Key('email_resend_button'),
                onPressed: _busy ? null : _send,
                child: const Text('Send another code'),
              ),
            ),
          ] else
            _PrimaryButton(
              key: const Key('email_send_button'),
              label: 'Send me a code',
              busy: _busy,
              onPressed: _send,
            ),
        ],
      ),
    );
  }

  Widget _changeSection() {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Wrong address?', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: AppSpacing.xs),
          Text(
            'You can change it until it is verified.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: AppSpacing.lg),
          TextField(
            key: const Key('email_new_field'),
            controller: _newEmail,
            keyboardType: TextInputType.emailAddress,
            autocorrect: false,
            decoration: InputDecoration(
              labelText: 'New email address',
              filled: true,
              fillColor: Colors.white,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppRadii.md),
              ),
            ),
            onSubmitted: (_) => _change(),
          ),
          const SizedBox(height: AppSpacing.md),
          _PrimaryButton(
            key: const Key('email_change_button'),
            label: 'Use this address',
            busy: _busy,
            onPressed: _change,
          ),
        ],
      ),
    );
  }
}

class _CurrentAddress extends StatelessWidget {
  final String email;
  final bool verified;
  const _CurrentAddress({required this.email, required this.verified});

  @override
  Widget build(BuildContext context) {
    final tone = verified ? AppColors.seenTick : AppColors.noticeInk;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(email, style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 2),
        Row(
          children: [
            Icon(
              verified ? Icons.verified_rounded : Icons.error_outline_rounded,
              size: 15,
              color: tone,
            ),
            const SizedBox(width: AppSpacing.xs),
            Text(
              verified ? 'Verified' : 'Not verified yet',
              style: Theme.of(
                context,
              ).textTheme.labelMedium?.copyWith(color: tone),
            ),
          ],
        ),
      ],
    );
  }
}

class _Message extends StatelessWidget {
  final String text;
  final bool isError;
  const _Message({required this.text, required this.isError});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: isError
            ? AppColors.error.withValues(alpha: 0.1)
            : AppColors.calmSurface,
        borderRadius: BorderRadius.circular(AppRadii.md),
      ),
      child: Text(
        text,
        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
          color: isError ? AppColors.error : AppColors.softCharcoal,
        ),
      ),
    );
  }
}

class _PrimaryButton extends StatelessWidget {
  final String label;
  final bool busy;
  final VoidCallback onPressed;

  const _PrimaryButton({
    required this.label,
    required this.busy,
    required this.onPressed,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: busy ? null : onPressed,
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.warmCoral,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(vertical: AppSpacing.lg),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadii.lg),
          ),
        ),
        child: Text(busy ? 'Working…' : label),
      ),
    );
  }
}
