import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/manhua.dart';

class StorageService {
  static const String _defaultUrl = 'http://100.84.57.79:5000';
  static const String _keyBackendUrl = 'backend_base_url';
  static const String _keyCachedManhuas = 'cached_manhuas_list';

  Future<String> getBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyBackendUrl) ?? _defaultUrl;
  }

  Future<void> setBaseUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    String formatted = url.trim();
    if (formatted.endsWith('/')) {
      formatted = formatted.substring(0, formatted.length - 1);
    }
    await prefs.setString(_keyBackendUrl, formatted);
  }

  Future<void> saveCachedManhuas(List<Manhua> manhuas) async {
    final prefs = await SharedPreferences.getInstance();
    final listJson = manhuas.map((m) => m.toJson()).toList();
    await prefs.setString(_keyCachedManhuas, jsonEncode(listJson));
  }

  Future<List<Manhua>> getCachedManhuas() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_keyCachedManhuas);
    if (raw == null || raw.isEmpty) return [];
    try {
      final List<dynamic> decoded = jsonDecode(raw);
      return decoded.map((item) => Manhua.fromJson(item as Map<String, dynamic>)).toList();
    } catch (_) {
      return [];
    }
  }
}
