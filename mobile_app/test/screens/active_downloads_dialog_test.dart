import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile_app/controllers/manhua_controller.dart';
import 'package:mobile_app/models/manhua.dart';
import 'package:mobile_app/screens/home_screen.dart';
import 'package:mobile_app/screens/widgets/active_downloads_dialog.dart';
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

void main() {
  late Directory tempDir;
  late DownloadService downloadService;
  late DownloadManager downloadManager;
  late ManhuaController manhuaController;

  final sampleManhua = Manhua(
    id: 1,
    title: 'Martial Peak',
    urlTemplate: 'https://example.com/ch/{chapter}',
    currentChapter: 100,
    updatedAt: 1000,
  );

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('active_dlg_test');
    downloadService = DownloadService(baseDirProvider: () async => tempDir);
    downloadManager = DownloadManager();

    final mockClient = MockClient((request) async {
      return http.Response(jsonEncode({'chapters': []}), 200);
    });
    final apiService = ApiService(client: mockClient, storageService: FakeStorageService());
    manhuaController = ManhuaController(apiService: apiService, storageService: FakeStorageService());
  });

  tearDown(() async {
    if (await tempDir.exists()) {
      await tempDir.delete(recursive: true);
    }
  });

  Widget createTestWidget({required Widget child}) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<DownloadManager>.value(value: downloadManager),
        ChangeNotifierProvider<ManhuaController>.value(value: manhuaController),
      ],
      child: MaterialApp(
        home: Scaffold(
          body: child,
        ),
      ),
    );
  }

  testWidgets('ActiveDownloadsDialog exibe mensagem vazia quando nao ha downloads ativos', (tester) async {
    await tester.pumpWidget(
      createTestWidget(
        child: ActiveDownloadsDialog(
          downloadManager: downloadManager,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Nenhum download em andamento no momento.'), findsOneWidget);
  });

  testWidgets('ActiveDownloadsDialog lista download em andamento e cancela com sucesso', (tester) async {
    final mockClient = MockClient((request) async {
      return http.Response(
        jsonEncode({
          'chapters': [
            {'chapter': 100, 'images': ['https://example.com/1.jpg']}
          ]
        }),
        200,
      );
    });
    final apiService = ApiService(client: mockClient, storageService: FakeStorageService());

    downloadManager.startDownload(
      manhua: sampleManhua,
      startChapter: 100,
      endChapter: 100,
      apiService: apiService,
      downloadService: downloadService,
    );

    await tester.pumpWidget(
      createTestWidget(
        child: ActiveDownloadsDialog(
          downloadManager: downloadManager,
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Martial Peak'), findsOneWidget);
    expect(find.text('Cancelar'), findsOneWidget);

    await tester.tap(find.text('Cancelar'));
    await tester.pumpAndSettle();

    expect(downloadManager.isDownloading(1), isFalse);
    expect(find.text('Nenhum download em andamento no momento.'), findsOneWidget);
  });

  testWidgets('HomeScreen exibe badge de downloads ativos e abre ActiveDownloadsDialog', (tester) async {
    final mockClient = MockClient((request) async {
      return http.Response(
        jsonEncode({
          'chapters': [
            {'chapter': 100, 'images': ['https://example.com/1.jpg']}
          ]
        }),
        200,
      );
    });
    final apiService = ApiService(client: mockClient, storageService: FakeStorageService());

    downloadManager.startDownload(
      manhua: sampleManhua,
      startChapter: 100,
      endChapter: 100,
      apiService: apiService,
      downloadService: downloadService,
    );

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<DownloadManager>.value(value: downloadManager),
          ChangeNotifierProvider<ManhuaController>.value(value: manhuaController),
        ],
        child: const MaterialApp(
          home: HomeScreen(),
        ),
      ),
    );
    await tester.pump();

    // Badge com contagem 1 deve estar visível
    expect(find.byTooltip('Downloads em Andamento'), findsOneWidget);
    expect(find.text('1'), findsOneWidget);

    // Tocar no botão de downloads em andamento
    await tester.tap(find.byTooltip('Downloads em Andamento'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // Diálogo aberto com o manhua listado
    expect(find.text('Downloads em Andamento'), findsOneWidget);
    expect(find.text('Martial Peak'), findsOneWidget);
  });
}
