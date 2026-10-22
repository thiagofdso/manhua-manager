import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile_app/services/api_service.dart';
import 'package:mobile_app/services/storage_service.dart';

class FakeStorageService extends StorageService {
  @override
  Future<String> getBaseUrl() async => 'http://test';
}

void main() {
  group('ApiService Notifications Tests', () {
    test('fetchNotifications retorna lista de notificacoes', () async {
      final mockClient = MockClient((request) async {
        if (request.url.path == '/api/notifications' && request.method == 'GET') {
          return http.Response(
            jsonEncode([
              {
                'id': 101,
                'manhuaId': 1,
                'title': 'Overgeared',
                'chapter': 245,
                'message': 'Novo episódio 245 disponível!',
                'createdAt': 1792623272
              }
            ]),
            200,
          );
        }
        return http.Response('Not Found', 404);
      });

      final api = ApiService(client: mockClient, storageService: FakeStorageService());
      final notifs = await api.fetchNotifications();
      expect(notifs.length, 1);
      expect(notifs[0]['id'], 101);
      expect(notifs[0]['chapter'], 245);
    });

    test('deleteNotification e clearNotifications executam DELETE', () async {
      bool deletedSingle = false;
      bool clearedAll = false;

      final mockClient = MockClient((request) async {
        if (request.url.path == '/api/notifications/101' && request.method == 'DELETE') {
          deletedSingle = true;
          return http.Response('{"status": "ok"}', 200);
        }
        if (request.url.path == '/api/notifications' && request.method == 'DELETE') {
          clearedAll = true;
          return http.Response('{"status": "ok"}', 200);
        }
        return http.Response('Not Found', 404);
      });

      final api = ApiService(client: mockClient, storageService: FakeStorageService());
      await api.deleteNotification(101);
      expect(deletedSingle, isTrue);

      await api.clearNotifications();
      expect(clearedAll, isTrue);
    });

    test('triggerManualCheck envia POST e retorna resultado', () async {
      final mockClient = MockClient((request) async {
        if (request.url.path == '/api/routine/run-check' && request.method == 'POST') {
          return http.Response(
            jsonEncode({
              'status': 'ok',
              'checkedCount': 2,
              'newChaptersFound': 1,
              'results': []
            }),
            200,
          );
        }
        return http.Response('Not Found', 404);
      });

      final api = ApiService(client: mockClient, storageService: FakeStorageService());
      final res = await api.triggerManualCheck(checkAll: true);
      expect(res['status'], 'ok');
      expect(res['checkedCount'], 2);
      expect(res['newChaptersFound'], 1);
    });
  });
}
