import 'dart:convert';
import 'package:http/http.dart' as http;
import 'relay_models.dart';

class RelayApiService {
  final String baseUrl;
  final String authToken;

  RelayApiService({required this.baseUrl, required this.authToken});

  Future<RelayPreviewResponse> previewRelay(String sessionId, RelayMessage message) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/sessions/$sessionId/relay/preview'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $authToken',
      },
      body: jsonEncode(message.toJson()),
    );
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return RelayPreviewResponse.fromJson(data);
    }
    throw Exception('Failed to preview relay');
  }

  Future<String> sendRelay(String sessionId, RelayMessage message) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/sessions/$sessionId/relay'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $authToken',
      },
      body: jsonEncode(message.toJson()),
    );
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data['relay_id'] as String;
    }
    throw Exception('Failed to send relay');
  }

  Future<List<dynamic>> fetchInbox(String userId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/v1/users/$userId/relay/inbox'),
      headers: {'Authorization': 'Bearer $authToken'},
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as List<dynamic>;
    }
    throw Exception('Failed to fetch inbox');
  }

  Future<List<dynamic>> fetchSent(String userId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/v1/users/$userId/relay/sent'),
      headers: {'Authorization': 'Bearer $authToken'},
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as List<dynamic>;
    }
    throw Exception('Failed to fetch sent messages');
  }

  Future<void> markAsRead(String sessionId, String relayId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/sessions/$sessionId/relay/$relayId/read'),
      headers: {'Authorization': 'Bearer $authToken'},
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to mark as read');
    }
  }
}
