import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:mobile_app/controllers/manhua_controller.dart';
import 'package:mobile_app/models/manhua.dart';
import 'package:mobile_app/services/api_service.dart';
import 'package:mobile_app/services/storage_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('ManhuaController carrega obras do cache quando API falha', () async {
    SharedPreferences.setMockInitialValues({});
    final storage = StorageService();
    final cachedList = [
      Manhua(id: 1, title: 'Solo Leveling', urlTemplate: 'https://test/{chapter}', currentChapter: 10),
    ];
    await storage.saveCachedManhuas(cachedList);

    // Mock client retornando erro 500
    final mockClient = MockClient((request) async {
      return http.Response('Server error', 500);
    });
    final api = ApiService(client: mockClient, storageService: storage);

    final controller = ManhuaController(apiService: api, storageService: storage);
    await controller.loadManhuas();

    expect(controller.isOfflineMode, isTrue);
    expect(controller.manhuas.length, 1);
    expect(controller.manhuas.first.title, 'Solo Leveling');
    expect(controller.errorMessage, isNull);
  });

  test('ManhuaController carrega cache instantaneamente antes da resposta da API', () async {
    SharedPreferences.setMockInitialValues({});
    final storage = StorageService();
    final cachedList = [
      Manhua(id: 1, title: 'Solo Leveling', urlTemplate: 'https://test/{chapter}', currentChapter: 10),
    ];
    await storage.saveCachedManhuas(cachedList);

    final mockClient = MockClient((request) async {
      await Future.delayed(const Duration(milliseconds: 60));
      return http.Response('[]', 200);
    });
    final api = ApiService(client: mockClient, storageService: storage);
    final controller = ManhuaController(apiService: api, storageService: storage);

    final loadFuture = controller.loadManhuas();
    // Após aguardar um pequeno instante (para leitura assíncrona do cache), o cache já deve estar em _manhuas
    await Future.delayed(const Duration(milliseconds: 10));
    expect(controller.manhuas.length, 1);
    expect(controller.manhuas.first.title, 'Solo Leveling');

    await loadFuture;
  });
}
