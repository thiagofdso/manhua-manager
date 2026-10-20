import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile_app/services/api_service.dart';
import 'package:mobile_app/services/storage_service.dart';

class FakeStorageService extends StorageService {
  String url = 'http://100.84.57.79:5000';

  @override
  Future<String> getBaseUrl() async => url;

  @override
  Future<void> setBaseUrl(String newUrl) async {
    url = newUrl;
  }
}

void main() {
  group('ApiService Tests', () {
    test('fetchManhuas deve retornar lista de manhuas', () async {
      final mockClient = MockClient((request) async {
        expect(request.url.path, '/api/manhuas');
        return http.Response(
          jsonEncode([
            {
              'id': 1,
              'title': 'Overgeared',
              'urlTemplate': 'https://asurascans.com/comics/overgeared-11fe7da3/chapter/{chapter}',
              'currentChapter': 203,
              'updatedAt': 123456
            }
          ]),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final storage = FakeStorageService();
      final api = ApiService(client: mockClient, storageService: storage);

      final list = await api.fetchManhuas();
      expect(list.length, 1);
      expect(list.first.title, 'Overgeared');
      expect(list.first.currentChapter, 203);
    });

    test('updateChapterDelta deve atualizar capitulo', () async {
      final mockClient = MockClient((request) async {
        expect(request.url.path, '/api/manhuas/1');
        expect(request.method, 'PATCH');
        final body = jsonDecode(request.body);
        expect(body['delta'], 1);
        return http.Response(
          jsonEncode({
            'status': 'ok',
            'item': {
              'id': 1,
              'title': 'Overgeared',
              'urlTemplate': 'https://asurascans.com/comics/overgeared-11fe7da3/chapter/{chapter}',
              'currentChapter': 204,
              'updatedAt': 123457
            }
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final storage = FakeStorageService();
      final api = ApiService(client: mockClient, storageService: storage);

      final updated = await api.updateChapterDelta(1, 1);
      expect(updated.currentChapter, 204);
    });

    test('fetchChapterImages deve retornar lista de imagens', () async {
      final mockClient = MockClient((request) async {
        expect(request.url.path, '/api/chapter-images');
        expect(request.url.queryParameters['url'], 'https://test.com/chapter-1');
        return http.Response(
          jsonEncode({
            'status': 'ok',
            'count': 2,
            'images': ['https://cdn.com/1.webp', 'https://cdn.com/2.webp']
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final storage = FakeStorageService();
      final api = ApiService(client: mockClient, storageService: storage);

      final imgs = await api.fetchChapterImages('https://test.com/chapter-1');
      expect(imgs.length, 2);
      expect(imgs[0], 'https://cdn.com/1.webp');
      expect(imgs[1], 'https://cdn.com/2.webp');
    });

    test('getProxyImageUrl formata url com proxy corretamente', () async {
      final storage = FakeStorageService();
      final api = ApiService(storageService: storage);

      final proxyUrl = await api.getProxyImageUrl('https://cdn.com/1.webp');
      expect(proxyUrl, 'http://100.84.57.79:5000/api/proxy-image?url=https%3A%2F%2Fcdn.com%2F1.webp');
    });
  });
}
