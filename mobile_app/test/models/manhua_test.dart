import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/models/manhua.dart';

void main() {
  test('Manhua serializa e deserializa lastChapter, updateDay e isHiatus', () {
    final manhua = Manhua(
      id: 1,
      title: 'Solo Leveling',
      urlTemplate: 'https://asurascans.com/solo/{chapter}',
      currentChapter: 10,
      lastChapter: 15,
      updateDay: 4,
      isHiatus: true,
    );

    final json = manhua.toJson();
    expect(json['lastChapter'], 15);
    expect(json['updateDay'], 4);
    expect(json['isHiatus'], true);

    final parsed = Manhua.fromJson(json);
    expect(parsed.lastChapter, 15);
    expect(parsed.updateDay, 4);
    expect(parsed.isHiatus, true);
  });

  test('Manhua default values para campos novos', () {
    final parsed = Manhua.fromJson({
      'id': 2,
      'title': 'Test',
      'urlTemplate': 'https://test.com/{chapter}',
      'currentChapter': 1,
    });
    expect(parsed.lastChapter, isNull);
    expect(parsed.updateDay, isNull);
    expect(parsed.isHiatus, isFalse);
  });
}
