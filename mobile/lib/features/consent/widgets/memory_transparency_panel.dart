import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/consent/viewmodels/consent_viewmodel.dart';
import 'package:mobile/features/consent/models/memory_model.dart';

// ---------------------------------------------------------------------------
// Memory type badge colors (REL-89)
// ---------------------------------------------------------------------------

extension MemoryTypeColor on MemoryType {
  Color get badgeColor {
    switch (this) {
      case MemoryType.communicationStyle:
        return const Color(0xFF6366F1); // indigo
      case MemoryType.trigger:
        return const Color(0xFFEF4444); // red
      case MemoryType.conflictPattern:
        return const Color(0xFFF97316); // orange
      case MemoryType.repairEvent:
        return const Color(0xFF22C55E); // green
      case MemoryType.statedNeed:
        return const Color(0xFF3B82F6); // blue
      case MemoryType.unknown:
        return const Color(0xFF9CA3AF); // gray
    }
  }
}

// ---------------------------------------------------------------------------
// MemoryTransparencyPanel
// ---------------------------------------------------------------------------

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
  MemoryType? _selectedType; // null = show all types
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
            final matchesSearch = _searchQuery.isEmpty ||
                m.title.toLowerCase().contains(_searchQuery.toLowerCase()) ||
                m.whyStored.toLowerCase().contains(_searchQuery.toLowerCase());
            final matchesType =
                _selectedType == null || m.memoryType == _selectedType;
            return matchesZone && matchesSearch && matchesType;
          }).toList();

          return Column(
            children: [
              // Search bar
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
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

              // Zone selector
              _buildZoneSelector(),

              // Memory type filter (REL-89)
              _buildTypeFilter(),

              // Memory list
              Expanded(
                child: filteredMemories.isEmpty
                    ? _buildEmptyState()
                    : ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: filteredMemories.length,
                        itemBuilder: (context, index) {
                          return _buildMemoryItem(
                              context, vm, filteredMemories[index]);
                        },
                      ),
              ),
            ],
          );
        },
      ),
    );
  }

  // -------------------------------------------------------------------------
  // Zone selector
  // -------------------------------------------------------------------------

  Widget _buildZoneSelector() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
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

  // -------------------------------------------------------------------------
  // Memory type filter (REL-89)
  // -------------------------------------------------------------------------

  Widget _buildTypeFilter() {
    final types = [null, ...MemoryType.values.where((t) => t != MemoryType.unknown)];
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 4),
      child: SizedBox(
        height: 34,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: types.length,
          separatorBuilder: (_, _) => const SizedBox(width: 6),
          itemBuilder: (context, index) {
            final type = types[index];
            final isSelected = _selectedType == type;
            final label = type == null ? 'All' : type.label;
            final color = type == null ? AppColors.calmTeal : type.badgeColor;

            return GestureDetector(
              onTap: () => setState(() => _selectedType = type),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                decoration: BoxDecoration(
                  color: isSelected ? color : color.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: isSelected ? color : color.withValues(alpha: 0.4),
                  ),
                ),
                child: Text(
                  label,
                  style: TextStyle(
                    color: isSelected ? Colors.white : color,
                    fontWeight: FontWeight.w600,
                    fontSize: 11,
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  // -------------------------------------------------------------------------
  // Memory item card
  // -------------------------------------------------------------------------

  Widget _buildMemoryItem(
      BuildContext context, ConsentViewModel vm, MemoryModel memory) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Badges row
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    _buildZoneBadge(memory.zone),
                    const SizedBox(width: 6),
                    // REL-89: memory type badge
                    if (memory.memoryType != MemoryType.unknown)
                      _buildTypeBadge(memory.memoryType),
                  ],
                ),
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
              style: TextStyle(
                  fontSize: 13,
                  color: Colors.grey[600],
                  fontStyle: FontStyle.italic),
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
                  onPressed: () =>
                      _showDeleteConfirmation(context, vm, memory),
                  icon: const Icon(Icons.delete_outline,
                      size: 16, color: Colors.red),
                  label: const Text('Delete',
                      style: TextStyle(color: Colors.red)),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // -------------------------------------------------------------------------
  // Badge widgets
  // -------------------------------------------------------------------------

  Widget _buildZoneBadge(MemoryZone zone) {
    Color color;
    switch (zone) {
      case MemoryZone.private:
        color = AppColors.calmTeal;
        break;
      case MemoryZone.shared:
        color = Colors.green;
        break;
      case MemoryZone.therapist:
        color = Colors.orange;
        break;
    }
    return _badge(zone.label, color);
  }

  Widget _buildTypeBadge(MemoryType type) {
    return _badge(type.label, type.badgeColor);
  }

  Widget _badge(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        label.toUpperCase(),
        style:
            TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.bold),
      ),
    );
  }

  // -------------------------------------------------------------------------
  // Empty state
  // -------------------------------------------------------------------------

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.inventory_2_outlined, size: 64, color: Colors.grey[300]),
          const SizedBox(height: 16),
          Text(
            'No memories found',
            style: TextStyle(
                color: Colors.grey[500],
                fontSize: 16,
                fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 4),
          Text(
            _selectedType != null
                ? 'No ${_selectedType!.label.toLowerCase()} memories in this zone'
                : 'No memories found in this zone',
            style: TextStyle(color: Colors.grey[400], fontSize: 13),
          ),
        ],
      ),
    );
  }

  // -------------------------------------------------------------------------
  // Edit / Delete dialogs
  // -------------------------------------------------------------------------

  void _showEditDialog(
      BuildContext context, ConsentViewModel vm, MemoryModel memory) {
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
          TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel')),
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

  void _showDeleteConfirmation(
      BuildContext context, ConsentViewModel vm, MemoryModel memory) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete memory?'),
        content: const Text(
          'This action cannot be undone. RelationshipAI will no longer factor this pattern into your insights.',
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Keep it')),
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
