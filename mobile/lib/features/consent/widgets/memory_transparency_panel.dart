import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/consent/viewmodels/consent_viewmodel.dart';
import 'package:mobile/features/consent/models/memory_model.dart';

class MemoryTransparencyPanel extends StatefulWidget {
  final MemoryZone initialZone;

  const MemoryTransparencyPanel({
    super.key,
    this.initialZone = MemoryZone.private,
  });

  @override
  State<MemoryTransparencyPanel> createState() => _MemoryTransparencyPanelState();
}

class _MemoryTransparencyPanelState extends State<MemoryTransparencyPanel> {
  late MemoryZone _selectedZone;
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    _selectedZone = widget.initialZone;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Memory Transparency'),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: Consumer<ConsentViewModel>(
        builder: (context, vm, child) {
          final filteredMemories = vm.memories.where((m) {
            final matchesZone = m.zone == _selectedZone;
            final matchesSearch = m.title.toLowerCase().contains(_searchQuery.toLowerCase()) ||
                                 m.whyStored.toLowerCase().contains(_searchQuery.toLowerCase());
            return matchesZone && matchesSearch;
          }).toList();

          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.all(16.0),
                child: TextField(
                  onChanged: (val) => setState(() => _searchQuery = val),
                  decoration: InputDecoration(
                    hintText: 'Search memories...',
                    prefixIcon: const Icon(Icons.search),
                    filled: true,
                    fillColor: Colors.white,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: BorderSide.none,
                    ),
                  ),
                ),
              ),
              _buildZoneSelector(),
              Expanded(
                child: filteredMemories.isEmpty
                    ? _buildEmptyState()
                    : ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: filteredMemories.length,
                        itemBuilder: (context, index) {
                          return _buildMemoryItem(context, vm, filteredMemories[index]);
                        },
                      ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildZoneSelector() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16.0),
      child: Row(
        children: [
          _buildZoneTab(MemoryZone.private, AppColors.calmTeal),
          const SizedBox(width: 8),
          _buildZoneTab(MemoryZone.shared, Colors.green),
          const SizedBox(width: 8),
          _buildZoneTab(MemoryZone.therapist, Colors.orange),
        ],
      ),
    );
  }

  Widget _buildZoneTab(MemoryZone zone, Color color) {
    final isSelected = _selectedZone == zone;
    return GestureDetector(
      onTap: () => setState(() => _selectedZone = zone),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? color : color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: color),
        ),
        child: Text(
          zone.label,
          style: TextStyle(
            color: isSelected ? Colors.white : color,
            fontWeight: FontWeight.bold,
            fontSize: 12,
          ),
        ),
      ),
    );
  }

  Widget _buildMemoryItem(BuildContext context, ConsentViewModel vm, MemoryModel memory) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildBadge(memory.zone),
                Text(
                  memory.formattedDate,
                  style: const TextStyle(fontSize: 11, color: Colors.grey),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              memory.title,
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              'Why stored: ${memory.whyStored}',
              style: TextStyle(fontSize: 13, color: Colors.grey[600], fontStyle: FontStyle.italic),
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton.icon(
                  onPressed: () => _showEditDialog(context, vm, memory),
                  icon: const Icon(Icons.edit_outlined, size: 16),
                  label: const Text('Edit'),
                ),
                const SizedBox(width: 8),
                TextButton.icon(
                  onPressed: () => _showDeleteConfirmation(context, vm, memory),
                  icon: const Icon(Icons.delete_outline, size: 16, color: Colors.red),
                  label: const Text('Delete', style: TextStyle(color: Colors.red)),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBadge(MemoryZone zone) {
    Color color;
    switch (zone) {
      case MemoryZone.private: color = AppColors.calmTeal; break;
      case MemoryZone.shared: color = Colors.green; break;
      case MemoryZone.therapist: color = Colors.orange; break;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        zone.label.toUpperCase(),
        style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.bold),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.inventory_2_outlined, size: 64, color: Colors.grey[300]),
          const SizedBox(height: 16),
          Text(
            'No memories found in this zone',
            style: TextStyle(color: Colors.grey[400]),
          ),
        ],
      ),
    );
  }

  void _showEditDialog(BuildContext context, ConsentViewModel vm, MemoryModel memory) {
    final controller = TextEditingController(text: memory.title);
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Edit Memory Content'),
        content: TextField(
          controller: controller,
          maxLines: 5,
          decoration: const InputDecoration(
            hintText: 'Describe this pattern...',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () {
              vm.updateMemory(memory.id, controller.text);
              Navigator.pop(context);
            },
            child: const Text('Save Changes'),
          ),
        ],
      ),
    );
  }

  void _showDeleteConfirmation(BuildContext context, ConsentViewModel vm, MemoryModel memory) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete memory?'),
        content: const Text(
          'This action cannot be undone. RelationshipAI will no longer factor this pattern into your insights.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Keep it')),
          TextButton(
            onPressed: () {
              vm.deleteMemory(memory.id);
              Navigator.pop(context);
            },
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }
}
