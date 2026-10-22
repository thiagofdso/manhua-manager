# Validação do Último Episódio na Função de Download Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Impedir que downloads de capítulos ultrapassem o último episódio lançado (`lastChapter`), sugerir valores coerentes nos formulários e validar os limites tanto no cliente (Web e Mobile) quanto na API backend.

**Architecture:** Validação em três camadas: no backend (`/api/manhuas/<id>/batch-chapter-images`) rejeitando com HTTP 400 se `start` ou `end` exceder `lastChapter`; na interface web (`index.html`) ajustando o teto inicial sugerido e bloqueando com alerta antes do disparo; e no Flutter (`download_manhua_dialog.dart` e `download_manager.dart`) ajustando a sugestão inicial, bloqueando com `SnackBar` e executando guarda defensiva.

**Tech Stack:** Python 3 (Flask, pytest), Vanilla JavaScript (PWA / IndexedDB), Flutter / Dart (Provider, widget tests).

## Global Constraints
- Ambiente Python virtual: `./.venv/bin/python` e `./.venv/bin/pytest`.
- Ambiente Flutter: `/home/thiagofdso/development/flutter/bin/flutter`.
- Serviço do sistema: `systemctl --user restart manhua-manager.service`.
- URLs e templates: preservar `{chapter}`.

---

### Task 1: Backend Validation for Batch Chapter Images

**Files:**
- Modify: `server.py:801-830`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `GET /api/manhuas/<int:item_id>/batch-chapter-images?start=<start>&end=<end>`
- Produces: HTTP 400 com `{"error": "Capítulo excede o último episódio disponível (<lastChapter>)"}` se `start > lastChapter` ou `end > lastChapter`.

- [ ] **Step 1: Escrever teste de falha para a validação no backend**

Adicionar em `tests/test_server.py`:

```python
def test_batch_chapter_images_exceeding_last_chapter_returns_400(client, sample_db):
    # Overgeared tem id=1. Definir lastChapter=245
    with open(DB_FILE, "r") as f:
        data = json.load(f)
    data[0]["lastChapter"] = 245
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

    # Requisitar intervalo que excede lastChapter (ex: 240 a 246)
    res = client.get("/api/manhuas/1/batch-chapter-images?start=240&end=246")
    assert res.status_code == 400
    assert "Capítulo excede o último episódio disponível" in res.get_json()["error"]
```

- [ ] **Step 2: Executar teste para verificar que falha**

Run: `./.venv/bin/pytest tests/test_server.py -k test_batch_chapter_images_exceeding_last_chapter_returns_400`  
Expected: FAIL (retorna 200 ou tenta extrair em vez de retornar 400).

- [ ] **Step 3: Implementar validação de `lastChapter` em `server.py`**

Em `server.py`, dentro de `get_batch_chapter_images(item_id)`:

```python
    if (end - start + 1) > 50:
        return jsonify({"error": "Limite máximo de 50 capítulos por lote excedido"}), 400

    last_chap = manhua.get("lastChapter")
    if last_chap is not None and (start > last_chap or end > last_chap):
        return jsonify({"error": f"Capítulo excede o último episódio disponível ({last_chap})"}), 400
```

- [ ] **Step 4: Executar testes de backend e verificar sucesso**

Run: `./.venv/bin/pytest tests/test_server.py`  
Expected: Todos os testes passando (PASS).

- [ ] **Step 5: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat(backend): validate lastChapter limit in batch chapter images endpoint"
```

---

### Task 2: Web Interface Download Limit Validation and Form Defaults

**Files:**
- Modify: `index.html:1350-1375`, `index.html:1469-1495`
- Test: `tests/test_web_interface.py`

**Interfaces:**
- Consumes: Objeto `m` de `manhuas` com `currentChapter` e `lastChapter`.
- Produces: `downloadEndChapter` padrão limitado a `lastChapter`, atributo `max` dinâmico e validação impeditiva em `startBatchDownload`.

- [ ] **Step 1: Adicionar teste para validação de download no web interface**

Adicionar em `tests/test_web_interface.py`:

```python
def test_web_index_contains_download_last_chapter_validation():
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Validação no startBatchDownload e ajuste de max no openDownloadModal
    assert "m.lastChapter != null" in html
    assert "ultrapassar o último episódio disponível" in html
