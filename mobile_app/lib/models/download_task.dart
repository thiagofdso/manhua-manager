enum DownloadTaskStatus {
  downloading,
  completed,
  cancelled,
  error,
}

class DownloadTask {
  final int manhuaId;
  final String manhuaTitle;
  final int startChapter;
  final int endChapter;

  int currentChapter;
  int currentImage;
  int totalImagesInCurrentChapter;
  int totalImages;
  int downloadedImages;
  double progress;
  String statusMessage;
  DownloadTaskStatus status;
  bool isCancelled;
  String? errorMessage;

  DownloadTask({
    required this.manhuaId,
    required this.manhuaTitle,
    required this.startChapter,
    required this.endChapter,
    this.currentChapter = 0,
    this.currentImage = 0,
    this.totalImagesInCurrentChapter = 0,
    this.totalImages = 0,
    this.downloadedImages = 0,
    this.progress = 0.0,
    this.statusMessage = 'Iniciando download...',
    this.status = DownloadTaskStatus.downloading,
    this.isCancelled = false,
    this.errorMessage,
  });
}
