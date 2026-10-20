import 'package:flutter/foundation.dart';
import '../models/manhua.dart';
import '../services/api_service.dart';
import '../services/storage_service.dart';

class ManhuaController extends ChangeNotifier {
  final ApiService _apiService;
  final StorageService _storageService;

  List<Manhua> _manhuas = [];
  bool _isLoading = false;
  String? _errorMessage;
  String _baseUrl = 'http://100.84.57.79:5000';

  ManhuaController({
    ApiService? apiService,
    StorageService? storageService,
  })  : _apiService = apiService ?? ApiService(),
        _storageService = storageService ?? StorageService() {
    loadBaseUrl();
  }

  List<Manhua> get manhuas => _manhuas;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
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
    notifyListeners();

    try {
      _manhuas = await _apiService.fetchManhuas();
    } catch (e) {
      _errorMessage = e.toString();
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
        notifyListeners();
      }
    } catch (e) {
      _errorMessage = 'Erro ao alterar capítulo: $e';
      notifyListeners();
    }
  }

  Future<void> addManhua(String title, String urlTemplate, int currentChapter) async {
    _isLoading = true;
    notifyListeners();
    try {
      final created = await _apiService.addManhua(title, urlTemplate, currentChapter);
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
  }) async {
    _isLoading = true;
    notifyListeners();
    try {
      final updated = await _apiService.updateManhua(
        id,
        title: title,
        urlTemplate: urlTemplate,
        chapter: chapter,
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
}
