# Background Downloads Queue and Cancellation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar o gerenciador global de downloads contínuos com cancelamento, reconexão de progresso nos diálogos das obras e fila de downloads ativos na tela principal tanto no Mobile (Flutter) quanto na Web.

**Architecture:** 
- Web (`index.html`): Gerenciador global `activeDownloads` em memória com suporte a `AbortController` para cancelamento instantâneo, reconexão de estado no modal da obra e modal `#activeDownloadsModal` com badge dinâmico no cabeçalho.
- Mobile (`mobile_app/`): Modelo `DownloadTask`, serviço reativo `DownloadManager` (ChangeNotifier) com tarefas em segundo plano e cancelamento seguro, `DownloadManhuaDialog` reconectado dinamicamente e `ActiveDownloadsDialog` acessível pela AppBar da `HomeScreen`.

**Tech Stack:** Vanilla JavaScript (AbortController, Fetch, IndexedDB), Flutter 3 / Dart (ChangeNotifier, Provider, flutter_test).

## Global Constraints

- Ambiente Python estrito: `./.venv/bin/python` e `./.venv/bin/pytest`.
- Ambiente Flutter estrito: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`.
- Preservar capítulos já 100% concluídos no disco/IndexedDB quando o download for cancelado.
- Reabrir o diálogo de uma obra em download deve reconectar imediatamente a barra de progresso no ponto atual.
- Zero limpeza automática.

---

### Task 1: Web - Global Active Downloads, Cancellation & Queue Modal (`index.html`)

**Files:**
- Modify: `index.html`
- Test: `tests/test_server.py`

**Interfaces:**
- Produces: 
  - `activeDownloads`: Objeto global mapeando `manhuaId` para tarefa de download ativa.
  - `startBatchDownload()`: Inicia tarefa no gerenciador com `AbortController` e atualiza a interface dinamicamente.
  - `cancelActiveDownload(manhuaId)`: Aborta as requisições em andamento e atualiza a interface.
  - `openActiveDownloadsModal()`: Exibe `#activeDownloadsModal` com a lista de todos os downloads ativos e suas barras de progresso.
  - Badge no cabeçalho: `#btnActiveDownloadsHeader` com indicador numérico.

- [ ] **Step 1: Write test for web active downloads elements in `tests/test_server.py`**

Adicionar teste em `tests/test_server.py`:
```python
def test_web_index_contains_active_downloads_queue_elements(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "activeDownloadsModal" in html
    assert "btnActiveDownloadsHeader" in html
    assert "cancelActiveDownload" in html
    assert "renderActiveDownloadsList" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/test_server.py -k test_web_index_contains_active_downloads_queue_elements -v`
Expected: FAIL

- [ ] **Step 3: Implement Web Active Downloads Queue and Cancellation in `index.html`**

Em `index.html`:
1. No cabeçalho de `listView`, adicionar botão dinâmico `#btnActiveDownloadsHeader` (oculto quando não houver downloads ativos).
2. Adicionar modal `#activeDownloadsModal` com lista `#activeDownloadsContainer`.
3. No script de `index.html`:
   - Estrutura `activeDownloads = {}`.
   - `updateActiveDownloadsHeaderBadge()`: Atualiza a visibilidade e texto do botão no topo.
   - Atualizar `startBatchDownload()` para registrar a tarefa em `activeDownloads[manhuaId]` com `AbortController`, checar `isCancelled`, e emitir atualizações de progresso para qualquer modal aberto.
   - `cancelActiveDownload(manhuaId)`: Seta `isCancelled = true`, chama `abortController.abort()`, remove da fila e atualiza o modal da obra e a fila global.
   - No `openDownloadModal(id)`: Se `activeDownloads[id]` estiver ativo, exibe barra de progresso e botão "Cancelar Download".

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/pytest tests/test_server.py -k test_web_index_contains_active_downloads_queue_elements -v`
Expected: PASS

- [ ] **Step 5: Run all backend tests**

Run: `./.venv/bin/pytest tests/`
Expected: 56 passed

- [ ] **Step 6: Commit**

```bash
git add index.html tests/test_server.py
git commit -m "feat(web): add global active downloads queue, reconnection and cancellation"
```

---

### Task 2: Mobile - `DownloadTask` Model & `DownloadManager` Service

**Files:**
- Create: `mobile_app/lib/models/download_task.dart`
- Create: `mobile_app/lib/services/download_manager.dart`
- Test: `mobile_app/test/services/download_manager_test.dart`

**Interfaces:**
- Produces: 
  - `DownloadTask`
  - `DownloadManager`:
    - `List<DownloadTask> get activeTasks`
    - `DownloadTask? getTask(int manhuaId)`
    - `Future<void> startDownload(Manhua manhua, int startChapter, int endChapter, ApiService apiService, DownloadService downloadService)`
    - `void cancelDownload(int manhuaId)`

- [ ] **Step 1: Write failing unit tests in `mobile_app/test/services/download_manager_test.dart`**

Testar criação de tarefa, atualização de progresso, cancelamento e conclusão.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/services/download_manager_test.dart`
Expected: FAIL (arquivos não existem)

