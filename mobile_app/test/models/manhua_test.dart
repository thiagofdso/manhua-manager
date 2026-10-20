import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/models/manhua.dart';

void main() {
  group('Manhua Model Test', () {
    test('deve deserializar JSON corretamente', () {
      final json = {
        'id': 1,
        'title': 'Overgeared',
        'urlTemplate': 'https://asurascans.com/comics/overgeared-11fe7da3/chapter/{chapter}',
        'currentChapter': 203,
        'updatedAt': 1792465472,
      };

      final manhua = Manhua.fromJson(json);

      expect(manhua.id, 1);
      expect(manhua.title, 'Overgeared');
      expect(manhua.currentChapter, 203);
      expect(
        manhua.targetUrlForChapter(204),
        'https://asurascans.com/comics/overgeared-11fe7da3/chapter/204',
      );
    });

    test('deve serializar para JSON', () {
      final manhua = Manhua(
        id: 2,
        title: 'Solo Leveling',
        urlTemplate: 'https://exemplo.com/chapter-{chapter}',
        currentChapter: 10,
      );

      final json = manhua.toJson();
      expect(json['id'], 2);
      expect(json['title'], 'Solo Leveling');
      expect(json['currentChapter'], 10);
    });

    test('deve criar copia com copyWith', () {
      final manhua = Manhua(
        id: 1,
        title: 'Overgeared',
        urlTemplate: 'https://asurascans.com/comics/overgeared-11fe7da3/chapter/{chapter}',
        currentChapter: 203,
      );

      final updated = manhua.copyWith(currentChapter: 204);
      expect(updated.currentChapter, 204);
      expect(updated.title, 'Overgeared');
    });
  });
}
