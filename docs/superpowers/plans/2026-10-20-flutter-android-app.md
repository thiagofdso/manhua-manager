# Flutter Android App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Desenvolver um aplicativo móvel em Flutter para Android no diretório `mobile_app/`, integrado ao backend via Tailscale (`http://100.84.57.79:5000`), com gerenciamento completo de manhuas, leitor contínuo vertical webtoon e navegação entre episódios via gesto de arrastar (swipe horizontal).

**Architecture:** Flutter com arquitetura em camadas (Models, Services, ChangeNotifier Controller, UI Screens). HTTP REST com fallback e proxying de imagens. Armazenamento local com `shared_preferences`. Gesto `onHorizontalDragEnd` no leitor.

**Tech Stack:** Flutter 3+, Dart, Provider, HTTP, Shared Preferences, Cached Network Image, Android SDK.

## Global Constraints

- O projeto móvel deve residir em `mobile_app/` dentro deste repositório.
- A URL padrão do backend deve ser `http://100.84.57.79:5000` (Tailscale) com possibilidade de alteração em tela.
- Leitor no estilo Webtoon (rolagem contínua vertical sem quebras).
- Gestos: swipe horizontal para trocar de capítulo (esquerda: próximo; direita: anterior).
- Manter TDD com testes de unidade (`flutter test`) em cada etapa.

---

### Task 1: Inicialização do Projeto Flutter em `mobile_app/`

**Files:**
- Create: `mobile_app/pubspec.yaml`
- Create: `mobile_app/android/app/src/main/AndroidManifest.xml`
- Create: `mobile_app/lib/main.dart`

**Interfaces:**
- Produces: Estrutura base de compilação Flutter e dependências instaladas (`http`, `provider`, `shared_preferences`, `cached_network_image`).

- [x] **Step 1: Criar scaffold do projeto Flutter**

Executar comando para inicializar o app Flutter em `mobile_app/`:
```bash
/home/thiagofdso/development/flutter/bin/flutter create --org com.manhuamanager --project-name mobile_app mobile_app
```

- [x] **Step 2: Configurar dependências no `pubspec.yaml`**

Adicionar ao `mobile_app/pubspec.yaml`:
```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.2.0
  provider: ^6.1.1
  shared_preferences: ^2.2.2
  cached_network_image: ^3.3.1
  cupertino_icons: ^1.0.6

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.0
```

- [x] **Step 3: Configurar permissão de internet no `AndroidManifest.xml`**

No `mobile_app/android/app/src/main/AndroidManifest.xml`, adicionar antes de `<application>`:
```xml
    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>
```

