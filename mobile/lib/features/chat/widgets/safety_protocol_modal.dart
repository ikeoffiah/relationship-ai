import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

class SafetyProtocolModal extends StatelessWidget {
  final String level;
  final List<Map> resources;

  const SafetyProtocolModal({super.key, required this.level, required this.resources});

  Future<void> _launchResource(Map resource) async {
    final phone = resource['phone'];
    final url = resource['url'];

    if (phone != null) {
      final Uri uri = Uri(scheme: 'tel', path: phone.toString());
      if (await canLaunchUrl(uri)) await launchUrl(uri);
    } else if (url != null) {
      final Uri uri = Uri.parse(url.toString());
      if (await canLaunchUrl(uri)) await launchUrl(uri, mode: LaunchMode.inAppBrowserView);
    }
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      child: Scaffold(
        backgroundColor: Colors.amber.shade50,
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              children: [
                const Icon(Icons.favorite, color: Colors.red, size: 48),
                const SizedBox(height: 16),
                const Text(
                  'We want to make sure you\'re supported',
                  style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                const Text(
                  'It sounds like you\'re going through something really difficult. '
                  'Here are some resources that can provide immediate support:',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 24),
                Expanded(
                  child: ListView.builder(
                    itemCount: resources.length,
                    itemBuilder: (context, index) {
                      final r = resources[index];
                      return Card(
                        margin: const EdgeInsets.symmetric(vertical: 8),
                        child: ListTile(
                          title: Text(r['name'] ?? 'Support Resource'),
                          subtitle: Text(r['description'] ?? ''),
                          trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                          onTap: () => _launchResource(r),
                        ),
                      );
                    },
                  ),
                ),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('I\'ve noted these resources'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
