import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/controllers/manhua_controller.dart';
import 'package:mobile_app/models/manhua.dart';
import 'package:mobile_app/screens/widgets/add_manhua_dialog.dart';
import 'package:mobile_app/screens/widgets/edit_manhua_dialog.dart';

class MockManhuaController extends ChangeNotifier implements ManhuaController {
  String? lastAddedTitle;
  int? lastAddedLastChapter;
  int? lastAddedUpdateDay;
  bool? lastAddedIsHiatus;

  String? lastEditedTitle;
  int? lastEditedLastChapter;
  int? lastEditedUpdateDay;
  bool? lastEditedIsHiatus;

  @override
  Future<void> addManhua(
    String title,
    String urlTemplate,
    int currentChapter, {
    int? lastChapter,
    int? updateDay,
    bool isHiatus = false,
  }) async {
    lastAddedTitle = title;
    lastAddedLastChapter = lastChapter;
    lastAddedUpdateDay = updateDay;
    lastAddedIsHiatus = isHiatus;
  }

  @override
  Future<void> editManhua(
    int id, {
    String? title,
    String? urlTemplate,
    int? chapter,
    int? lastChapter,
    bool clearLastChapter = false,
    int? updateDay,
    bool clearUpdateDay = false,
    bool? isHiatus,
  }) async {
    lastEditedTitle = title;
    lastEditedLastChapter = lastChapter;
    lastEditedUpdateDay = updateDay;
    lastEditedIsHiatus = isHiatus;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  testWidgets('AddManhuaDialog exibe campos e salva com lastChapter, updateDay e isHiatus', (tester) async {
    final mock = MockManhuaController();

    await tester.pumpWidget(
      MaterialApp(
        home: ChangeNotifierProvider<ManhuaController>.value(
          value: mock,
          child: const Scaffold(body: AddManhuaDialog()),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Cadastrar Nova Obra'), findsOneWidget);
    expect(find.text('Dia de Atualização Semanal'), findsOneWidget);
    expect(find.text('Obra em Hiato'), findsOneWidget);

    // Preenche título, URL e capítulo inicial
    await tester.enterText(find.byType(TextFormField).at(0), 'Solo Leveling');
    await tester.enterText(find.byType(TextFormField).at(1), 'https://asurascans.com/solo/chapter/10');
    await tester.enterText(find.byType(TextFormField).at(2), '10');
    // Preenche último episódio
    await tester.enterText(find.byType(TextFormField).at(3), '15');

    // Seleciona quarta-feira (Qua - índice 2)
    await tester.tap(find.text('Qua'));
    await tester.pumpAndSettle();

    // Ativa switch de hiato
    await tester.ensureVisible(find.byType(SwitchListTile));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(SwitchListTile));
    await tester.pumpAndSettle();

    // Clica em salvar
    await tester.ensureVisible(find.text('Salvar'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Salvar'));
    await tester.pumpAndSettle();

    expect(mock.lastAddedTitle, 'Solo Leveling');
    expect(mock.lastAddedLastChapter, 15);
    expect(mock.lastAddedUpdateDay, 2);
    expect(mock.lastAddedIsHiatus, isTrue);
  });

  testWidgets('EditManhuaDialog inicializa com valores existentes e salva atualizações', (tester) async {
    final mock = MockManhuaController();
    final manhua = Manhua(
      id: 1,
      title: 'Overgeared',
      urlTemplate: 'https://asurascans.com/overgeared/chapter/{chapter}',
      currentChapter: 200,
      lastChapter: 245,
      updateDay: 4, // Sex
      isHiatus: true,
    );

    await tester.pumpWidget(
      MaterialApp(
        home: ChangeNotifierProvider<ManhuaController>.value(
          value: mock,
          child: Scaffold(body: EditManhuaDialog(manhua: manhua)),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Editar Obra'), findsOneWidget);
    expect(find.text('245'), findsOneWidget);

    // Altera último episódio para 250
    await tester.enterText(find.byType(TextFormField).at(3), '250');
    // Altera dia para Sáb (índice 5)
    await tester.tap(find.text('Sáb'));
    await tester.pumpAndSettle();

    // Desmarca hiato
    await tester.ensureVisible(find.byType(SwitchListTile));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(SwitchListTile));
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('Salvar'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Salvar'));
    await tester.pumpAndSettle();

    expect(mock.lastEditedLastChapter, 250);
    expect(mock.lastEditedUpdateDay, 5);
    expect(mock.lastEditedIsHiatus, isFalse);
  });
}