- [ ] **Step 3: Implement `DownloadTask` and `DownloadManager`**

Criar `mobile_app/lib/models/download_task.dart` e `mobile_app/lib/services/download_manager.dart` com controle de `isCancelled`, emissão de `notifyListeners()` e persistência por capítulo concluído.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/services/download_manager_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mobile_app/lib/models/download_task.dart mobile_app/lib/services/download_manager.dart mobile_app/test/services/download_manager_test.dart
git commit -m "feat(mobile): implement DownloadTask model and DownloadManager service"
```

---

### Task 3: Mobile - Connect `DownloadManager` in Provider and `DownloadManhuaDialog`

**Files:**
- Modify: `mobile_app/lib/main.dart`
- Modify: `mobile_app/lib/screens/widgets/download_manhua_dialog.dart`
- Test: `mobile_app/test/screens/download_manhua_dialog_test.dart`

**Interfaces:**
- Consumes: `DownloadManager`, `DownloadService`, `ApiService`
- Produces: `DownloadManhuaDialog` que se reconecta a downloads ativos e fornece botão de cancelar.

- [ ] **Step 1: Write widget test for `DownloadManhuaDialog` with active task**

Verificar que se já houver tarefa ativa em `DownloadManager`, o diálogo exibe a barra e o botão "Cancelar Download".

- [ ] **Step 2: Register `DownloadManager` in `main.dart`**

Adicionar `ChangeNotifierProvider(create: (_) => DownloadManager())` no `MultiProvider` em `main.dart`.

- [ ] **Step 3: Update `DownloadManhuaDialog` to consume `DownloadManager`**

Se houver tarefa ativa para `widget.manhua.id`:
- Exibe o progresso em tempo real.
- Substitui "Iniciar Download" por "Cancelar Download".
- O botão "Fechar" fecha o diálogo sem interromper a tarefa.

- [ ] **Step 4: Run flutter tests**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mobile_app/lib/main.dart mobile_app/lib/screens/widgets/download_manhua_dialog.dart mobile_app/test/screens/download_manhua_dialog_test.dart
git commit -m "feat(mobile): integrate DownloadManager with DownloadManhuaDialog for continuous progress and cancellation"
```

---

### Task 4: Mobile - `ActiveDownloadsDialog` and Queue Badge on `HomeScreen`

**Files:**
- Create: `mobile_app/lib/screens/widgets/active_downloads_dialog.dart`
- Modify: `mobile_app/lib/screens/home_screen.dart`
- Test: `mobile_app/test/screens/active_downloads_dialog_test.dart`

**Interfaces:**
- Produces: 
  - `ActiveDownloadsDialog`: Diálogo com lista de todas as tarefas ativas, barra de progresso e botão individual de cancelamento.
  - Ícone na AppBar da `HomeScreen` com badge numérico quando `downloadManager.activeTasks.isNotEmpty`.

- [ ] **Step 1: Write test for `ActiveDownloadsDialog`**

Verificar listagem de downloads em andamento e ação de cancelar.

- [ ] **Step 2: Implement `ActiveDownloadsDialog` widget**

Criar `mobile_app/lib/screens/widgets/active_downloads_dialog.dart`.

- [ ] **Step 3: Add active downloads button/badge to `HomeScreen` AppBar**

Em `mobile_app/lib/screens/home_screen.dart`, exibir ícone de downloads ativos quando `downloadManager.activeTasks.isNotEmpty`.

- [ ] **Step 4: Run flutter tests**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mobile_app/lib/screens/widgets/active_downloads_dialog.dart mobile_app/lib/screens/home_screen.dart mobile_app/test/screens/active_downloads_dialog_test.dart
git commit -m "feat(mobile): add ActiveDownloadsDialog and queue badge on HomeScreen"
```

---

### Task 5: Verification, APK Generation and End-to-End System Health

**Files:**
- Rebuild APK: `mobile_app/build/app/outputs/flutter-apk/app-release.apk` and `app-debug.apk`
- Verify pytest: `./.venv/bin/pytest tests/`
- Verify flutter: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`

- [ ] **Step 1: Run complete backend pytest suite**

Run: `./.venv/bin/pytest tests/`
Expected: All tests pass.

- [ ] **Step 2: Run complete mobile flutter test suite**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`
Expected: All tests pass.

- [ ] **Step 3: Rebuild release APK**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter build apk --release`
Expected: `app-release.apk` built successfully.

- [ ] **Step 4: Rebuild debug APK**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter build apk --debug`
Expected: `app-debug.apk` built successfully.
