import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/manhua.dart';
import 'storage_service.dart';

class ApiService {
  final http.Client _client;
  final StorageService _storageService;

  ApiService({
    http.Client? client,
    StorageService? storageService,
  })  : _client = client ?? http.Client(),
        _storageService = storageService ?? StorageService();

  Future<String> _baseUrl() async {
    return await _storageService.getBaseUrl();
  }

  Future<List<Manhua>> fetchManhuas() async {
    final base = await _baseUrl();
    final res = await _client.get(Uri.parse('$base/api/manhuas'));
    if (res.statusCode == 200) {
      final List<dynamic> data = jsonDecode(res.body);
      return data.map((item) => Manhua.fromJson(item as Map<String, dynamic>)).toList();
    } else {
      throw Exception('Falha ao carregar manhuas: ${res.statusCode}');
    }
  }

  Future<Manhua> addManhua(String title, String urlTemplate, int currentChapter) async {
    final base = await _baseUrl();
    final res = await _client.post(
      Uri.parse('$base/api/manhuas'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'title': title,
        'urlTemplate': urlTemplate,
        'currentChapter': currentChapter,
      }),
    );
    if (res.statusCode == 200) {
      final data = jsonDecode(res.body);
      return Manhua.fromJson(data['item'] as Map<String, dynamic>);
    } else {
      throw Exception('Falha ao cadastrar manhua: ${res.statusCode}');
    }
  }

  Future<Manhua> updateChapterDelta(int id, int delta) async {
    final base = await _baseUrl();
    final res = await _client.patch(
      Uri.parse('$base/api/manhuas/$id'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'delta': delta}),
    );
    if (res.statusCode == 200) {
      final data = jsonDecode(res.body);
      return Manhua.fromJson(data['item'] as Map<String, dynamic>);
    } else {
      throw Exception('Falha ao alterar capitulo: ${res.statusCode}');
    }
  }

  Future<Manhua> updateManhua(
    int id, {
    String? title,
    String? urlTemplate,
    int? chapter,
  }) async {
    final base = await _baseUrl();
    final Map<String, dynamic> body = {};
    if (title != null) body['title'] = title;
    if (urlTemplate != null) body['urlTemplate'] = urlTemplate;
    if (chapter != null) body['chapter'] = chapter;

    final res = await _client.patch(
      Uri.parse('$base/api/manhuas/$id'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    if (res.statusCode == 200) {
      final data = jsonDecode(res.body);
      return Manhua.fromJson(data['item'] as Map<String, dynamic>);
    } else {
      throw Exception('Falha ao atualizar manhua: ${res.statusCode}');
    }
  }

  Future<void> deleteManhua(int id) async {
    final base = await _baseUrl();
    final res = await _client.delete(Uri.parse('$base/api/manhuas/$id'));
    if (res.statusCode != 200) {
      throw Exception('Falha ao excluir manhua: ${res.statusCode}');
    }
  }

  Future<List<String>> fetchChapterImages(String targetUrl) async {
    final base = await _baseUrl();
    final uri = Uri.parse('$base/api/chapter-images').replace(
      queryParameters: {'url': targetUrl},
    );
    final res = await _client.get(uri);
    if (res.statusCode == 200) {
      final data = jsonDecode(res.body);
      final List<dynamic> images = data['images'] ?? [];
      return images.map((e) => e.toString()).toList();
    } else {
      throw Exception('Falha ao extrair imagens: ${res.statusCode}');
    }
  }

  Future<String> getProxyImageUrl(String imageUrl) async {
    final base = await _baseUrl();
    return '$base/api/proxy-image?url=${Uri.encodeComponent(imageUrl)}';
  }
}
