import 'package:flutter/foundation.dart';
import '../models/manhua.dart';
import '../services/api_service.dart';
import '../services/storage_service.dart';

class ManhuaController extends ChangeNotifier {
  final ApiService _apiService;
  final StorageService _storageService;

  List<Manhua> _manhuas = [];
  List<Map<String, dynamic>> _notifications = [];
  bool _isLoading = false;
  String? _errorMessage;
  bool _isOfflineMode = false;
  String _baseUrl = 'http://100.84.57.79:5000';

  ManhuaController({
    ApiService? apiService,
    StorageService? storageService,
  })  : _apiService = apiService ?? ApiService(),
        _storageService = storageService ?? StorageService() {
    loadBaseUrl();
  }

  List<Manhua> get manhuas => _manhuas;
  List<Map<String, dynamic>> get notifications => _notifications;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  bool get isOfflineMode => _isOfflineMode;
  String get baseUrl => _baseUrl;
  ApiService get apiService => _apiService;

  Future<void> loadBaseUrl() async {
    _baseUrl = await _storageService.getBaseUrl();
    notifyListeners();
  }

  Future<void> updateBaseUrl(String newUrl) async {
    await _storageService.setBaseUrl(newUrl);
    _baseUrl = await _storageService.getBaseUrl();
    notifyListeners();
    await loadManhuas();
  }

  Future<void> loadManhuas() async {
    _isLoading = true;
    _errorMessage = null;

    // Carregamento instantâneo do cache offline para abertura imediata
    final cached = await _storageService.getCachedManhuas();
    if (cached.isNotEmpty && _manhuas.isEmpty) {
      _manhuas = cached;
      notifyListeners();
    } else {
      notifyListeners();
    }

    try {
      final list = await _apiService.fetchManhuas();
      _manhuas = list;
      _isOfflineMode = false;
      await _storageService.saveCachedManhuas(list);
      await loadNotifications();
    } catch (e) {
      final fallbackCached = await _storageService.getCachedManhuas();
      if (fallbackCached.isNotEmpty) {
        _manhuas = fallbackCached;
        _isOfflineMode = true;
        _errorMessage = null;
      } else {
        _errorMessage = e.toString();
      }
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> changeChapterDelta(int id, int delta) async {
    try {
      final updated = await _apiService.updateChapterDelta(id, delta);
      final idx = _manhuas.indexWhere((m) => m.id == id);
      if (idx != -1) {
        _manhuas[idx] = updated;
        await _storageService.saveCachedManhuas(_manhuas);
        notifyListeners();
      }
    } catch (e) {
      _isOfflineMode = true;
      final idx = _manhuas.indexWhere((m) => m.id == id);
      if (idx != -1) {
        final current = _manhuas[idx];
        final nextChap = current.currentChapter + delta;
        if (nextChap >= 1) {
          _manhuas[idx] = current.copyWith(currentChapter: nextChap);
          await _storageService.saveCachedManhuas(_manhuas);
          notifyListeners();
        }
      }
    }
  }

  Future<void> addManhua(
    String title,
    String urlTemplate,
    int currentChapter, {
    int? lastChapter,
    int? updateDay,
    bool isHiatus = false,
  }) async {
    _isLoading = true;
    notifyListeners();
    try {
      final created = await _apiService.addManhua(
        title,
        urlTemplate,
        currentChapter,
        lastChapter: lastChapter,
        updateDay: updateDay,
        isHiatus: isHiatus,
      );
      _manhuas.add(created);
    } catch (e) {
      _errorMessage = 'Erro ao adicionar manhua: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> editManhua(
    int id, {
    String? title,
    String? urlTemplate,
    int? chapter,
    int? lastChapter,
    bool clearLastChapter = false,
    int? updateDay,
    bool clearUpdateDay = false,
    bool? isHiatus,
  }) async {
    _isLoading = true;
    notifyListeners();
    try {
      final updated = await _apiService.updateManhua(
        id,
        title: title,
        urlTemplate: urlTemplate,
        chapter: chapter,
        lastChapter: lastChapter,
        clearLastChapter: clearLastChapter,
        updateDay: updateDay,
        clearUpdateDay: clearUpdateDay,
        isHiatus: isHiatus,
      );
      final idx = _manhuas.indexWhere((m) => m.id == id);
      if (idx != -1) {
        _manhuas[idx] = updated;
      }
    } catch (e) {
      _errorMessage = 'Erro ao atualizar manhua: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> loadNotifications() async {
    try {
      final notifs = await _apiService.fetchNotifications();
      _notifications = notifs;
      notifyListeners();
    } catch (_) {}
  }

  Future<void> dismissNotification(int id) async {
    try {
      await _apiService.deleteNotification(id);
      _notifications.removeWhere((n) => n['id'] == id);
      notifyListeners();
    } catch (_) {}
  }

  Future<void> clearAllNotifications() async {
    try {
      await _apiService.clearNotifications();
      _notifications.clear();
      notifyListeners();
    } catch (_) {}
  }

  Future<Map<String, dynamic>> triggerManualCheck({bool checkAll = false}) async {
    _isLoading = true;
    notifyListeners();
    try {
      final res = await _apiService.triggerManualCheck(checkAll: checkAll);
      await loadManhuas();
      return res;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> deleteManhua(int id) async {
    try {
      await _apiService.deleteManhua(id);
      _manhuas.removeWhere((m) => m.id == id);
      notifyListeners();
    } catch (e) {
      _errorMessage = 'Erro ao excluir manhua: $e';
      notifyListeners();
    }
  }

  Future<void> toggleFavorite(int id) async {
    final index = _manhuas.indexWhere((m) => m.id == id);
    if (index == -1) return;
    final current = _manhuas[index];
    final newStatus = !current.isFavorite;

    try {
      await _apiService.toggleFavorite(id, newStatus);
      await loadManhuas();
    } catch (e) {
      _errorMessage = 'Erro ao alternar favorito: $e';
      notifyListeners();
    }
  }

  Future<void> saveReorder(List<int> orderedIds) async {
    _isLoading = true;
    notifyListeners();
    try {
      await _apiService.reorderManhuas(orderedIds);
      await loadManhuas();
    } catch (e) {
      _errorMessage = 'Erro ao salvar reordenação: $e';
      notifyListeners();
    }
  }
}
