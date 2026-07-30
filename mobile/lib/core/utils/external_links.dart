import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

/// Canonical external links for the app's legal / support surfaces, plus a
/// small helper to open them. Centralized so the URLs live in one place.
class AppLinks {
  // The legal documents live in the app now (see settings/legal_documents.dart)
  // rather than behind these links, which pointed at relationshipai.com — the
  // project's code name, never the company. Bliss is a product of owjar.co.
  static const supportEmail = 'support@owjar.co';

  /// A pre-filled feedback email.
  static Uri feedbackMailto() => Uri(
        scheme: 'mailto',
        path: supportEmail,
        query: 'subject=${Uri.encodeComponent('Bliss feedback')}',
      );
}

/// Opens [url] in the external browser/app. Shows a gentle snackbar if nothing
/// can handle it, so a dead link never fails silently.
Future<void> openExternal(BuildContext context, Uri url) async {
  final messenger = ScaffoldMessenger.of(context);
  try {
    final ok = await launchUrl(url, mode: LaunchMode.externalApplication);
    if (!ok && context.mounted) {
      messenger.showSnackBar(const SnackBar(content: Text('Couldn\'t open the link.')));
    }
  } catch (_) {
    if (context.mounted) {
      messenger.showSnackBar(const SnackBar(content: Text('Couldn\'t open the link.')));
    }
  }
}

/// Convenience for a plain https URL string.
Future<void> openUrl(BuildContext context, String url) =>
    openExternal(context, Uri.parse(url));
