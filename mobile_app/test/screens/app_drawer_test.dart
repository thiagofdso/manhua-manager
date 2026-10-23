import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/controllers/manhua_controller.dart';
import 'package:mobile_app/models/manhua.dart';
import 'package:mobile_app/screens/widgets/active_downloads_dialog.dart';
import 'package:mobile_app/screens/widgets/app_drawer.dart';
import 'package:mobile_app/screens/widgets/storage_management_dialog.dart';
import 'package:mobile_app/screens/widgets/settings_dialog.dart';
import 'package:mobile_app/services/api_service.dart';
import 'package:mobile_app/services/download_manager.dart';
import 'package:mobile_app/services/download_service.dart';
import 'package:mobile_app/services/storage_service.dart';
import 'package:provider/provider.dart';

class FakeStorageService extends StorageService {
  @override
  Future<String> getBaseUrl() async => 'http://127.0.0.1:5000';
  @override
  Future<List<Manhua>> loadOfflineManhuas() async => [];
}

class FakeApiService extends ApiService {
  FakeApiService() : super(storageService: FakeStorageService());
  @override
  Future<List<Manhua>> fetchManhuas() async => [];
}

class FakeDownloadService extends DownloadService {
  @override
  Future<int> getTotalDownloadedCount() async => 5;
}

void main() {
  late DownloadManager downloadManager;
  late ManhuaController controller;
  late FakeDownloadService downloadService;

  setUp(() {
    downloadManager = DownloadManager();
    downloadService = FakeDownloadService();
    controller = ManhuaController(
      apiService: FakeApiService(),
      storageService: FakeStorageService(),
    );
  });

  Widget createTestWidget({
    VoidCallback? onEnterEditOrder,
    VoidCallback? onRefresh,
  }) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<DownloadManager>.value(value: downloadManager),
        ChangeNotifierProvider<ManhuaController>.value(value: controller),
      ],
      child: MaterialApp(
        home: Scaffold(
          drawer: AppDrawer(
            onEnterEditOrder: onEnterEditOrder,
            onRefresh: onRefresh,
            downloadManager: downloadManager,
            downloadService: downloadService,
          ),
          body: Builder(
            builder: (ctx) => ElevatedButton(
              onPressed: () => Scaffold.of(ctx).openDrawer(),
              child: const Text('Abrir Drawer'),
            ),
          ),
        ),
      ),
    );
  }

  testWidgets('AppDrawer exibe todos os itens de navegacao e executa callbacks', (tester) async {
    bool editOrderCalled = false;
    bool refreshCalled = false;

    await tester.pumpWidget(
      createTestWidget(
        onEnterEditOrder: () => editOrderCalled = true,
        onRefresh: () => refreshCalled = true,
      ),
    );
    await tester.pumpAndSettle();

    // Abrir o Drawer
    await tester.tap(find.text('Abrir Drawer'));
    await tester.pumpAndSettle();

    expect(find.text('Manhua Manager'), findsOneWidget);
    expect(find.text('Downloads em Andamento'), findsOneWidget);
    expect(find.text('Armazenamento Offline'), findsOneWidget);
    expect(find.text('Importar Obras'), findsOneWidget);
    expect(find.text('Organizar Obras'), findsOneWidget);
    expect(find.text('Configurações'), findsOneWidget);
    expect(find.text('Atualizar Lista'), findsOneWidget);

    // Clicar em Organizar Obras
    await tester.tap(find.text('Organizar Obras'));
    await tester.pumpAndSettle();
    expect(editOrderCalled, isTrue);

    // Reabrir o Drawer e clicar em Atualizar Lista
    await tester.tap(find.text('Abrir Drawer'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Atualizar Lista'));
    await tester.pumpAndSettle();
    expect(refreshCalled, isTrue);
  });

  testWidgets('AppDrawer abre ActiveDownloadsDialog ao clicar em Downloads', (tester) async {
    await tester.pumpWidget(createTestWidget());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Abrir Drawer'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Downloads em Andamento'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.byType(ActiveDownloadsDialog), findsOneWidget);
  });

  testWidgets('AppDrawer abre StorageManagementDialog ao clicar em Armazenamento Offline', (tester) async {
    await tester.pumpWidget(createTestWidget());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Abrir Drawer'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Armazenamento Offline'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.byType(StorageManagementDialog), findsOneWidget);
  });
}
