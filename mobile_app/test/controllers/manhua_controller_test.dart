import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/controllers/manhua_controller.dart';
import 'package:mobile_app/models/manhua.dart';
import 'package:mobile_app/services/api_service.dart';
import 'package:mobile_app/services/storage_service.dart';

class FakeStorageService extends StorageService {
  String url = 'http://100.84.57.79:5000';
  List<Manhua> cached = [];

  @override
  Future<String> getBaseUrl() async => url;

  @override
  Future<void> setBaseUrl(String newUrl) async {
    url = newUrl;
  }

  @override
  Future<void> saveCachedManhuas(List<Manhua> manhuas) async {
    cached = List.from(manhuas);
  }

  @override
  Future<List<Manhua>> getCachedManhuas() async => cached;
}

class FakeApiService extends ApiService {
  final List<Manhua> items = [
    Manhua(
      id: 1,
      title: 'Overgeared',
      urlTemplate: 'https://asurascans.com/comics/overgeared-11fe7da3/chapter/{chapter}',
      currentChapter: 203,
    )
  ];

  @override
  Future<List<Manhua>> fetchManhuas() async {
    return List.from(items);
  }

  @override
  Future<Manhua> updateChapterDelta(int id, int delta) async {
    final idx = items.indexWhere((m) => m.id == id);
    final updated = items[idx].copyWith(currentChapter: items[idx].currentChapter + delta);
    items[idx] = updated;
    return updated;
  }

  @override
  Future<Manhua> addManhua(
    String title,
    String urlTemplate,
    int currentChapter, {
    int? lastChapter,
    int? updateDay,
    bool isHiatus = false,
  }) async {
    final newItem = Manhua(
      id: items.length + 1,
      title: title,
      urlTemplate: urlTemplate,
      currentChapter: currentChapter,
      lastChapter: lastChapter,
      updateDay: updateDay,
      isHiatus: isHiatus,
    );
    items.add(newItem);
    return newItem;
  }

  @override
  Future<List<Map<String, dynamic>>> fetchNotifications() async {
    return [];
  }

  @override
  Future<void> deleteManhua(int id) async {
    items.removeWhere((m) => m.id == id);
  }

  @override
  Future<Manhua> toggleFavorite(int id, bool isFavorite) async {
    final idx = items.indexWhere((m) => m.id == id);
    final updated = items[idx].copyWith(isFavorite: isFavorite);
    items[idx] = updated;
    return updated;
  }

  @override
  Future<void> reorderManhuas(List<int> orderedIds) async {
    final map = {for (var m in items) m.id: m};
    items.clear();
    for (var id in orderedIds) {
      if (map.containsKey(id)) {
        items.add(map[id]!);
      }
    }
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  group('ManhuaController Test', () {
    test('loadManhuas deve carregar lista no controller', () async {
      final fakeApi = FakeApiService();
      final fakeStorage = FakeStorageService();
      final controller = ManhuaController(apiService: fakeApi, storageService: fakeStorage);

      expect(controller.isLoading, false);
      final future = controller.loadManhuas();
      expect(controller.isLoading, true);
      await future;
      expect(controller.isLoading, false);
      expect(controller.manhuas.length, 1);
      expect(controller.manhuas.first.title, 'Overgeared');
    });

    test('changeChapterDelta deve atualizar o capítulo no controller', () async {
      final fakeApi = FakeApiService();
      final fakeStorage = FakeStorageService();
      final controller = ManhuaController(apiService: fakeApi, storageService: fakeStorage);

      await controller.loadManhuas();
      await controller.changeChapterDelta(1, 1);
      expect(controller.manhuas.first.currentChapter, 204);
    });

    test('addManhua deve incluir nova obra na lista', () async {
      final fakeApi = FakeApiService();
      final fakeStorage = FakeStorageService();
      final controller = ManhuaController(apiService: fakeApi, storageService: fakeStorage);

      await controller.loadManhuas();
      await controller.addManhua('Solo Leveling', 'https://ex.com/{chapter}', 10);
      expect(controller.manhuas.length, 2);
      expect(controller.manhuas.last.title, 'Solo Leveling');
    });

    test('deleteManhua deve remover obra da lista', () async {
      final fakeApi = FakeApiService();
      final fakeStorage = FakeStorageService();
      final controller = ManhuaController(apiService: fakeApi, storageService: fakeStorage);

      await controller.loadManhuas();
      await controller.deleteManhua(1);
      expect(controller.manhuas.isEmpty, true);
    });

    test('toggleFavorite deve alternar favorito e recarregar lista', () async {
      final fakeApi = FakeApiService();
      final fakeStorage = FakeStorageService();
      final controller = ManhuaController(apiService: fakeApi, storageService: fakeStorage);

      await controller.loadManhuas();
      expect(controller.manhuas.first.isFavorite, false);

      await controller.toggleFavorite(1);
      expect(controller.manhuas.first.isFavorite, true);
    });

    test('saveReorder deve salvar nova ordem e atualizar lista', () async {
      final fakeApi = FakeApiService();
      fakeApi.items.add(Manhua(id: 2, title: 'Item 2', urlTemplate: 'http://ex/{chapter}', currentChapter: 1));
      final fakeStorage = FakeStorageService();
      final controller = ManhuaController(apiService: fakeApi, storageService: fakeStorage);

      await controller.loadManhuas();
      expect(controller.manhuas.map((m) => m.id).toList(), [1, 2]);

      await controller.saveReorder([2, 1]);
      expect(controller.manhuas.map((m) => m.id).toList(), [2, 1]);
    });
  });
}
