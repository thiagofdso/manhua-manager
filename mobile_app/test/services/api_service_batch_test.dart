import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile_app/services/api_service.dart';
import 'package:mobile_app/services/storage_service.dart';

class FakeStorageService extends StorageService {
  @override
  Future<String> getBaseUrl() async => 'http://100.84.57.79:5000';
}

void main() {
  test('fetchBatchChapterImages envia id, start e end e retorna json', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.path, '/api/manhuas/1/batch-chapter-images');
      expect(request.url.queryParameters['start'], '10');
      expect(request.url.queryParameters['end'], '12');
      return http.Response(jsonEncode({
        'manhuaId': 1,
        'chapters': [
          {'chapter': 10, 'images': ['https://test/1.jpg']}
        ]
      }), 200);
    });

    final api = ApiService(client: mockClient, storageService: FakeStorageService());
    final res = await api.fetchBatchChapterImages(1, 10, 12);
    expect(res['manhuaId'], 1);
    expect(res['chapters'].length, 1);
  });
}
