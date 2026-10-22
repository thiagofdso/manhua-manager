import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/controllers/manhua_controller.dart';
import 'package:mobile_app/models/manhua.dart';
import 'package:mobile_app/screens/home_screen.dart';

class MockManhuaController extends ChangeNotifier implements ManhuaController {
  @override
  List<Manhua> manhuas = [
    Manhua(
      id: 1,
      title: 'Overgeared',
      urlTemplate: 'https://test.com/{chapter}',
      currentChapter: 245,
      lastChapter: 245, // No limite máximo
      updateDay: 4,
      isHiatus: false,
    ),
    Manhua(
      id: 2,
      title: 'Solo Leveling',
      urlTemplate: 'https://test.com/{chapter}',
      currentChapter: 10,
      lastChapter: 20, // Pode avançar
      updateDay: 1,
      isHiatus: false,
    ),
  ];

  @override
  bool isLoading = false;
  @override
  bool isOfflineMode = false;
  @override
  String? errorMessage;
  @override
  String baseUrl = 'http://test';
  @override
  List<Map<String, dynamic>> notifications = [
    {'id': 10, 'manhuaId': 2, 'title': 'Solo Leveling', 'chapter': 11}
  ];

  @override
  Future<void> loadManhuas() async {}

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  testWidgets('HomeScreen desativa botão +1 quando currentChapter >= lastChapter', (tester) async {
    final mock = MockManhuaController();

    await tester.pumpWidget(
      MaterialApp(
        home: ChangeNotifierProvider<ManhuaController>.value(
          value: mock,
          child: const HomeScreen(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Botão +1 da obra 1 (Overgeared, 245/245) deve estar desabilitado
    final addButtons = find.widgetWithIcon(IconButton, Icons.add_circle_outline);
    expect(addButtons, findsNWidgets(2));

    final IconButton overgearedAdd = tester.widget(addButtons.first);
    expect(overgearedAdd.onPressed, isNull);

    // Botão +1 da obra 2 (Solo Leveling, 10/20) deve estar ativo
    final IconButton soloAdd = tester.widget(addButtons.at(1));
    expect(soloAdd.onPressed, isNotNull);

    // Verifica presença do ícone de notificações
    expect(find.byIcon(Icons.notifications_outlined), findsOneWidget);
  });
}
