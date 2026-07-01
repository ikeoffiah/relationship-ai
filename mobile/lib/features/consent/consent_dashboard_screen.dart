import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/consent/viewmodels/consent_viewmodel.dart';
import 'package:mobile/features/consent/models/memory_model.dart';
import 'package:mobile/features/consent/widgets/memory_transparency_panel.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/shared/widgets/get_help_now_button.dart';

class ConsentDashboardScreen extends StatefulWidget {
  const ConsentDashboardScreen({super.key});

  @override
  State<ConsentDashboardScreen> createState() => _ConsentDashboardScreenState();
}

class _ConsentDashboardScreenState extends State<ConsentDashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _refreshData();
    });
  }

  Future<void> _refreshData() async {
    final consentVM = context.read<ConsentViewModel>();
    await Future.wait([
      consentVM.fetchConsent(),
      consentVM.fetchMemories(),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.creamWhite,
      appBar: AppBar(
        title: const Text('Privacy & Consent'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: true,
      ),
      body: Consumer<ConsentViewModel>(
        builder: (context, vm, child) {
          if (vm.isLoading && vm.consent == null) {
            return const Center(child: CircularProgressIndicator());
          }

          if (vm.consent == null) {
            return _buildErrorState();
          }

          return RefreshIndicator(
            onRefresh: _refreshData,
            color: AppColors.warmCoral,
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                const GetHelpNowButton(),
                const SizedBox(height: 16),
                if (context.read<AuthViewModel>().isMinor)
                  _buildMinorSafetyBanner(),
                _buildSectionHeader('What\'s stored about you', 'Your memory zones and item counts'),
                _buildMemoryZones(vm),
                const SizedBox(height: 32),
                _buildSectionHeader('What\'s shared with your partner', 'Permissions and visibility controls'),
                _buildConsentPermissions(vm),
                const SizedBox(height: 32),
                if (vm.consent!.therapistSummaryAccess) ...[
                  _buildSectionHeader('What your therapist can see', 'Summary of therapist-visible data'),
                  _buildTherapistVisibilityCard(vm),
                  const SizedBox(height: 32),
                ],
                const SizedBox(height: 100), // Extra space for FAB
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildSectionHeader(String title, String subtitle) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppColors.softCharcoal),
        ),
        const SizedBox(height: 4),
        Text(
          subtitle,
          style: TextStyle(fontSize: 14, color: AppColors.softCharcoal.withValues(alpha: 0.6)),
        ),
        const SizedBox(height: 16),
      ],
    );
  }

  Widget _buildMemoryZones(ConsentViewModel vm) {
    return Row(
      children: [
        Expanded(
          child: _buildZoneCard(
            title: 'Private Profile',
            count: vm.privateMemoryCount,
            icon: Icons.lock_outline,
            color: AppColors.calmTeal,
            onTap: () => _openMemoryPanel(MemoryZone.private),
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: _buildZoneCard(
            title: 'Shared Context',
            count: vm.sharedMemoryCount,
            icon: Icons.people_outline,
            color: Colors.green,
            onTap: () => _openMemoryPanel(MemoryZone.shared),
          ),
        ),
      ],
    );
  }

  Widget _buildZoneCard({
    required String title,
    required int count,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(
              color: color.withValues(alpha: 0.05),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 32),
            const SizedBox(height: 12),
            Text(
              '$count items',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: color),
            ),
            const SizedBox(height: 4),
            Text(
              title,
              style: const TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildConsentPermissions(ConsentViewModel vm) {
    final consent = vm.consent!;
    final summary = consent.plainLanguageSummary;

    return Column(
      children: [
        _buildPermissionCard(
          title: 'Session transcript retention',
          description: summary['session_transcript_retention'] ?? '...',
          icon: Icons.history,
          onEdit: () => _showRetentionPicker(vm),
        ),
        _buildPermissionCard(
          title: 'Partner insight sharing',
          description: summary['cross_partner_insight_sharing'] ?? '...',
          icon: Icons.share_outlined,
          onEdit: () => _showInsightPicker(vm),
        ),
        _buildPermissionCard(
          title: 'Shared context access',
          description: summary['shared_relationship_context'] ?? '...',
          icon: Icons.connect_without_contact_outlined,
          onEdit: () => _showContextPicker(vm),
        ),
        _buildPermissionCard(
          title: 'Therapist access',
          description: summary['therapist_summary_access'] ?? '...',
          icon: Icons.medical_services_outlined,
          onEdit: () => vm.updateField('therapist_summary_access', !consent.therapistSummaryAccess),
          isToggle: true,
          toggleValue: consent.therapistSummaryAccess,
        ),
        _buildPermissionCard(
          title: 'Model improvement data',
          description: summary['model_improvement_data'] ?? 'Help improve the AI safely',
          icon: Icons.science_outlined,
          onEdit: () => vm.updateField('model_improvement_data', !consent.modelImprovementData),
          isToggle: true,
          toggleValue: consent.modelImprovementData,
        ),
      ],
    );
  }

  Widget _buildPermissionCard({
    required String title,
    required String description,
    required IconData icon,
    required VoidCallback onEdit,
    bool isToggle = false,
    bool toggleValue = false,
  }) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: ListTile(
        leading: Icon(icon, color: AppColors.warmCoral),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
        subtitle: Text(description, style: const TextStyle(fontSize: 13, color: Colors.grey)),
        trailing: isToggle 
          ? Switch(
              value: toggleValue, 
              onChanged: (_) => onEdit(),
              activeThumbColor: AppColors.warmCoral,
              activeTrackColor: AppColors.warmCoral.withValues(alpha: 0.5),
            )
          : const Icon(Icons.chevron_right, size: 20),
        onTap: isToggle ? null : onEdit,
      ),
    );
  }

  Widget _buildTherapistVisibilityCard(ConsentViewModel vm) {
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: const Padding(
        padding: EdgeInsets.all(20.0),
        child: Column(
          children: [
            Row(
              children: [
                Icon(Icons.visibility_outlined, color: Colors.orange),
                SizedBox(width: 12),
                Text('Visible to Therapist', style: TextStyle(fontWeight: FontWeight.bold)),
              ],
            ),
            SizedBox(height: 12),
            Text(
              'Your therapist can see anonymized summaries of your session patterns but cannot read raw transcripts or private profile items.',
              style: TextStyle(fontSize: 13, color: Colors.grey),
            ),
          ],
        ),
      ),
    );
  }

  void _openMemoryPanel(MemoryZone zone) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => MemoryTransparencyPanel(initialZone: zone)),
    );
  }

  void _showRetentionPicker(ConsentViewModel vm) {
    _showPicker(
      context,
      'Retention Period',
      [
        {'val': 'per_session', 'label': 'Not saved'},
        {'val': '30_days', 'label': 'Saved for 30 days'},
        {'val': '1_year', 'label': 'Saved for 1 year'},
        {'val': 'indefinite', 'label': 'Saved indefinitely'},
      ],
      vm.consent!.sessionTranscriptRetention,
      (val) => vm.updateField('session_transcript_retention', val),
    );
  }

  void _showInsightPicker(ConsentViewModel vm) {
    _showPicker(
      context,
      'Partner Insight Sharing',
      [
        {'val': 'never', 'label': 'Never shared'},
        {'val': 'anonymized', 'label': 'Shared anonymously'},
        {'val': 'named', 'label': 'Shared with name'},
      ],
      vm.consent!.crossPartnerInsightSharing,
      (val) => vm.updateField('cross_partner_insight_sharing', val),
    );
  }

  void _showContextPicker(ConsentViewModel vm) {
    _showPicker(
      context,
      'Shared Context Access',
      [
        {'val': 'not_participating', 'label': 'No shared context'},
        {'val': 'read_only', 'label': 'Partner can see summary'},
        {'val': 'read_write', 'label': 'Both partners share context'},
      ],
      vm.consent!.sharedRelationshipContext,
      (val) => vm.updateField('shared_relationship_context', val),
    );
  }

  void _showPicker(
    BuildContext context, 
    String title, 
    List<Map<String, String>> options, 
    String current,
    Function(String) onSelect,
  ) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (context) => Container(
        padding: const EdgeInsets.symmetric(vertical: 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),
            ...options.map((opt) => ListTile(
              title: Text(opt['label']!),
              trailing: opt['val'] == current ? const Icon(Icons.check, color: AppColors.warmCoral) : null,
              onTap: () {
                onSelect(opt['val']!);
                Navigator.pop(context);
              },
            )),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Text('Unable to load privacy settings'),
          TextButton(onPressed: _refreshData, child: const Text('Retry')),
        ],
      ),
    );
  }

  Widget _buildMinorSafetyBanner() {
    return Container(
      margin: const EdgeInsets.only(bottom: 24),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.warmCoral.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.warmCoral.withValues(alpha: 0.2)),
      ),
      child: Column(
        children: [
          const Row(
            children: [
              Icon(Icons.security, color: AppColors.warmCoral),
              SizedBox(width: 12),
              Text(
                'Guardian Managed Account',
                style: TextStyle(fontWeight: FontWeight.bold, color: AppColors.softCharcoal),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Because you are under 18, some privacy settings are managed in consultation with your guardian. Your safety is our top priority.',
            style: TextStyle(fontSize: 13, color: AppColors.softCharcoal.withValues(alpha: 0.7)),
          ),
        ],
      ),
    );
  }
}
