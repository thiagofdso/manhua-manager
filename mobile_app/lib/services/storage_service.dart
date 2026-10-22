import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/manhua.dart';

class StorageService {
  static const String _defaultUrl = 'http://100.84.57.79:5000';
  static const String _keyBackendUrl = 'backend_base_url';
  static const String _keyCachedManhuas = 'cached_manhuas_list';

  List<Manhua>? _memoryCache;

  Future<String> getBaseUrl() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return prefs.getString(_keyBackendUrl) ?? _defaultUrl;
    } catch (_) {
      return _defaultUrl;
    }
  }

  Future<void> setBaseUrl(String url) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      String formatted = url.trim();
      if (formatted.endsWith('/')) {
        formatted = formatted.substring(0, formatted.length - 1);
      }
      await prefs.setString(_keyBackendUrl, formatted);
    } catch (_) {}
  }

  Future<void> saveCachedManhuas(List<Manhua> manhuas) async {
    _memoryCache = List.from(manhuas);
    try {
      final prefs = await SharedPreferences.getInstance();
      final listJson = manhuas.map((m) => m.toJson()).toList();
      await prefs.setString(_keyCachedManhuas, jsonEncode(listJson));
    } catch (_) {}
  }

  Future<List<Manhua>> getCachedManhuas() async {
    if (_memoryCache != null && _memoryCache!.isNotEmpty) {
      return _memoryCache!;
    }
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getString(_keyCachedManhuas);
      if (raw == null || raw.isEmpty) return [];
      final List<dynamic> decoded = jsonDecode(raw);
      _memoryCache = decoded.map((item) => Manhua.fromJson(item as Map<String, dynamic>)).toList();
      return _memoryCache!;
    } catch (_) {
      return _memoryCache ?? [];
    }
  }
}
