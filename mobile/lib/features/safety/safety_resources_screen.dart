import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'safety_resources_data.dart';

class SafetyResourcesScreen extends StatelessWidget {
  const SafetyResourcesScreen({super.key});

  Future<void> _launchResource(SafetyResource resource) async {
    if (resource.phoneNumber != null && resource.chatUrl == null && resource.textNumber == null) {
      // Phone call
      final Uri uri = Uri(scheme: 'tel', path: resource.phoneNumber);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri);
      }
    } else if (resource.textNumber != null) {
      // SMS
      final Uri uri = Uri(
        scheme: 'sms',
        path: resource.textNumber,
        queryParameters: {'body': resource.textKeyword ?? ''},
      );
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri);
      }
    } else if (resource.chatUrl != null) {
      // Web chat
      final Uri uri = Uri.parse(resource.chatUrl!);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.inAppBrowserView);
      }
    }
  }

  Widget _buildResourceCard(SafetyResource resource) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 16.0),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${resource.category == 'DomesticViolence' ? '🏠' : resource.category == 'Emergency' ? '🚨' : '💬'} ${resource.name}',
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            if (resource.description != null) ...[
              Text(resource.description!),
              const SizedBox(height: 4),
            ],
            Text('Available: ${resource.available}'),
            const SizedBox(height: 12),
            Row(
              children: [
                if (resource.phoneNumber != null) ...[
                  ElevatedButton.icon(
                    icon: const Icon(Icons.phone),
                    label: Text(resource.category == 'DomesticViolence' ? 'Call' : 'Call ${resource.phoneNumber}'),
                    onPressed: () => _launchResource(SafetyResource(
                      category: resource.category,
                      name: resource.name,
                      phoneNumber: resource.phoneNumber,
                      available: resource.available,
                    )),
                  ),
                  const SizedBox(width: 8),
                ],
                if (resource.textNumber != null) ...[
                  ElevatedButton.icon(
                    icon: const Icon(Icons.message),
                    label: const Text('Text'),
                    onPressed: () => _launchResource(SafetyResource(
                      category: resource.category,
                      name: resource.name,
                      textNumber: resource.textNumber,
                      textKeyword: resource.textKeyword,
                      available: resource.available,
                    )),
                  ),
                ],
                if (resource.chatUrl != null) ...[
                  ElevatedButton.icon(
                    icon: const Icon(Icons.chat),
                    label: const Text('Chat online'),
                    onPressed: () => _launchResource(SafetyResource(
                      category: resource.category,
                      name: resource.name,
                      chatUrl: resource.chatUrl,
                      available: resource.available,
                    )),
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    // Check if there are arguments passed (e.g., from safety overlay)
    final String? prependedMessage = ModalRoute.of(context)?.settings.arguments as String?;

    return Scaffold(
      appBar: AppBar(
        backgroundColor: const Color(0xFFB71C1C),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: const Row(
          children: [
            Text('Get Help Now', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 24)),
            SizedBox(width: 8),
            Text('🆘', style: TextStyle(fontSize: 24)),
          ],
        ),
      ),
      body: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (prependedMessage != null) ...[
              Container(
                color: Colors.yellow.shade100,
                padding: const EdgeInsets.all(16.0),
                child: Text(
                  prependedMessage,
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
                ),
              ),
            ],
            const Padding(
              padding: EdgeInsets.all(16.0),
              child: Text(
                'If you\'re in immediate danger, please call emergency services:',
                style: TextStyle(fontSize: 18),
              ),
            ),
            ...safetyResources.where((r) => r.category == 'Emergency').map(_buildResourceCard),
            
            const Padding(
              padding: EdgeInsets.fromLTRB(16, 24, 16, 8),
              child: Text(
                'Crisis support',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
            ),
            ...safetyResources.where((r) => r.category == 'Crisis').map(_buildResourceCard),
            
            const Padding(
              padding: EdgeInsets.fromLTRB(16, 24, 16, 8),
              child: Text(
                'Domestic violence & safety',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
            ),
            ...safetyResources.where((r) => r.category == 'DomesticViolence').map(_buildResourceCard),

            const Padding(
              padding: EdgeInsets.fromLTRB(16, 24, 16, 8),
              child: Text(
                'About this app',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
            ),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
              child: Text(
                'RelationshipAI is an AI system, not a licensed therapist. It cannot provide emergency support.',
                style: TextStyle(fontSize: 16),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: ElevatedButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Return to app'),
              ),
            ),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }
}
