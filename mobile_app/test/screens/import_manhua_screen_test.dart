import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/models/import_domain.dart';
import 'package:mobile_app/models/import_work_item.dart';
import 'package:mobile_app/screens/import_manhua_screen.dart';
import 'package:mobile_app/services/api_service.dart';

class FakeApiService extends Fake implements ApiService {
  @override
  Future<List<ImportDomain>> fetchImportDomains() async {
    return [
      ImportDomain(domain: 'asurascans.com', name: 'Asura Scans', supported: true),
      ImportDomain(domain: 'mangafire.to', name: 'MangaFire', supported: false),
    ];
  }

  @override
  Future<ImportBrowseResult> browseImportWorks({required String domain, String? query, int page = 1}) async {
    return ImportBrowseResult(
      domain: domain,
      page: 1,
      totalPages: 1,
      items: [
        ImportWorkItem(title: 'Solo Comic', urlTemplate: 'solo_url', lastChapter: 40, alreadyExists: false),
        ImportWorkItem(title: 'Existing Comic', urlTemplate: 'exist_url', lastChapter: 100, alreadyExists: true),
      ],
    );
  }

  @override
  Future<ImportResponse> importWorks(List<ImportWorkItem> items) async {
    return ImportResponse(status: 'ok', imported: items.length, skipped: 0);
  }
}

void main() {
  testWidgets('ImportManhuaScreen renders domain selector, search, and work items', (tester) async {
    final fakeApi = FakeApiService();

    await tester.pumpWidget(
      MaterialApp(
        home: ImportManhuaScreen(apiService: fakeApi),
      ),
    );

    // Initial pump and wait for domains to load
    await tester.pumpAndSettle();

    expect(find.text('Importar Obras'), findsOneWidget);
    expect(find.text('Asura Scans'), findsWidgets);

    // Tap Pesquisar
    await tester.tap(find.text('Pesquisar'));
    await tester.pumpAndSettle();

    // Check items displayed in compact list
    expect(find.text('Solo Comic'), findsOneWidget);
    expect(find.text('Cap. 40'), findsOneWidget);
    expect(find.text('Existing Comic'), findsOneWidget);
    expect(find.text('Já cadastrada'), findsOneWidget);

    // Check Select All
    expect(find.text('Selecionar todos'), findsOneWidget);
    await tester.tap(find.text('Selecionar todos'));
    await tester.pumpAndSettle();

    // Check Import button enabled with 1 selected (since Existing Comic is disabled)
    expect(find.text('Importar (1)'), findsOneWidget);
  });
}
