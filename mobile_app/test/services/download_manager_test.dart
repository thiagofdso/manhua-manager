import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile_app/models/download_task.dart';
import 'package:mobile_app/models/manhua.dart';
import 'package:mobile_app/services/api_service.dart';
import 'package:mobile_app/services/download_manager.dart';
import 'package:mobile_app/services/download_service.dart';
import 'package:mobile_app/services/storage_service.dart';

class FakeStorageService extends StorageService {
  @override
  Future<String> getBaseUrl() async => 'http://127.0.0.1:5000';
}

void main() {
  late Directory tempDir;
  late DownloadService downloadService;
  late DownloadManager downloadManager;

  final sampleManhua = Manhua(
    id: 1,
    title: 'Test Manhua',
    urlTemplate: 'https://example.com/ch/{chapter}',
    currentChapter: 10,
    updatedAt: 1000,
  );

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('download_mgr_test');
    downloadService = DownloadService(baseDirProvider: () async => tempDir);
    downloadManager = DownloadManager();
  });

  tearDown(() async {
    if (await tempDir.exists()) {
      await tempDir.delete(recursive: true);
    }
  });

  test('DownloadManager executa download e salva imagens', () async {
    final mockClient = MockClient((request) async {
      if (request.url.path.contains('batch-chapter-images')) {
        return http.Response(
          jsonEncode({
            'manhuaId': 1,
            'chapters': [
              {
                'chapter': 10,
                'images': ['https://example.com/p1.jpg', 'https://example.com/p2.jpg']
              }
            ]
          }),
          200,
        );
      }
      if (request.url.path.contains('proxy-image')) {
        return http.Response.bytes([1, 2, 3, 4], 200);
      }
      return http.Response('Not found', 404);
    });

    final apiService = ApiService(client: mockClient, storageService: FakeStorageService());

    expect(downloadManager.isDownloading(1), isFalse);
    expect(downloadManager.activeTasks, isEmpty);

    final future = downloadManager.startDownload(
      manhua: sampleManhua,
      startChapter: 10,
      endChapter: 10,
      apiService: apiService,
      downloadService: downloadService,
    );

    expect(downloadManager.isDownloading(1), isTrue);
    expect(downloadManager.activeTasks.length, 1);
    expect(downloadManager.getTask(1)?.manhuaTitle, 'Test Manhua');

    await future;

    expect(downloadManager.isDownloading(1), isFalse);
    expect(downloadManager.activeTasks, isEmpty);
    final task = downloadManager.getTask(1);
    expect(task?.status, DownloadTaskStatus.completed);
    expect(task?.progress, 1.0);

    final hasChap = await downloadService.hasChapter(1, 10);
    expect(hasChap, isTrue);
    final pages = await downloadService.getChapterImagePaths(1, 10);
    expect(pages.length, 2);
  });

  test('DownloadManager cancelDownload interrompe download e mantém capítulos já salvos', () async {
    int proxyCallCount = 0;
    final mockClient = MockClient((request) async {
      if (request.url.path.contains('batch-chapter-images')) {
        return http.Response(
          jsonEncode({
            'manhuaId': 1,
            'chapters': [
              {
                'chapter': 10,
                'images': ['https://example.com/c10_1.jpg']
              },
              {
                'chapter': 11,
                'images': ['https://example.com/c11_1.jpg']
              }
            ]
          }),
          200,
        );
      }
      if (request.url.path.contains('proxy-image')) {
        proxyCallCount++;
        if (proxyCallCount == 2) {
          // Cancelamos na imagem do capítulo 11
          downloadManager.cancelDownload(1);
        }
        return http.Response.bytes([1, 2, 3], 200);
      }
      return http.Response('Not found', 404);
    });

    final apiService = ApiService(client: mockClient, storageService: FakeStorageService());

    await downloadManager.startDownload(
      manhua: sampleManhua,
      startChapter: 10,
      endChapter: 11,
      apiService: apiService,
      downloadService: downloadService,
    );

    final task = downloadManager.getTask(1);
    expect(task?.status, DownloadTaskStatus.cancelled);
    expect(task?.isCancelled, isTrue);
    expect(downloadManager.isDownloading(1), isFalse);

    // Capítulo 10 foi salvo antes do cancelamento e NÃO pode ser excluído
    expect(await downloadService.hasChapter(1, 10), isTrue);
    // Capítulo 11 não foi baixado
    expect(await downloadService.hasChapter(1, 11), isFalse);
  });
}
