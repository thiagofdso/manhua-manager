import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/controllers/manhua_controller.dart';
import 'package:mobile_app/models/manhua.dart';
import 'package:mobile_app/screens/home_screen.dart';
import 'package:mobile_app/screens/reader_screen.dart';
import 'package:mobile_app/services/api_service.dart';
import 'package:mobile_app/services/storage_service.dart';
import 'package:provider/provider.dart';

class FakeStorageService extends StorageService {
  @override
  Future<String> getBaseUrl() async => 'http://100.84.57.79:5000';
  @override
  Future<List<Manhua>> getCachedManhuas() async => [];
  @override
  Future<void> saveCachedManhuas(List<Manhua> manhuas) async {}
}

class FakeApiService extends ApiService {
  final List<Manhua> items = [
    Manhua(
      id: 1,
      title: 'Overgeared',
      urlTemplate: 'https://asurascans.com/comics/overgeared-11fe7da3/chapter/{chapter}',
      currentChapter: 203,
    ),
  ];

  @override
  Future<List<Manhua>> fetchManhuas() async => List.from(items);

  @override
  Future<List<String>> fetchChapterImages(String targetUrl) async {
    return ['https://cdn.com/page1.webp', 'https://cdn.com/page2.webp'];
  }

  @override
  Future<String> getProxyImageUrl(String imageUrl) async => imageUrl;

  @override
  Future<Manhua> updateChapterDelta(int id, int delta) async {
    final idx = items.indexWhere((m) => m.id == id);
    final updated = items[idx].copyWith(currentChapter: items[idx].currentChapter + delta);
    items[idx] = updated;
    return updated;
  }
}

void main() {
  Widget createTestApp(Widget child, ManhuaController controller) {
    return ChangeNotifierProvider<ManhuaController>.value(
      value: controller,
      child: MaterialApp(home: child),
    );
  }

  testWidgets('HomeScreen deve exibir lista de obras e botoes', (tester) async {
    final api = FakeApiService();
    final storage = FakeStorageService();
    final controller = ManhuaController(apiService: api, storageService: storage);

    await tester.pumpWidget(createTestApp(const HomeScreen(), controller));
    await tester.pumpAndSettle();

    expect(find.text('Manhua Manager'), findsOneWidget);
    expect(find.text('Overgeared'), findsOneWidget);
    expect(find.text('Capítulo 203'), findsOneWidget);
    expect(find.byIcon(Icons.visibility), findsOneWidget);
    expect(find.byIcon(Icons.add_circle_outline), findsOneWidget);
    expect(find.byIcon(Icons.remove_circle_outline), findsOneWidget);
  });

  testWidgets('ReaderScreen deve carregar e responder a gesto de swipe', (tester) async {
    final api = FakeApiService();
    final storage = FakeStorageService();
    final controller = ManhuaController(apiService: api, storageService: storage);

    final manhua = api.items.first;

    await tester.pumpWidget(createTestApp(ReaderScreen(manhua: manhua), controller));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));

    expect(find.text('Overgeared 203'), findsOneWidget);
    expect(find.text('Anterior'), findsOneWidget);
    expect(find.text('Próximo'), findsOneWidget);

    // Simula arrastar com velocidade (fling/swipe para a esquerda) -> avança para capítulo 204
    await tester.fling(find.byKey(const Key('reader_gesture_detector')), const Offset(-500.0, 0.0), 1000.0);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));

    expect(find.text('Overgeared 204'), findsOneWidget);
  });
}