- [x] **Step 4: Executar `flutter pub get`**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter pub get`  
Expected: Process finished with exit code 0.

- [x] **Step 5: Commit**

```bash
git add mobile_app/
git commit -m "chore: scaffold flutter project in mobile_app with android configuration"
```

---

### Task 2: Modelo de Dados `Manhua` e Testes Unitários

**Files:**
- Create: `mobile_app/lib/models/manhua.dart`
- Create: `mobile_app/test/models/manhua_test.dart`

**Interfaces:**
- Produces:
  - Classe `Manhua` com serialização JSON, imutabilidade com `copyWith` e método `targetUrlForChapter(int chapter)`.

- [x] **Step 1: Escrever teste unitário que falha**

Criar `mobile_app/test/models/manhua_test.dart`:
```dart
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
  });
}
```

- [x] **Step 2: Executar teste para verificar falha**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/models/manhua_test.dart`  
Expected: FAIL (Target of URI doesn't exist: 'package:mobile_app/models/manhua.dart').

- [x] **Step 3: Implementar `Manhua`**

Criar `mobile_app/lib/models/manhua.dart`:
```dart
class Manhua {
  final int id;
  final String title;
  final String urlTemplate;
  final int currentChapter;
  final int? updatedAt;

  Manhua({
    required this.id,
    required this.title,
    required this.urlTemplate,
    required this.currentChapter,
    this.updatedAt,
  });

  factory Manhua.fromJson(Map<String, dynamic> json) {
    return Manhua(
      id: json['id'] as int,
      title: json['title'] as String,
      urlTemplate: json['urlTemplate'] as String,
      currentChapter: json['currentChapter'] as int,
      updatedAt: json['updatedAt'] as int?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'urlTemplate': urlTemplate,
      'currentChapter': currentChapter,
      if (updatedAt != null) 'updatedAt': updatedAt,
    };
  }

  String targetUrlForChapter(int chapter) {
    return urlTemplate.replaceAll('{chapter}', chapter.toString());
  }

  Manhua copyWith({
    int? id,
    String? title,
    String? urlTemplate,
    int? currentChapter,
    int? updatedAt,
  }) {
    return Manhua(
      id: id ?? this.id,
      title: title ?? this.title,
      urlTemplate: urlTemplate ?? this.urlTemplate,
      currentChapter: currentChapter ?? this.currentChapter,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}
```

- [x] **Step 4: Executar teste para verificar aprovação**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/models/manhua_test.dart`  
Expected: PASS (All tests passed!).

- [x] **Step 5: Commit**

```bash
git add mobile_app/lib/models/ mobile_app/test/models/
git commit -m "feat: add Manhua model with json serialization and url formatting"
```

---

### Task 3: Serviços de Armazenamento e API REST (`StorageService` e `ApiService`)

**Files:**
- Create: `mobile_app/lib/services/storage_service.dart`
- Create: `mobile_app/lib/services/api_service.dart`
- Create: `mobile_app/test/services/api_service_test.dart`

**Interfaces:**
- Produces:
  - `StorageService.getBaseUrl()` / `StorageService.setBaseUrl(String url)` (padrão `http://100.84.57.79:5000`).
  - `ApiService.fetchManhuas() -> Future<List<Manhua>>`
  - `ApiService.updateChapterDelta(int id, int delta) -> Future<Manhua>`
  - `ApiService.updateManhua(int id, {String? title, String? urlTemplate, int? chapter}) -> Future<Manhua>`
  - `ApiService.addManhua(...) -> Future<Manhua>`
  - `ApiService.deleteManhua(int id) -> Future<void>`
  - `ApiService.fetchChapterImages(String targetUrl) -> Future<List<String>>`
  - `ApiService.getProxyImageUrl(String rawImageUrl) -> String`

- [x] **Step 1: Escrever teste unitário de serviços**

Criar `mobile_app/test/services/api_service_test.dart` utilizando mock client de `http`.

- [x] **Step 2: Executar teste para verificar falha**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/services/api_service_test.dart`  
Expected: FAIL.

- [x] **Step 3: Implementar `StorageService` e `ApiService`**

Implementar `storage_service.dart` com SharedPreferences e `api_service.dart` consumindo os endpoints `/api/manhuas`, `/api/chapter-images`, `/api/proxy-image`.

- [x] **Step 4: Executar teste para verificar aprovação**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/services/api_service_test.dart`  
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add mobile_app/lib/services/ mobile_app/test/services/
git commit -m "feat: add StorageService and ApiService with tailscale backend integration"
```

---

### Task 4: Gerenciador de Estado (`ManhuaController`)

**Files:**
- Create: `mobile_app/lib/controllers/manhua_controller.dart`
- Create: `mobile_app/test/controllers/manhua_controller_test.dart`

**Interfaces:**
- Consumes: `ApiService`, `StorageService`.
- Produces: `ManhuaController` herdando de `ChangeNotifier` com estados reativos (`isLoading`, `errorMessage`, `manhuas`, `changeChapter`, `refreshManhuas`).

- [x] **Step 1: Escrever teste unitário do controller**
- [x] **Step 2: Executar teste para verificar falha**
- [x] **Step 3: Implementar `ManhuaController`**
- [x] **Step 4: Executar teste para verificar aprovação**
- [x] **Step 5: Commit**

---

### Task 5: Telas da Aplicação e Gesto de Navegação

**Files:**
- Create: `mobile_app/lib/screens/home_screen.dart`
- Create: `mobile_app/lib/screens/reader_screen.dart`
- Create: `mobile_app/lib/screens/widgets/settings_dialog.dart`
- Create: `mobile_app/lib/screens/widgets/add_manhua_dialog.dart`
- Create: `mobile_app/lib/screens/widgets/edit_manhua_dialog.dart`
- Modify: `mobile_app/lib/main.dart`

**Interfaces:**
- Produces:
  - `HomeScreen`: Interface com lista de obras, botões rápidos `-1` e `+1`, botão de leitor `👁️`, menu de edição/exclusão e diálogo de IP.
  - `ReaderScreen`: Leitor vertical contínuo com `GestureDetector` para troca de capítulo ao arrastar para os lados (`onHorizontalDragEnd`).

- [x] **Step 1: Implementar telas e widgets**
- [x] **Step 2: Escrever widget test para `HomeScreen` e `ReaderScreen`**
- [x] **Step 3: Executar widget tests para validar renderização**
- [x] **Step 4: Commit**

---

### Task 6: Compilação do Pacote Android (APK)

**Files:**
- Modify: `mobile_app/android/app/build.gradle`

- [x] **Step 1: Configurar build Android e Gradle**
- [x] **Step 2: Executar build do APK**
  Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter build apk --debug`
  Expected: APK gerado em `mobile_app/build/app/outputs/flutter-apk/app-debug.apk`.
- [x] **Step 3: Verificar integridade do binário APK gerado**
- [x] **Step 4: Commit**

---

### Task 7: Validação Completa do Sistema

- [x] **Step 1: Executar suíte completa de testes no Flutter (`flutter test`)**
- [x] **Step 2: Executar suíte completa de testes no backend (`make test`)**
- [x] **Step 3: Testar comunicação do aplicativo com o serviço local/Tailscale**
