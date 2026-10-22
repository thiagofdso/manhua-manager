import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/controllers/manhua_controller.dart';
import 'package:mobile_app/models/manhua.dart';
import 'package:mobile_app/screens/reader_screen.dart';
import 'package:mobile_app/services/download_service.dart';

class MockManhuaController extends ChangeNotifier implements ManhuaController {
  @override
  List<Manhua> manhuas = [];

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class FakeDownloadService extends DownloadService {
  @override
  Future<bool> hasChapter(int manhuaId, int chapter) async => false;

  @override
  Future<List<String>> getChapterImagePaths(int manhuaId, int chapter) async => [];
}

void main() {
  testWidgets('ReaderScreen desativa botão Próximo quando no último episódio', (tester) async {
    final manhua = Manhua(
      id: 1,
      title: 'Solo Leveling',
      urlTemplate: 'https://test.com/{chapter}',
      currentChapter: 15,
      lastChapter: 15,
    );

    await tester.pumpWidget(
      MaterialApp(
        home: ChangeNotifierProvider<ManhuaController>.value(
          value: MockManhuaController(),
          child: ReaderScreen(
            manhua: manhua,
            downloadService: FakeDownloadService(),
          ),
        ),
      ),
    );
    await tester.pump();

    // Botão Anterior ativo (capítulo 15 > 1)
    final prevBtn = tester.widget<ElevatedButton>(find.widgetWithText(ElevatedButton, 'Anterior'));
    expect(prevBtn.onPressed, isNotNull);

    // Botão Próximo deve estar desabilitado pois 15 == lastChapter
    final nextBtn = tester.widget<ElevatedButton>(find.widgetWithText(ElevatedButton, 'Próximo'));
    expect(nextBtn.onPressed, isNull);
  });
}
