import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/screens/widgets/storage_management_dialog.dart';
import 'package:mobile_app/services/download_service.dart';

class FakeDownloadService extends DownloadService {
  int totalDownloaded = 2;

  @override
  Future<int> getTotalDownloadedCount() async => totalDownloaded;

  @override
  Future<void> clearAllDownloads() async {
    totalDownloaded = 0;
  }
}

void main() {
  testWidgets('StorageManagementDialog exibe contagem e limpa downloads com confirmação', (tester) async {
    final downloadService = FakeDownloadService();

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: StorageManagementDialog(downloadService: downloadService),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Armazenamento Offline'), findsOneWidget);
    expect(find.text('2 capítulos baixados no dispositivo.'), findsOneWidget);
    expect(find.text('Limpar Todos os Downloads'), findsOneWidget);

    // Clicar em limpar
    await tester.tap(find.text('Limpar Todos os Downloads'));
    await tester.pumpAndSettle();

    // Diálogo de confirmação aberto
    expect(find.text('Confirmar Limpeza'), findsOneWidget);

    // Confirmar limpeza
    await tester.tap(find.text('Limpar'));
    await tester.pumpAndSettle();

    expect(await downloadService.getTotalDownloadedCount(), 0);
    expect(find.text('0 capítulos baixados no dispositivo.'), findsOneWidget);
  });
}
