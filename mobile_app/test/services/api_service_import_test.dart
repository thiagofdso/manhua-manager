import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile_app/models/import_domain.dart';
import 'package:mobile_app/models/import_work_item.dart';
import 'package:mobile_app/services/api_service.dart';

void main() {
  group('ApiService Import Tests', () {
    test('fetchImportDomains parses domains correctly', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode([
            {"domain": "asurascans.com", "name": "Asura Scans", "supported": true},
            {"domain": "mangafire.to", "name": "MangaFire", "supported": false}
          ]),
          200,
        );
      });

      final api = ApiService(client: mockClient);
      final domains = await api.fetchImportDomains();
      expect(domains.length, 2);
      expect(domains[0].domain, 'asurascans.com');
      expect(domains[0].supported, true);
      expect(domains[1].supported, false);
    });

    test('browseImportWorks returns items and pagination', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({
            "status": "ok",
            "domain": "asurascans.com",
            "page": 1,
            "totalPages": 4,
            "items": [
              {
                "title": "Solo Comic",
                "urlTemplate": "https://asurascans.com/comics/solo/chapter/{chapter}",
                "lastChapter": 40,
                "alreadyExists": false,
                "domain": "asurascans.com",
                "domainName": "Asura Scans"
              },
              {
                "title": "Existing Comic",
                "urlTemplate": "https://asurascans.com/comics/existing/chapter/{chapter}",
                "lastChapter": 100,
                "alreadyExists": true
              }
            ]
          }),
          200,
        );
      });

      final api = ApiService(client: mockClient);
      final result = await api.browseImportWorks(domain: 'asurascans.com');
      expect(result.page, 1);
      expect(result.totalPages, 4);
      expect(result.items.length, 2);
      expect(result.items[0].alreadyExists, false);
      expect(result.items[0].domain, 'asurascans.com');
      expect(result.items[0].domainName, 'Asura Scans');
      expect(result.items[1].alreadyExists, true);
    });

    test('importWorks sends selected items and parses response', () async {
      final mockClient = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body['items'].length, 1);
        return http.Response(
          jsonEncode({"status": "ok", "imported": 1, "skipped": 0}),
          200,
        );
      });

      final api = ApiService(client: mockClient);
      final res = await api.importWorks([
        ImportWorkItem(
          title: 'Solo Comic',
          urlTemplate: 'https://asurascans.com/comics/solo/chapter/{chapter}',
          lastChapter: 40,
          alreadyExists: false,
        )
      ]);
      expect(res.imported, 1);
      expect(res.skipped, 0);
    });
  });
}
