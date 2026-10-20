import 'package:shared_preferences/shared_preferences.dart';

class StorageService {
  static const String _defaultUrl = 'http://100.84.57.79:5000';
  static const String _keyBackendUrl = 'backend_base_url';

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
}
