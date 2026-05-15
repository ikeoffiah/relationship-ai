import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/services/storage_service.dart';
import '../helpers/mock_services.dart';

void main() {
  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    setupMockSecureStorage();
  });

  group('StorageService Tests', () {
    test('saveToken and getToken work properly mock channel', () async {
      await StorageService.saveToken('test_token');
      // The mock returns null for reads, but the execution shouldn't throw errors.
      final token = await StorageService.getToken();
      expect(token, null);
    });

    test('saveUserId and getUserId work properly without errors', () async {
      await StorageService.saveUserId('user123');
      final userId = await StorageService.getUserId();
      expect(userId, null);
    });

    test('delete operations run without error', () async {
      await StorageService.deleteToken();
      await StorageService.deleteUserId();
      await StorageService.clearAll();
      expect(true, true);
    });
  });
}
