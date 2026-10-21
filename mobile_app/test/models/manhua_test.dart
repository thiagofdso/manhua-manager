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

    test('deve suportar MangaFire com chapterId e navigation metadata', () {
      final json = {
        'id': 10,
        'title': 'Necromancer, the Ultimate Scourge!',
        'urlTemplate': 'https://mangafire.to/title/nk6zl-necromancer/chapter/{chapter}',
        'currentChapter': 306,
        'chapterId': 9427010,
        'nextChapter': {'id': 9442025, 'number': 307},
        'prevChapter': {'id': 9426675, 'number': 305},
      };

      final manhua = Manhua.fromJson(json);
      expect(manhua.chapterId, 9427010);
      expect(manhua.nextChapter?['id'], 9442025);
      expect(manhua.prevChapter?['id'], 9426675);

      // Current chapter uses chapterId for MangaFire
      expect(
        manhua.targetUrlForChapter(306),
        'https://mangafire.to/title/nk6zl-necromancer/chapter/9427010',
      );

      // Other chapter uses chapter number
      expect(
        manhua.targetUrlForChapter(307),
        'https://mangafire.to/title/nk6zl-necromancer/chapter/307',
      );

      final exported = manhua.toJson();
      expect(exported['chapterId'], 9427010);
      expect(exported['nextChapter']['number'], 307);
    });

    test('deve suportar Comix com chapterId e navigation metadata', () {
      final json = {
        'id': 20,
        'title': 'The Jobless Guy Who Has Come to Slay',
        'urlTemplate': 'https://comix.to/title/q8qxd-the-jobless-guy-who-has-come-to-slay/{chapter}',
        'currentChapter': 231,
        'chapterId': 11349222,
        'nextChapter': {'id': 11385174, 'number': 232, 'url': 'https://comix.to/title/q8qxd-the-jobless-guy-who-has-come-to-slay/11385174-chapter-232'},
        'prevChapter': {'id': 11323925, 'number': 230, 'url': 'https://comix.to/title/q8qxd-the-jobless-guy-who-has-come-to-slay/11323925-chapter-230'},
      };

      final manhua = Manhua.fromJson(json);
      expect(manhua.chapterId, 11349222);
      expect(manhua.nextChapter?['id'], 11385174);
      expect(manhua.prevChapter?['id'], 11323925);

      // Current chapter uses chapterId-chapter-number for Comix
      expect(
        manhua.targetUrlForChapter(231),
        'https://comix.to/title/q8qxd-the-jobless-guy-who-has-come-to-slay/11349222-chapter-231',
      );

      // Other chapter uses chapter number
      expect(
        manhua.targetUrlForChapter(232),
        'https://comix.to/title/q8qxd-the-jobless-guy-who-has-come-to-slay/232',
      );
    });

    test('deve suportar isFavorite e customOrder no fromJson e toJson', () {
      final json = {
        'id': 30,
        'title': 'Favorite Manhua',
        'urlTemplate': 'https://exemplo.com/{chapter}',
        'currentChapter': 1,
        'isFavorite': true,
        'customOrder': 5,
      };

      final manhua = Manhua.fromJson(json);
      expect(manhua.isFavorite, true);
      expect(manhua.customOrder, 5);

      final exported = manhua.toJson();
      expect(exported['isFavorite'], true);
      expect(exported['customOrder'], 5);
    });

    test('deve assumir isFavorite como false quando ausente', () {
      final json = {
        'id': 31,
        'title': 'Regular Manhua',
        'urlTemplate': 'https://exemplo.com/{chapter}',
        'currentChapter': 1,
      };

      final manhua = Manhua.fromJson(json);
      expect(manhua.isFavorite, false);
      expect(manhua.customOrder, null);
    });
  });
}
