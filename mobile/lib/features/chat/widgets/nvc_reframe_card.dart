import 'package:flutter/material.dart';
import 'package:mobile/features/chat/models/chat_models.dart';

class NVCReframeCard extends StatefulWidget {
  final NVCReframe reframe;
  final ValueChanged<String> onReject;

  const NVCReframeCard({super.key, required this.reframe, required this.onReject});

  @override
  State<NVCReframeCard> createState() => _NVCReframeCardState();
}

class _NVCReframeCardState extends State<NVCReframeCard> {
  bool _showingOriginal = false;
  bool _correcting = false;
  final TextEditingController _correctionController = TextEditingController();

  @override
  void dispose() {
    _correctionController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.blue.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.blue.shade200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.auto_fix_high, size: 14, color: Colors.blue),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  'Reframed to express feelings and needs',
                  style: TextStyle(fontSize: 12, color: Colors.blue.shade700, fontWeight: FontWeight.w500),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(widget.reframe.reframed, style: const TextStyle(fontSize: 15)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              TextButton(
                style: TextButton.styleFrom(
                  minimumSize: Size.zero,
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
                onPressed: () => setState(() => _showingOriginal = !_showingOriginal),
                child: Text(_showingOriginal ? 'Hide original' : 'Show original',
                    style: TextStyle(fontSize: 12, color: Colors.blue.shade600)),
              ),
              TextButton(
                style: TextButton.styleFrom(
                  minimumSize: Size.zero,
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
                onPressed: () => setState(() => _correcting = !_correcting),
                child: Text("This doesn't capture what I meant",
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
              ),
            ],
          ),
          if (_showingOriginal) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(8),
              width: double.infinity,
              decoration: BoxDecoration(
                color: Colors.grey.shade100,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                'Original: ${widget.reframe.original}',
                style: TextStyle(fontSize: 13, color: Colors.grey.shade700, fontStyle: FontStyle.italic),
              ),
            ),
          ],
          if (_correcting) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _correctionController,
                    style: const TextStyle(fontSize: 13),
                    decoration: const InputDecoration(
                      hintText: 'What did you mean?',
                      isDense: true,
                      contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.send, size: 18, color: Colors.blue),
                  onPressed: () {
                    if (_correctionController.text.isNotEmpty) {
                      widget.onReject(_correctionController.text);
                    }
                  },
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
