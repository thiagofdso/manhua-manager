import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/services/download_service.dart';

void main() {
  late Directory tempDir;
  late DownloadService downloadService;

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('download_service_test');
    downloadService = DownloadService(baseDirProvider: () async => tempDir);
  });

  tearDown(() async {
    if (await tempDir.exists()) {
      await tempDir.delete(recursive: true);
    }
  });

  test('salva imagem de capitulo e verifica existencia', () async {
    expect(await downloadService.hasChapter(1, 10), isFalse);

    await downloadService.saveChapterImage(1, 10, 0, [1, 2, 3]);
    await downloadService.saveChapterImage(1, 10, 1, [4, 5, 6]);

    expect(await downloadService.hasChapter(1, 10), isTrue);
    final paths = await downloadService.getChapterImagePaths(1, 10);
    expect(paths.length, 2);

    final chapters = await downloadService.getDownloadedChapters(1);
    expect(chapters, [10]);
  });

  test('deleteChapter e deleteAllForManhua removem arquivos', () async {
    await downloadService.saveChapterImage(1, 10, 0, [1, 2, 3]);
    await downloadService.saveChapterImage(1, 11, 0, [1, 2, 3]);

    await downloadService.deleteChapter(1, 10);
    expect(await downloadService.hasChapter(1, 10), isFalse);
    expect(await downloadService.hasChapter(1, 11), isTrue);

    await downloadService.deleteAllForManhua(1);
    expect(await downloadService.hasChapter(1, 11), isFalse);
  });

  test('clearAllDownloads limpa todos os downloads', () async {
    await downloadService.saveChapterImage(1, 10, 0, [1, 2, 3]);
    await downloadService.saveChapterImage(2, 20, 0, [4, 5, 6]);
    expect(await downloadService.getTotalDownloadedCount(), 2);

    await downloadService.clearAllDownloads();
    expect(await downloadService.getTotalDownloadedCount(), 0);
  });
}
