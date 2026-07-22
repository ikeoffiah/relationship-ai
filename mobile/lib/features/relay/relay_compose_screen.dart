import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/relay/relay_viewmodel.dart';

/// Compose an async relay to your partner. The message is NVC-translated
/// server-side on send; the recipient chooses which version to read.
class RelayComposeScreen extends StatefulWidget {
  const RelayComposeScreen({super.key});

  @override
  State<RelayComposeScreen> createState() => _RelayComposeScreenState();
}

class _RelayComposeScreenState extends State<RelayComposeScreen> {
  final TextEditingController _controller = TextEditingController();
  bool _consent = false;
  bool _isSending = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final content = _controller.text.trim();
    if (content.isEmpty || !_consent) return;

    setState(() => _isSending = true);
    final status = await context.read<RelayViewModel>().send(
          content,
          consent: _consent,
        );
    if (!mounted) return;
    setState(() => _isSending = false);

    if (status != null) {
      final msg = status == 'processing'
          ? 'Relay sent — it\'s being reviewed for tone before delivery.'
          : 'Relay sent to your partner.';
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(msg)));
      Navigator.pop(context);
    } else {
      final err = context.read<RelayViewModel>().error ?? 'Send failed';
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(err)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final canSend = _controller.text.trim().isNotEmpty && _consent && !_isSending;
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Compose Relay',
            style: TextStyle(color: AppColors.softCharcoal)),
        backgroundColor: Colors.transparent,
        elevation: 0,
        iconTheme: const IconThemeData(color: AppColors.softCharcoal),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _controller,
              maxLines: 6,
              onChanged: (_) => setState(() {}),
              decoration: const InputDecoration(
                labelText: 'Your message',
                hintText: 'Say what\'s on your mind — we\'ll help phrase it.',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            CheckboxListTile(
              value: _consent,
              onChanged: (v) => setState(() => _consent = v ?? false),
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              activeColor: AppColors.warmCoral,
              title: const Text(
                'I consent to my partner receiving an AI-assisted version of '
                'this message.',
                style: TextStyle(fontSize: 13),
              ),
            ),
            const Spacer(),
            ElevatedButton(
              onPressed: canSend ? _send : null,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.warmCoral,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12)),
              ),
              child: _isSending
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : const Text('Send relay',
                      style: TextStyle(color: Colors.white)),
            ),
          ],
        ),
      ),
    );
  }
}
