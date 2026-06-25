import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'package:mobile/features/relay/relay_models.dart';
import 'package:mobile/features/relay/relay_viewmodel.dart';

class RelayComposeScreen extends StatefulWidget {
  const RelayComposeScreen({super.key});

  @override
  State<RelayComposeScreen> createState() => _RelayComposeScreenState();
}

class _RelayComposeScreenState extends State<RelayComposeScreen> {
  final TextEditingController _controller = TextEditingController();
  String? _previewHtml;
  bool _isLoading = false;

  Future<void> _preview() async {
    final vm = context.read<RelayViewModel>();
    final message = RelayMessage(content: _controller.text);
    if (!mounted) return;
    setState(() => _isLoading = true);
    try {
      final preview = await vm.preview(message);
      if (!mounted) return;
      setState(() => _previewHtml = preview.previewHtml);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Preview failed')));
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _send() async {
    final vm = context.read<RelayViewModel>();
    final message = RelayMessage(content: _controller.text);
    if (!mounted) return;
    setState(() => _isLoading = true);
    try {
      await vm.send(message);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Relay sent')));
        _controller.clear();
        setState(() => _previewHtml = null);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Send failed')));
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Compose Relay')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _controller,
              maxLines: 5,
              decoration: const InputDecoration(
                labelText: 'Message',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            ElevatedButton(onPressed: _isLoading ? null : _preview, child: const Text('Preview')),
            if (_previewHtml != null) ...[
              const SizedBox(height: 12),
              Expanded(
                child: SingleChildScrollView(
                  child: Container(
                    padding: const EdgeInsets.all(8),
                    color: Colors.grey.shade200,
                    child: Text(_previewHtml!),
                  ),
                ),
              ),
            ],
            const SizedBox(height: 12),
            ElevatedButton(onPressed: _isLoading ? null : _send, child: const Text('Send')),
          ],
        ),
      ),
    );
  }
}