```

- [ ] **Step 2: Executar teste para verificar que falha**

Run: `./.venv/bin/pytest tests/test_web_interface.py -k test_web_index_contains_download_last_chapter_validation`  
Expected: FAIL.

- [ ] **Step 3: Implementar ajuste no `openDownloadModal` e `startBatchDownload` em `index.html`**

No `openDownloadModal(id, event)` em `index.html`:
```javascript
      const maxChap = m.lastChapter;
      const startVal = m.currentChapter || 1;
      let defaultEnd = startVal + 4;
      if (maxChap != null) {
        defaultEnd = Math.min(defaultEnd, maxChap);
        if (defaultEnd < startVal) defaultEnd = startVal;
      }

      if (task) {
        document.getElementById('downloadStartChapter').value = task.start;
        document.getElementById('downloadEndChapter').value = task.end;
      } else {
        document.getElementById('downloadStartChapter').value = startVal;
        document.getElementById('downloadEndChapter').value = defaultEnd;
      }

      if (maxChap != null) {
        document.getElementById('downloadStartChapter').max = maxChap;
        document.getElementById('downloadEndChapter').max = maxChap;
      } else {
        document.getElementById('downloadStartChapter').removeAttribute('max');
        document.getElementById('downloadEndChapter').removeAttribute('max');
      }
```

No `startBatchDownload()` em `index.html`:
```javascript
      if (isNaN(start) || isNaN(end) || start < 1 || end < start) {
        alert('Por favor, informe um intervalo válido (Capítulo inicial >= 1 e <= Capítulo final).');
        return;
      }

      if (m.lastChapter != null && (start > m.lastChapter || end > m.lastChapter)) {
        alert(`O intervalo não pode ultrapassar o último episódio disponível (${m.lastChapter}).`);
        return;
      }

      if ((end - start + 1) > 50) {
        alert('O limite máximo por lote é de 50 capítulos.');
        return;
      }
```

- [ ] **Step 4: Executar testes para verificar que passam**

Run: `./.venv/bin/pytest tests/test_web_interface.py`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add index.html tests/test_web_interface.py
git commit -m "feat(web): validate lastChapter in batch download modal and cap suggested range"
```

---

### Task 3: Mobile App Download Validation and Suggested Limit

**Files:**
- Modify: `mobile_app/lib/screens/widgets/download_manhua_dialog.dart:35-45`, `mobile_app/lib/screens/widgets/download_manhua_dialog.dart:90-110`
- Modify: `mobile_app/lib/services/download_manager.dart:36-50`
- Test: `mobile_app/test/screens/download_manhua_dialog_test.dart`

**Interfaces:**
- Consumes: `widget.manhua.lastChapter`.
- Produces: `_endController` padrão limitado, bloqueio em `_startDownload` com `SnackBar`, e guarda em `DownloadManager.startDownload`.

- [ ] **Step 1: Escrever teste de widget para o limite de download no mobile**

Adicionar em `mobile_app/test/screens/download_manhua_dialog_test.dart`:

