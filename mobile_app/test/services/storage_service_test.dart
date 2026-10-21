import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:mobile_app/services/storage_service.dart';
import 'package:mobile_app/models/manhua.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('saveCachedManhuas e getCachedManhuas persistem e recuperam obras', () async {
    SharedPreferences.setMockInitialValues({});
    final storage = StorageService();

    final original = [
      Manhua(id: 1, title: 'Solo Leveling', urlTemplate: 'https://test/{chapter}', currentChapter: 10),
      Manhua(id: 2, title: 'Overgeared', urlTemplate: 'https://test2/{chapter}', currentChapter: 20, isFavorite: true),
    ];

    await storage.saveCachedManhuas(original);
    final cached = await storage.getCachedManhuas();

    expect(cached.length, 2);
    expect(cached[0].title, 'Solo Leveling');
    expect(cached[1].isFavorite, true);
  });
}
