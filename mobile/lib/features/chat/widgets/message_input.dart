import 'package:flutter/material.dart';

class MessageInput extends StatefulWidget {
  final bool isSending;
  final bool disabled;
  final ValueChanged<String> onSend;

  /// Optional external controller so a parent can prefill the draft (from a
  /// suggestion or a coach rewrite) and read it back for coaching. When omitted,
  /// the widget manages its own controller as before.
  final TextEditingController? controller;

  /// When provided, a "tune" button appears while there is a draft; tapping it
  /// asks the tone coach to review the current text.
  final VoidCallback? onCoach;

  const MessageInput({
    super.key,
    required this.onSend,
    this.isSending = false,
    this.disabled = false,
    this.controller,
    this.onCoach,
  });

  @override
  State<MessageInput> createState() => _MessageInputState();
}

class _MessageInputState extends State<MessageInput> {
  TextEditingController? _ownController;
  TextEditingController get _controller =>
      widget.controller ?? (_ownController ??= TextEditingController());
  int _charCount = 0;
  static const int _maxChars = 1000;

  @override
  void initState() {
    super.initState();
    _controller.addListener(_onChanged);
    _charCount = _controller.text.length;
  }

  void _onChanged() {
    if (!mounted) return;
    setState(() => _charCount = _controller.text.length);
  }

  @override
  void dispose() {
    _controller.removeListener(_onChanged);
    _ownController?.dispose(); // never dispose a controller we don't own
    super.dispose();
  }

  void _handleSend() {
    if (_controller.text.trim().isNotEmpty && !widget.isSending && !widget.disabled) {
      widget.onSend(_controller.text.trim());
      _controller.clear();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        border: Border(top: BorderSide(color: Colors.grey.shade200)),
      ),
      child: SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    enabled: !widget.disabled,
                    maxLines: 5,
                    minLines: 1,
                    maxLength: _maxChars,
                    textCapitalization: TextCapitalization.sentences,
                    decoration: InputDecoration(
                      hintText: widget.disabled ? 'Please wait...' : 'Type a message...',
                      counterText: '', // Hide default counter
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide(color: Colors.grey.shade300),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide(color: Colors.grey.shade300),
                      ),
                    ),
                  ),
                ),
                if (widget.onCoach != null &&
                    _controller.text.trim().isNotEmpty &&
                    !widget.disabled) ...[
                  const SizedBox(width: 4),
                  IconButton(
                    icon: const Icon(Icons.spa_outlined),
                    color: Theme.of(context).primaryColor,
                    tooltip: 'Check the tone',
                    onPressed: widget.isSending ? null : widget.onCoach,
                  ),
                ],
                const SizedBox(width: 8),
                Container(
                  decoration: BoxDecoration(
                    color: (_controller.text.trim().isEmpty || widget.isSending || widget.disabled)
                        ? Colors.grey.shade300
                        : Theme.of(context).primaryColor,
                    shape: BoxShape.circle,
                  ),
                  child: IconButton(
                    icon: widget.isSending
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                          )
                        : const Icon(Icons.send, color: Colors.white),
                    onPressed: _handleSend,
                  ),
                ),
              ],
            ),
            if (!widget.disabled)
              Padding(
                padding: const EdgeInsets.only(top: 4, right: 48),
                child: Text(
                  '$_charCount/$_maxChars',
                  style: TextStyle(
                    fontSize: 10,
                    color: _charCount >= _maxChars ? Colors.red : Colors.grey,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