```dart
  testWidgets('DownloadManhuaDialog bloqueia download e exibe snackbar quando excede lastChapter', (tester) async {
    final mockApiService = MockApiService();
    final mockDownloadService = MockDownloadService();
    final controller = ManhuaController(apiService: mockApiService);
    final downloadManager = DownloadManager();

    final testManhua = Manhua(
      id: 99,
      title: 'Obra Limitada',
      urlTemplate: 'https://exemplo.com/{chapter}',
      currentChapter: 10,
      lastChapter: 12,
    );

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<ManhuaController>.value(value: controller),
          ChangeNotifierProvider<DownloadManager>.value(value: downloadManager),
        ],
        child: MaterialApp(
          home: Scaffold(
            body: DownloadManhuaDialog(
              manhua: testManhua,
              downloadService: mockDownloadService,
              downloadManager: downloadManager,
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // Verifica que o fim sugerido não ultrapassou o lastChapter (12)
    final endFinder = find.widgetWithText(TextField, '12');
    expect(endFinder, findsOneWidget);

    // Tenta digitar um capítulo final além do limite (15)
    await tester.enterText(endFinder, '15');
    await tester.pumpAndSettle();

    // Clica em Iniciar Download
    await tester.tap(find.text('Iniciar Download'));
    await tester.pumpAndSettle();

    // Verifica mensagem de bloqueio no SnackBar
    expect(find.textContaining('O intervalo não pode ultrapassar o último episódio disponível (12)'), findsOneWidget);
    // Verifica que nenhuma tarefa de download foi iniciada
    expect(downloadManager.isDownloading(99), isFalse);
  });
```

- [ ] **Step 2: Executar teste Flutter para verificar falha**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/screens/download_manhua_dialog_test.dart`  
Expected: FAIL.

- [ ] **Step 3: Implementar validação e ajuste de teto em `download_manhua_dialog.dart` e `download_manager.dart`**

Em `mobile_app/lib/screens/widgets/download_manhua_dialog.dart`:
```dart
  @override
  void initState() {
    super.initState();
    _downloadService = widget.downloadService ?? DownloadService();
    final startChap = widget.manhua.currentChapter > 0 ? widget.manhua.currentChapter : 1;
    _startController = TextEditingController(text: startChap.toString());
    
    final last = widget.manhua.lastChapter;
    var endChap = startChap + 4;
    if (last != null) {
      if (endChap > last) {
        endChap = (startChap > last) ? startChap : last;
      }
    }
    _endController = TextEditingController(text: endChap.toString());
    _loadDownloadedChapters();
  }
```

E em `_startDownload`:
```dart
    if (start == null || end == null || start < 1 || end < start) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, informe um intervalo válido (Início >= 1 e <= Fim).')),
      );
      return;
    }

    if (widget.manhua.lastChapter != null) {
      final last = widget.manhua.lastChapter!;
      if (start > last || end > last) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('O intervalo não pode ultrapassar o último episódio disponível ($last).')),
        );
        return;
      }
    }

    if ((end - start + 1) > 50) {
```

Em `mobile_app/lib/services/download_manager.dart`:
```dart
  Future<void> startDownload({
    required Manhua manhua,
    required int startChapter,
    required int endChapter,
    required ApiService apiService,
    required DownloadService downloadService,
  }) async {
    if (isDownloading(manhua.id)) return;
    if (manhua.lastChapter != null && (startChapter > manhua.lastChapter! || endChapter > manhua.lastChapter!)) {
      return;
    }
```

- [ ] **Step 4: Executar testes Flutter para verificar sucesso**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`  
Expected: Todos os testes passando (PASS).

- [ ] **Step 5: Commit**

```bash
git add mobile_app/lib/screens/widgets/download_manhua_dialog.dart mobile_app/lib/services/download_manager.dart mobile_app/test/screens/download_manhua_dialog_test.dart
git commit -m "feat(mobile): validate lastChapter in DownloadManhuaDialog and cap suggested end chapter"
```

---

### Task 4: System Verification, Service Restart and APK Generation

**Files:**
- Output: `mobile_app/build/app/outputs/flutter-apk/app-release.apk`
- Output: `mobile_app/build/app/outputs/flutter-apk/app-debug.apk`

- [ ] **Step 1: Executar suíte completa de testes backend**

Run: `./.venv/bin/pytest tests/`  
Expected: 63/63 tests PASS.

- [ ] **Step 2: Executar suíte completa de testes mobile**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`  
Expected: 43/43 tests PASS.

- [ ] **Step 3: Reiniciar serviço systemd**

Run: `systemctl --user restart manhua-manager.service`  
Verify: `systemctl --user status manhua-manager.service --no-pager` (Active: active (running)).

- [ ] **Step 4: Recompilar APKs**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter build apk --release`  
Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter build apk --debug`  
Expected: APKs compilados com sucesso.
