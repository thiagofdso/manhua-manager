import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/controllers/manhua_controller.dart';
import 'package:mobile_app/models/manhua.dart';
import 'package:mobile_app/screens/home_screen.dart';
import 'package:mobile_app/services/api_service.dart';
import 'package:mobile_app/services/storage_service.dart';

class FakeStorageService extends StorageService {
  @override
  Future<String> getBaseUrl() async => 'http://100.84.57.79:5000';
}

class FakeApiService extends ApiService {
  final List<Manhua> items = [
    Manhua(id: 1, title: 'Obra 1', urlTemplate: 'https://ex/{chapter}', currentChapter: 10, isFavorite: true),
    Manhua(id: 2, title: 'Obra 2', urlTemplate: 'https://ex/{chapter}', currentChapter: 20, isFavorite: false),
  ];

  @override
  Future<List<Manhua>> fetchManhuas() async => List.from(items);

  @override
  Future<Manhua> toggleFavorite(int id, bool isFavorite) async {
    final idx = items.indexWhere((m) => m.id == id);
    final updated = items[idx].copyWith(isFavorite: isFavorite);
    items[idx] = updated;
    return updated;
  }

  @override
  Future<void> reorderManhuas(List<int> orderedIds) async {}
}

void main() {
  testWidgets('HomeScreen exibe botão de estrela e permite alternar modo de reordenação', (tester) async {
    final api = FakeApiService();
    final storage = FakeStorageService();
    final controller = ManhuaController(apiService: api, storageService: storage);

    await tester.pumpWidget(
      MaterialApp(
        home: ChangeNotifierProvider<ManhuaController>.value(
          value: controller,
          child: const HomeScreen(),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // Verifica que obras são exibidas com estrelas
    expect(find.text('Obra 1'), findsOneWidget);
    expect(find.text('Obra 2'), findsOneWidget);
    expect(find.byIcon(Icons.star), findsOneWidget);
    expect(find.byIcon(Icons.star_border), findsOneWidget);

    // Botão de editar ordem no AppBar
    final sortBtn = find.byTooltip('Editar Ordem da Lista');
    expect(sortBtn, findsOneWidget);

    // Clica no botão de editar ordem
    await tester.tap(sortBtn);
    await tester.pumpAndSettle();

    // Deve entrar em modo de edição
    expect(find.text('Editar Ordem'), findsOneWidget);
    expect(find.byTooltip('Concluir'), findsOneWidget);
    expect(find.byTooltip('Cancelar'), findsOneWidget);
    expect(find.byIcon(Icons.drag_handle_rounded), findsWidgets);
  });
}
