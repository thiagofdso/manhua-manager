import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile_app/controllers/manhua_controller.dart';
import 'package:mobile_app/models/download_task.dart';
import 'package:mobile_app/models/manhua.dart';
import 'package:mobile_app/screens/widgets/download_manhua_dialog.dart';
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
    title: 'Solo Leveling',
    urlTemplate: 'https://example.com/ch/{chapter}',
    currentChapter: 10,
    updatedAt: 1000,
  );

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('dlg_test');
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

  testWidgets('DownloadManhuaDialog exibe botao Iniciar Download quando nao ha tarefa ativa', (tester) async {
    await tester.pumpWidget(
      createTestWidget(
        child: DownloadManhuaDialog(
          manhua: sampleManhua,
          downloadService: downloadService,
          downloadManager: downloadManager,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Iniciar Download'), findsOneWidget);
    expect(find.text('Cancelar Download'), findsNothing);
  });

  testWidgets('DownloadManhuaDialog reconecta a tarefa em andamento e permite cancelar', (tester) async {
    // Inicia uma tarefa simulada no DownloadManager
    final mockClient = MockClient((request) async {
      // Deixar pendente ou retornar dados
      return http.Response(
        jsonEncode({
          'chapters': [
            {'chapter': 10, 'images': ['https://example.com/1.jpg']}
          ]
        }),
        200,
      );
    });
    final apiService = ApiService(client: mockClient, storageService: FakeStorageService());

    // Iniciar download
    downloadManager.startDownload(
      manhua: sampleManhua,
      startChapter: 10,
      endChapter: 10,
      apiService: apiService,
      downloadService: downloadService,
    );

    await tester.pumpWidget(
      createTestWidget(
        child: DownloadManhuaDialog(
          manhua: sampleManhua,
          downloadService: downloadService,
          downloadManager: downloadManager,
        ),
      ),
    );
    await tester.pump();

    // Deve exibir botão de cancelar
    expect(find.text('Cancelar Download'), findsOneWidget);

    // Clicar em cancelar download
    await tester.tap(find.text('Cancelar Download'));
    await tester.pumpAndSettle();

    expect(downloadManager.getTask(1)?.isCancelled, isTrue);
  });

  testWidgets('DownloadManhuaDialog bloqueia download e exibe snackbar quando excede lastChapter', (tester) async {
    final limitedManhua = Manhua(
      id: 99,
      title: 'Obra Limitada',
      urlTemplate: 'https://exemplo.com/{chapter}',
      currentChapter: 10,
      lastChapter: 12,
    );

    await tester.pumpWidget(
      createTestWidget(
        child: DownloadManhuaDialog(
          manhua: limitedManhua,
          downloadService: downloadService,
          downloadManager: downloadManager,
        ),
      ),
    );
    await tester.pumpAndSettle();

    // O campo fim sugerido não deve ultrapassar o lastChapter (12)
    final endFinder = find.widgetWithText(TextField, '12');
    expect(endFinder, findsOneWidget);

    // Digita um capítulo final além do limite (15)
    await tester.enterText(endFinder, '15');
    await tester.pumpAndSettle();

    // Clica em Iniciar Download
    await tester.tap(find.text('Iniciar Download'));
    await tester.pumpAndSettle();

    // Verifica mensagem de bloqueio no SnackBar
    expect(find.textContaining('O intervalo não pode ultrapassar o último episódio disponível (12)'), findsOneWidget);
    // Verifica que nenhuma tarefa de download foi iniciada
    expect(downloadManager.isDownloading(99), isFalse);
  });
}
