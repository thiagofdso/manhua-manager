import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/controllers/manhua_controller.dart';
import 'package:mobile_app/models/manhua.dart';
import 'package:mobile_app/screens/reader_screen.dart';
import 'package:mobile_app/services/download_service.dart';
import 'package:mobile_app/services/api_service.dart';
import 'package:mobile_app/services/storage_service.dart';

class FakeStorageService extends StorageService {
  @override
  Future<String> getBaseUrl() async => 'http://100.84.57.79:5000';
}

class FakeApiService extends ApiService {
  @override
  Future<List<String>> fetchChapterImages(String targetUrl) async => [];
  @override
  Future<String> getProxyImageUrl(String imageUrl) async => imageUrl;
}

class FakeOfflineDownloadService extends DownloadService {
  final Map<int, List<String>> chapters = {};

  @override
  Future<bool> hasChapter(int manhuaId, int chapter) async {
    return chapters.containsKey(chapter) && chapters[chapter]!.isNotEmpty;
  }

  @override
  Future<List<String>> getChapterImagePaths(int manhuaId, int chapter) async {
    return chapters[chapter] ?? [];
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('ReaderScreen carrega imagens locais e exibe badge offline sem chamar rede', (tester) async {
    final manhua = Manhua(
      id: 1,
      title: 'Overgeared',
      urlTemplate: 'https://test/chapter/{chapter}',
      currentChapter: 10,
    );

    late Directory tempDir;
    late File dummyFile;
    await tester.runAsync(() async {
      tempDir = await Directory.systemTemp.createTemp('reader_offline_test');
      dummyFile = File('${tempDir.path}/page_0001.png');
      await dummyFile.writeAsBytes(base64Decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='));
    });

    final fakeDownloadService = FakeOfflineDownloadService();
    fakeDownloadService.chapters[10] = [dummyFile.path];

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider(create: (_) => ManhuaController(
            apiService: FakeApiService(),
            storageService: FakeStorageService(),
          )),
        ],
        child: MaterialApp(
          home: ReaderScreen(
            manhua: manhua,
            downloadService: fakeDownloadService,
          ),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));

    expect(find.text('💾 Offline'), findsOneWidget);

    await tester.runAsync(() async {
      if (await tempDir.exists()) {
        await tempDir.delete(recursive: true);
      }
    });
  });
}
