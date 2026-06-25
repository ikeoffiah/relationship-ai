import 'relay_api_service.dart';
import 'relay_models.dart';
import 'package:flutter/foundation.dart';

class RelayViewModel extends ChangeNotifier {
  final RelayApiService _api;

  RelayViewModel({
    required String baseUrl,
    required String authToken,
  }) : _api = RelayApiService(baseUrl: baseUrl, authToken: authToken);

  // Placeholder session ID for demo – replace with actual session context.
  static const String _defaultSessionId = 'default';

  Future<RelayPreviewResponse> preview(RelayMessage message) async {
    return await _api.previewRelay(_defaultSessionId, message);
  }

  Future<void> send(RelayMessage message) async {
    await _api.sendRelay(_defaultSessionId, message);
  }
}
