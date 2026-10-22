import 'package:flutter/foundation.dart';
import '../models/manhua.dart';
import '../models/download_task.dart';
import 'api_service.dart';
import 'download_service.dart';

class DownloadManager extends ChangeNotifier {
  final Map<int, DownloadTask> _tasks = {};

  List<DownloadTask> get activeTasks => _tasks.values
      .where((t) => !t.isCancelled && t.status == DownloadTaskStatus.downloading)
      .toList();

  DownloadTask? getTask(int manhuaId) => _tasks[manhuaId];

  bool isDownloading(int manhuaId) {
    final task = _tasks[manhuaId];
    return task != null && !task.isCancelled && task.status == DownloadTaskStatus.downloading;
  }

  void cancelDownload(int manhuaId) {
    final task = _tasks[manhuaId];
    if (task != null && task.status == DownloadTaskStatus.downloading) {
      task.isCancelled = true;
      task.status = DownloadTaskStatus.cancelled;
      task.statusMessage = 'Download cancelado pelo usuário.';
      notifyListeners();
    }
  }

  void removeTask(int manhuaId) {
    _tasks.remove(manhuaId);
    notifyListeners();
  }

  Future<void> startDownload({
    required Manhua manhua,
    required int startChapter,
    required int endChapter,
    required ApiService apiService,
    required DownloadService downloadService,
  }) async {
    if (isDownloading(manhua.id)) return;
    if (manhua.lastChapter != null && (startChapter > manhua.lastChapter! || endChapter > manhua.lastChapter!)) {
      return;
    }

    final task = DownloadTask(
      manhuaId: manhua.id,
      manhuaTitle: manhua.title,
      startChapter: startChapter,
      endChapter: endChapter,
      statusMessage: 'Consultando capítulos no servidor...',
      progress: 0.05,
    );
    _tasks[manhua.id] = task;
    notifyListeners();

    try {
      final batchData = await apiService.fetchBatchChapterImages(manhua.id, startChapter, endChapter);
      if (task.isCancelled) return;

      final List<dynamic> chapters = batchData['chapters'] ?? [];
      int totalImages = 0;
      for (final c in chapters) {
        final List<dynamic> imgs = c['images'] ?? [];
        totalImages += imgs.length;
      }
      task.totalImages = totalImages;

      int downloadedImages = 0;

      for (int i = 0; i < chapters.length; i++) {
        if (task.isCancelled) break;
        final c = chapters[i];
        final chapNum = c['chapter'] as int;
        final List<dynamic> images = c['images'] ?? [];
        if (images.isEmpty) continue;

        task.currentChapter = chapNum;
        task.totalImagesInCurrentChapter = images.length;

        for (int p = 0; p < images.length; p++) {
          if (task.isCancelled) break;
          final imgUrl = images[p].toString();
          task.currentImage = p + 1;
          task.statusMessage = 'Capítulo $chapNum: imagem ${p + 1} de ${images.length}...';
          notifyListeners();

          try {
            final proxy = await apiService.getProxyImageUrl(imgUrl);
            final bytes = await apiService.downloadImageBytes(proxy);
            if (task.isCancelled) break;
            await downloadService.saveChapterImage(manhua.id, chapNum, p, bytes);
          } catch (e) {
            debugPrint('Erro ao baixar imagem $imgUrl: $e');
          }

          downloadedImages++;
          task.downloadedImages = downloadedImages;
          if (totalImages > 0) {
            task.progress = downloadedImages / totalImages;
          }
          notifyListeners();
        }
      }

      if (task.isCancelled) {
        task.status = DownloadTaskStatus.cancelled;
        task.statusMessage = 'Download cancelado pelo usuário.';
      } else {
        task.progress = 1.0;
        task.status = DownloadTaskStatus.completed;
        task.statusMessage = 'Download finalizado com sucesso!';
      }
    } catch (e) {
      if (!task.isCancelled) {
        task.status = DownloadTaskStatus.error;
        task.errorMessage = e.toString();
        task.statusMessage = 'Erro durante o download: $e';
      }
    } finally {
      notifyListeners();
    }
  }
}
