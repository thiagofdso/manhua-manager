import 'dart:io';
import 'package:path_provider/path_provider.dart';

class DownloadService {
  final Future<Directory> Function()? _baseDirProvider;

  DownloadService({Future<Directory> Function()? baseDirProvider})
      : _baseDirProvider = baseDirProvider;

  Future<Directory> _getBaseDir() async {
    if (_baseDirProvider != null) {
      return await _baseDirProvider();
    }
    final appDir = await getApplicationDocumentsDirectory();
    final downloadDir = Directory('${appDir.path}/downloads');
    if (!await downloadDir.exists()) {
      await downloadDir.create(recursive: true);
    }
    return downloadDir;
  }

  Future<Directory> _getChapterDir(int manhuaId, int chapter) async {
    final base = await _getBaseDir();
    return Directory('${base.path}/$manhuaId/chapter_$chapter');
  }

  Future<bool> hasChapter(int manhuaId, int chapter) async {
    final dir = await _getChapterDir(manhuaId, chapter);
    if (!await dir.exists()) return false;
    final files = dir.listSync().whereType<File>().toList();
    return files.isNotEmpty;
  }

  Future<List<String>> getChapterImagePaths(int manhuaId, int chapter) async {
    final dir = await _getChapterDir(manhuaId, chapter);
    if (!await dir.exists()) return [];
    final files = dir.listSync().whereType<File>().toList();
    files.sort((a, b) => a.path.compareTo(b.path));
    return files.map((f) => f.path).toList();
  }

  Future<void> saveChapterImage(int manhuaId, int chapter, int pageIndex, List<int> bytes) async {
    final dir = await _getChapterDir(manhuaId, chapter);
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    final formattedIndex = pageIndex.toString().padLeft(4, '0');
    final file = File('${dir.path}/page_$formattedIndex.jpg');
    await file.writeAsBytes(bytes);
  }

  Future<void> deleteChapter(int manhuaId, int chapter) async {
    final dir = await _getChapterDir(manhuaId, chapter);
    if (await dir.exists()) {
      await dir.delete(recursive: true);
    }
  }

  Future<void> deleteAllForManhua(int manhuaId) async {
    final base = await _getBaseDir();
    final manhuaDir = Directory('${base.path}/$manhuaId');
    if (await manhuaDir.exists()) {
      await manhuaDir.delete(recursive: true);
    }
  }

  Future<void> clearAllDownloads() async {
    final base = await _getBaseDir();
    if (await base.exists()) {
      await base.delete(recursive: true);
      await base.create(recursive: true);
    }
  }

  Future<List<int>> getDownloadedChapters(int manhuaId) async {
    final base = await _getBaseDir();
    final manhuaDir = Directory('${base.path}/$manhuaId');
    if (!await manhuaDir.exists()) return [];
    final list = <int>[];
    for (final entity in manhuaDir.listSync()) {
      if (entity is Directory) {
        final name = entity.uri.pathSegments.where((s) => s.isNotEmpty).last;
        if (name.startsWith('chapter_')) {
          final numStr = name.replaceFirst('chapter_', '');
          final n = int.tryParse(numStr);
          if (n != null) list.add(n);
        }
      }
    }
    list.sort();
    return list;
  }

  Future<int> getTotalDownloadedCount() async {
    final base = await _getBaseDir();
    if (!await base.exists()) return 0;
    int count = 0;
    for (final entity in base.listSync()) {
      if (entity is Directory) {
        for (final chapDir in entity.listSync()) {
          if (chapDir is Directory) count++;
        }
      }
    }
    return count;
  }
}
