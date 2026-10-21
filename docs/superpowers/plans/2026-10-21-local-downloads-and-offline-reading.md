# Download Local de Capítulos e Leitura Offline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar a funcionalidade de download local de episódios por faixa (range) e leitura offline no Web e Mobile (Flutter), com verificação local prévia no leitor, cópia em cache das obras no mobile, solicitação de permissão de disco e gerenciamento manual sem limpeza automática.

**Architecture:** 
- Backend: Endpoint `/api/manhuas/<id>/batch-chapter-images` extrai em lote via `ThreadPoolExecutor` e entrega JSON com imagens por capítulo.
- Web: Armazenamento em `IndexedDB` nativo com Blobs para leitura instantânea offline no leitor e modal de gerenciamento.
- Mobile: `DownloadService` com `path_provider` armazenando imagens em disco local, `StorageService` com fallback offline de catálogo, `permission_handler` na inicialização e `ReaderScreen` prioritariamente local (`Image.file`).

**Tech Stack:** Python 3.14 (Flask, ThreadPoolExecutor, pytest), Vanilla JavaScript (IndexedDB, Fetch API), Flutter 3 / Dart (path_provider, permission_handler, shared_preferences, provider, flutter_test).

## Global Constraints

- Ambiente Python estrito: `./.venv/bin/python` e `./.venv/bin/pytest`.
- Ambiente Flutter estrito: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`.
- Preservar o placeholder `{chapter}` nos templates de URL.
- Zero limpeza automática: nenhum capítulo baixado deve expirar ou ser excluído automaticamente.
- Verificação local prioritária no Leitor Web e Mobile antes de qualquer requisição ao backend.

---

### Task 1: Backend - Batch Chapter Images Endpoint (`server.py`)

**Files:**
- Modify: `server.py`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `load_data()`, `extract_chapter_images_by_domain()`, `extract_html_navigation()`, domain providers (`mangafire_provider`, `comix_provider`, `manhuaus_provider`).
- Produces: `GET /api/manhuas/<int:item_id>/batch-chapter-images?start=<int>&end=<int>` returning JSON:
  ```json
  {
    "manhuaId": 1,
    "title": "...",
    "range": { "start": 10, "end": 12 },
    "totalChapters": 3,
    "chapters": [
      { "chapter": 10, "targetUrl": "...", "images": ["..."] }
    ]
  }
  ```

- [ ] **Step 1: Write failing tests in `tests/test_server.py`**

Adicionar ao final de `tests/test_server.py`:
```python
def test_batch_chapter_images_validation(client):
    # Obra inexistente
    res = client.get('/api/manhuas/999999999/batch-chapter-images?start=1&end=5')
    assert res.status_code == 404
    assert 'não encontrada' in res.get_json()['error']

    # Faltando start ou end
    res = client.get('/api/manhuas/1/batch-chapter-images?start=1')
    assert res.status_code == 400

    # start > end
    res = client.get('/api/manhuas/1/batch-chapter-images?start=10&end=5')
    assert res.status_code == 400

    # start < 1
    res = client.get('/api/manhuas/1/batch-chapter-images?start=0&end=5')
    assert res.status_code == 400

    # Lote superior a 50 capítulos
    res = client.get('/api/manhuas/1/batch-chapter-images?start=1&end=60')
    assert res.status_code == 400
    assert 'Limite máximo' in res.get_json()['error']

def test_batch_chapter_images_success(client, monkeypatch):
    # Mocking single chapter scraper helper
    from server import extract_images_from_url
    monkeypatch.setattr('server.extract_images_from_url', lambda url: ['https://example.com/p1.jpg', 'https://example.com/p2.jpg'])

    res = client.get('/api/manhuas/1/batch-chapter-images?start=10&end=12')
    assert res.status_code == 200
    data = res.get_json()
    assert data['manhuaId'] == 1
    assert data['totalChapters'] == 3
    assert len(data['chapters']) == 3
    assert data['chapters'][0]['chapter'] == 10
    assert len(data['chapters'][0]['images']) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/test_server.py -k test_batch_chapter_images -v`
Expected: FAIL (404 Not Found para a rota)

- [ ] **Step 3: Implement `extract_images_from_url` helper and endpoint in `server.py`**

Em `server.py`, extrair a função auxiliar `extract_images_from_url(target_url)` reutilizável e adicionar o endpoint:
```python
from concurrent.futures import ThreadPoolExecutor

def extract_images_from_url(target_url):
    parsed = urllib.parse.urlparse(target_url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]

    if domain == "mangafire.to":
        data = mangafire_provider.get_mangafire_chapter_data(target_url)
        return data.get("images", [])

    if domain == "comix.to":
        data = comix_provider.get_comix_chapter_data(target_url)
        return data.get("images", [])

    if domain == "manhuaus.com":
        data = manhuaus_provider.get_manhuaus_chapter_data(target_url)
        return data.get("images", [])

    req = urllib.request.Request(
        target_url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
    return extract_chapter_images_by_domain(html, target_url)

@app.route("/api/manhuas/<int:item_id>/batch-chapter-images", methods=["GET"])
def get_batch_chapter_images(item_id):
    db_data = load_data()
    manhua = next((m for m in db_data if m["id"] == item_id), None)
    if not manhua:
        return jsonify({"error": "Obra não encontrada"}), 404

    try:
        start = int(request.args.get("start", ""))
        end = int(request.args.get("end", ""))
    except ValueError:
        return jsonify({"error": "Parâmetros 'start' e 'end' devem ser inteiros válidos"}), 400

    if start < 1 or end < start:
        return jsonify({"error": "Intervalo de capítulos inválido"}), 400

    if (end - start + 1) > 50:
        return jsonify({"error": "Limite máximo de 50 capítulos por lote excedido"}), 400

    url_template = manhua.get("urlTemplate", "")

    def process_chapter(chap_num):
        # Resolve target url for chapter
        chap_url = url_template.replace("{chapter}", str(chap_num))
        try:
            images = extract_images_from_url(chap_url)
            return {"chapter": chap_num, "targetUrl": chap_url, "images": images}
        except Exception as e:
            return {"chapter": chap_num, "targetUrl": chap_url, "images": [], "error": str(e)}

    chapters_to_fetch = list(range(start, end + 1))
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(process_chapter, chapters_to_fetch))

    results.sort(key=lambda x: x["chapter"])

    return jsonify({
        "manhuaId": manhua["id"],
        "title": manhua.get("title", ""),
        "range": {"start": start, "end": end},
        "totalChapters": len(results),
        "chapters": results
    })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/pytest tests/test_server.py -k test_batch_chapter_images -v`
Expected: PASS

- [ ] **Step 5: Run all backend tests**

Run: `./.venv/bin/pytest tests/`
Expected: 54 passed

- [ ] **Step 6: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat(backend): add batch-chapter-images endpoint with concurrent extraction"
```

---

### Task 2: Web Frontend - IndexedDB Helper & Offline Reader Check (`index.html`)

**Files:**
- Modify: `index.html`

**Interfaces:**
- Produces: 
  - `openOfflineDB(): Promise<IDBDatabase>`
  - `hasDownloadedChapter(manhuaId, chapter): Promise<boolean>`
  - `getDownloadedChapterPages(manhuaId, chapter): Promise<Blob[]>`
  - `saveDownloadedChapter(manhuaId, chapter, title, blobs): Promise<void>`
  - `deleteDownloadedChapter(manhuaId, chapter): Promise<void>`
  - `deleteAllDownloadedForManhua(manhuaId): Promise<void>`
  - `getDownloadedChapters(manhuaId): Promise<Array<{chapter: number, pageCount: number, downloadedAt: number}>>`
  - `getAllDownloadedSummary(): Promise<Array<{manhuaId: number, count: number}>>`
  - `clearAllOfflineDB(): Promise<void>`

- [ ] **Step 1: Implement `IndexedDB` Helper Functions in `index.html`**

Adicionar script no `<script>` de `index.html`:
```javascript
const DB_NAME = 'ManhuaOfflineDB';
const DB_VERSION = 1;

function openOfflineDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains('chapters')) {
        db.createObjectStore('chapters', { keyPath: 'id' }); // id: "${manhuaId}_${chapter}"
      }
      if (!db.objectStoreNames.contains('pages')) {
        db.createObjectStore('pages'); // key: "${manhuaId}_${chapter}_${pageIndex}"
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function hasDownloadedChapter(manhuaId, chapter) {
  const db = await openOfflineDB();
  return new Promise((resolve) => {
    const tx = db.transaction('chapters', 'readonly');
    const store = tx.objectStore('chapters');
    const req = store.get(`${manhuaId}_${chapter}`);
    req.onsuccess = () => resolve(!!req.result);
    req.onerror = () => resolve(false);
  });
}

async function getDownloadedChapterPages(manhuaId, chapter) {
  const db = await openOfflineDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(['chapters', 'pages'], 'readonly');
    const chapStore = tx.objectStore('chapters');
    const pageStore = tx.objectStore('pages');
    
    const chapReq = chapStore.get(`${manhuaId}_${chapter}`);
    chapReq.onsuccess = () => {
      const chap = chapReq.result;
      if (!chap) return resolve(null);
      const pageBlobs = [];
      let pending = chap.pageCount;
      if (pending === 0) return resolve([]);
      for (let i = 0; i < chap.pageCount; i++) {
        const pageReq = pageStore.get(`${manhuaId}_${chapter}_${i}`);
        pageReq.onsuccess = () => {
          pageBlobs[i] = pageReq.result;
          pending--;
          if (pending === 0) resolve(pageBlobs);
        };
        pageReq.onerror = () => reject(pageReq.error);
      }
    };
    chapReq.onerror = () => reject(chapReq.error);
  });
}

async function saveDownloadedChapter(manhuaId, chapter, title, blobs) {
  const db = await openOfflineDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(['chapters', 'pages'], 'readwrite');
    const chapStore = tx.objectStore('chapters');
    const pageStore = tx.objectStore('pages');

    chapStore.put({
      id: `${manhuaId}_${chapter}`,
      manhuaId: manhuaId,
      chapter: chapter,
      title: title,
      pageCount: blobs.length,
      downloadedAt: Date.now()
    });

    blobs.forEach((blob, idx) => {
      pageStore.put(blob, `${manhuaId}_${chapter}_${idx}`);
    });

    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

async function deleteDownloadedChapter(manhuaId, chapter) {
  const db = await openOfflineDB();
  const pages = await getDownloadedChapterPages(manhuaId, chapter);
  const count = pages ? pages.length : 100;
  return new Promise((resolve, reject) => {
    const tx = db.transaction(['chapters', 'pages'], 'readwrite');
    tx.objectStore('chapters').delete(`${manhuaId}_${chapter}`);
    const pageStore = tx.objectStore('pages');
    for (let i = 0; i < count; i++) {
      pageStore.delete(`${manhuaId}_${chapter}_${i}`);
    }
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

async function deleteAllDownloadedForManhua(manhuaId) {
  const chapters = await getDownloadedChapters(manhuaId);
  for (const c of chapters) {
    await deleteDownloadedChapter(manhuaId, c.chapter);
  }
}

async function getDownloadedChapters(manhuaId) {
  const db = await openOfflineDB();
  return new Promise((resolve) => {
    const tx = db.transaction('chapters', 'readonly');
    const store = tx.objectStore('chapters');
    const req = store.openCursor();
    const list = [];
    req.onsuccess = (e) => {
      const cursor = e.target.result;
      if (cursor) {
        if (cursor.value.manhuaId === manhuaId) {
          list.push(cursor.value);
        }
        cursor.continue();
      } else {
        list.sort((a, b) => a.chapter - b.chapter);
        resolve(list);
      }
    };
    req.onerror = () => resolve([]);
  });
}

async function clearAllOfflineDB() {
  const db = await openOfflineDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(['chapters', 'pages'], 'readwrite');
    tx.objectStore('chapters').clear();
    tx.objectStore('pages').clear();
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}
```

- [ ] **Step 2: Update `loadChapterPages()` in `index.html` to check local storage first**

Modificar `loadChapterPages()` em `index.html`:
```javascript
async function loadChapterPages() {
  if (!readerManhua) return;
  updateReaderHeader();
  window.scrollTo({ top: 0, behavior: 'smooth' });

  const container = document.getElementById('readerImagesContainer');
  const loading = document.getElementById('readerLoading');
  const errorEl = document.getElementById('readerError');
  const footer = document.getElementById('readerFooter');

  container.innerHTML = '';
  loading.style.display = 'block';
  errorEl.style.display = 'none';
  footer.style.display = 'none';

  // 1. Sempre verificar se existe o episódio localmente antes de chamar o backend
  try {
    const hasLocal = await hasDownloadedChapter(readerManhua.id, readerManhua.currentChapter);
    if (hasLocal) {
      const blobs = await getDownloadedChapterPages(readerManhua.id, readerManhua.currentChapter);
      if (blobs && blobs.length > 0) {
        loading.style.display = 'none';
        document.getElementById('readerSubtitle').innerHTML = `Capítulo ${readerManhua.currentChapter} <span class="badge-offline" style="background:#8257e6;color:#fff;font-size:0.7rem;padding:2px 6px;border-radius:4px;margin-left:6px;">💾 Offline</span>`;
        container.innerHTML = blobs.map((blob, idx) => {
          const url = URL.createObjectURL(blob);
          return `<img src="${url}" class="chapter-page-img" alt="Página ${idx + 1}" />`;
        }).join('');
        footer.style.display = 'block';
        return; // Retorna imediatamente sem chamar a API!
      }
    }
  } catch (localErr) {
    console.warn('Erro ao consultar IndexedDB:', localErr);
  }

  // 2. Se não estiver local, carregar da API normalmente
  const targetUrl = resolveTargetUrl(readerManhua);
  try {
    const res = await fetch(`/api/chapter-images?url=${encodeURIComponent(targetUrl)}`);
    const data = await res.json();
    loading.style.display = 'none';
    if ((data.status === 'ok' || Array.isArray(data.images)) && data.images && data.images.length > 0) {
      if (data.chapter) readerManhua.currentChapter = data.chapter;
      if (data.chapterId) readerManhua.chapterId = data.chapterId;
      if (data.next) readerManhua.nextChapter = data.next;
      if (data.prev) readerManhua.prevChapter = data.prev;
      updateReaderHeader();
      container.innerHTML = data.images.map((imgUrl, idx) => `
        <img 
          src="/api/proxy-image?url=${encodeURIComponent(imgUrl)}" 
          loading="lazy" 
          class="chapter-page-img" 
          alt="Página ${idx + 1}"
        />
      `).join('');
      footer.style.display = 'block';
    } else {
      errorEl.style.display = 'block';
      errorEl.innerHTML = `
        <p style="margin-bottom: 12px;">Não foi possível extrair as páginas deste capítulo automaticamente.</p>
        <a href="${targetUrl}" target="_blank" class="btn btn-secondary">Abrir no Site Original ↗</a>
      `;
    }
  } catch (err) {
    loading.style.display = 'none';
    errorEl.style.display = 'block';
    errorEl.innerHTML = `
      <p style="margin-bottom: 12px; color: var(--danger);">Erro de conexão ao carregar páginas.</p>
      <a href="${targetUrl}" target="_blank" class="btn btn-secondary">Abrir no Site Original ↗</a>
    `;
  }
}
```

- [ ] **Step 3: Test syntax and run asset tests**

Run: `./.venv/bin/pytest tests/test_pwa_assets.py`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat(web): add IndexedDB storage helper and offline-first reader flow"
```

---

### Task 3: Web Frontend - Download Modal and Storage Clear (`index.html`)

**Files:**
- Modify: `index.html`

**Interfaces:**
- Produces: 
  - Modal `#downloadModal` com inputs de range, barra de progresso e lista de capítulos com lixeira.
  - Botão de download em cada card na listagem.
  - Botão de limpeza geral no modal de configurações / rodapé.

- [ ] **Step 1: Add Download Modal HTML & CSS in `index.html`**

Adicionar estilos CSS e estrutura HTML para `#downloadModal`:
- Botão no card: botão com ícone de download que chama `openDownloadModal(manhua.id)`.
- Modal `#downloadModal`:
  - Título da obra
  - Input `downloadStartChapter` e `downloadEndChapter`
  - Botão `btnStartDownloadBatch`
  - Progresso: `#downloadProgressContainer` com barra e texto `#downloadProgressText`
  - `#downloadedChaptersList` com listagem dos capítulos salvos e botões de excluir.
  - Botão `btnDeleteAllManhuaDownloads`

- [ ] **Step 2: Add Download Batch and Cleanup Logic in `index.html`**

Implementar funções JS:
- `openDownloadModal(manhuaId)`: preenche inputs com capítulo atual, busca `getDownloadedChapters(manhuaId)` e renderiza a lista.
- `startBatchDownload()`:
  - Valida `start` e `end`.
  - Chama `fetch(`/api/manhuas/${activeDownloadManhuaId}/batch-chapter-images?start=${start}&end=${end}`)`.
  - Para cada capítulo retornado, para cada imagem:
    - Baixa como blob: `fetch('/api/proxy-image?url=' + encodeURIComponent(imgUrl)).then(r => r.blob())`.
    - Atualiza barra de progresso.
    - Salva no IndexedDB via `saveDownloadedChapter(...)`.
  - Atualiza a listagem de capítulos baixados no modal.
- `deleteChapterFromModal(manhuaId, chapter)`: remove do IndexedDB e re-renderiza.
- `deleteAllForManhuaFromModal(manhuaId)`: remove todos daquela obra.
- `clearAllGlobalDownloads()`: remove todo o IndexedDB com confirmação do usuário.

- [ ] **Step 3: Verify and run backend & pwa tests**

Run: `./.venv/bin/pytest tests/`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat(web): add batch download modal and manual storage management UI"
```

---

### Task 4: Mobile - Dependencies and Permissions Setup

**Files:**
- Modify: `mobile_app/pubspec.yaml`
- Modify: `mobile_app/android/app/src/main/AndroidManifest.xml`

**Interfaces:**
- Produces: `path_provider` e `permission_handler` instalados e permissões de disco declaradas no manifest Android.

- [ ] **Step 1: Add dependencies to `mobile_app/pubspec.yaml`**

Adicionar sob `dependencies:` em `mobile_app/pubspec.yaml`:
```yaml
  path_provider: ^2.1.2
  permission_handler: ^11.3.1
```

- [ ] **Step 2: Declare permissions in `mobile_app/android/app/src/main/AndroidManifest.xml`**

Adicionar permissões antes da tag `<application>`:
```xml
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"/>
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"/>
```

- [ ] **Step 3: Run `flutter pub get` and verify compilation/tests**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter pub get && /home/thiagofdso/development/flutter/bin/flutter test`
Expected: Dependencies resolved and all existing tests pass.

- [ ] **Step 4: Commit**

```bash
git add mobile_app/pubspec.yaml mobile_app/pubspec.lock mobile_app/android/app/src/main/AndroidManifest.xml
git commit -m "chore(mobile): add path_provider, permission_handler and storage permissions"
```

---

### Task 5: Mobile - Local Catalog Cache in `StorageService` & `ManhuaController`

**Files:**
- Modify: `mobile_app/lib/services/storage_service.dart`
- Modify: `mobile_app/lib/controllers/manhua_controller.dart`
- Modify: `mobile_app/lib/screens/home_screen.dart`
- Test: `mobile_app/test/services/storage_service_test.dart`
- Test: `mobile_app/test/controllers/manhua_controller_offline_test.dart`

**Interfaces:**
- Consumes: `SharedPreferences`, `Manhua`
- Produces: 
  - `StorageService.saveCachedManhuas(List<Manhua> manhuas): Future<void>`
  - `StorageService.getCachedManhuas(): Future<List<Manhua>>`
  - `ManhuaController.isOfflineMode: bool` (true quando exibindo cache local de fallback)

- [ ] **Step 1: Write failing tests for cached catalog in `storage_service_test.dart`**

Criar `mobile_app/test/services/storage_service_test.dart`:
```dart
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/services/storage_service_test.dart`
Expected: FAIL (métodos não existem)

- [ ] **Step 3: Implement `saveCachedManhuas` and `getCachedManhuas` in `StorageService`**

Em `mobile_app/lib/services/storage_service.dart`:
```dart
import 'dart:convert';
import '../models/manhua.dart';

// No StorageService:
static const String _keyCachedManhuas = 'cached_manhuas_list';

Future<void> saveCachedManhuas(List<Manhua> manhuas) async {
  final prefs = await SharedPreferences.getInstance();
  final listJson = manhuas.map((m) => m.toJson()).toList();
  await prefs.setString(_keyCachedManhuas, jsonEncode(listJson));
}

Future<List<Manhua>> getCachedManhuas() async {
  final prefs = await SharedPreferences.getInstance();
  final raw = prefs.getString(_keyCachedManhuas);
  if (raw == null || raw.isEmpty) return [];
  try {
    final List<dynamic> decoded = jsonDecode(raw);
    return decoded.map((item) => Manhua.fromJson(item as Map<String, dynamic>)).toList();
  } catch (_) {
    return [];
  }
}
```

- [ ] **Step 4: Update `ManhuaController` to cache on success and fallback on failure**

Em `mobile_app/lib/controllers/manhua_controller.dart`:
- Adicionar `bool _isOfflineMode = false; bool get isOfflineMode => _isOfflineMode;`
- Em `loadManhuas()`:
  ```dart
  Future<void> loadManhuas() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final list = await _apiService.fetchManhuas();
      _manhuas = list;
      _isOfflineMode = false;
      await _storageService.saveCachedManhuas(list);
    } catch (e) {
      final cached = await _storageService.getCachedManhuas();
      if (cached.isNotEmpty) {
        _manhuas = cached;
        _isOfflineMode = true;
        _errorMessage = null;
      } else {
        _errorMessage = e.toString();
      }
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
  ```

- [ ] **Step 5: Display offline indicator banner in `HomeScreen` when `isOfflineMode == true`**

Em `mobile_app/lib/screens/home_screen.dart`, exibir banner sutil sob a AppBar caso `controller.isOfflineMode` seja verdadeiro.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add mobile_app/lib/services/storage_service.dart mobile_app/lib/controllers/manhua_controller.dart mobile_app/lib/screens/home_screen.dart mobile_app/test/services/storage_service_test.dart
git commit -m "feat(mobile): implement offline catalog cache fallback in storage service and controller"
```

---

### Task 6: Mobile - `DownloadService` (Local File Storage & Manifest)

**Files:**
- Create: `mobile_app/lib/services/download_service.dart`
- Test: `mobile_app/test/services/download_service_test.dart`

**Interfaces:**
- Produces: 
  - `hasChapter(int manhuaId, int chapter): Future<bool>`
  - `getChapterImagePaths(int manhuaId, int chapter): Future<List<String>>`
  - `saveChapterImage(int manhuaId, int chapter, int pageIndex, List<int> bytes): Future<void>`
  - `deleteChapter(int manhuaId, int chapter): Future<void>`
  - `deleteAllForManhua(int manhuaId): Future<void>`
  - `clearAllDownloads(): Future<void>`
  - `getDownloadedChapters(int manhuaId): Future<List<int>>`
  - `getTotalDownloadedCount(): Future<int>`

- [ ] **Step 1: Write failing unit tests in `test/services/download_service_test.dart`**

Criar teste unitário utilizando diretório temporário para mock de sistema de arquivos:
```dart
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/services/download_service.dart';

void main() {
  late Directory tempDir;
  late DownloadService downloadService;

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('download_service_test');
    downloadService = DownloadService(baseDirProvider: () async => tempDir);
  });

  tearDown(() async {
    if (await tempDir.exists()) {
      await tempDir.delete(recursive: true);
    }
  });

  test('salva imagem de capitulo e verifica existencia', () async {
    expect(await downloadService.hasChapter(1, 10), isFalse);

    await downloadService.saveChapterImage(1, 10, 0, [1, 2, 3]);
    await downloadService.saveChapterImage(1, 10, 1, [4, 5, 6]);

    expect(await downloadService.hasChapter(1, 10), isTrue);
    final paths = await downloadService.getChapterImagePaths(1, 10);
    expect(paths.length, 2);

    final chapters = await downloadService.getDownloadedChapters(1);
    expect(chapters, [10]);
  });

  test('deleteChapter e deleteAllForManhua removem arquivos', () async {
    await downloadService.saveChapterImage(1, 10, 0, [1, 2, 3]);
    await downloadService.saveChapterImage(1, 11, 0, [1, 2, 3]);

    await downloadService.deleteChapter(1, 10);
    expect(await downloadService.hasChapter(1, 10), isFalse);
    expect(await downloadService.hasChapter(1, 11), isTrue);

    await downloadService.deleteAllForManhua(1);
    expect(await downloadService.hasChapter(1, 11), isFalse);
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/services/download_service_test.dart`
Expected: FAIL (DownloadService não existe)

- [ ] **Step 3: Implement `DownloadService`**

Criar `mobile_app/lib/services/download_service.dart`:
```dart
import 'dart:io';
import 'package:path_provider/path_provider.dart';

class DownloadService {
  final Future<Directory> Function()? _baseDirProvider;

  DownloadService({Future<Directory> Function()? baseDirProvider})
      : _baseDirProvider = baseDirProvider;

  Future<Directory> _getBaseDir() async {
    if (_baseDirProvider != null) {
      return await _baseDirProvider();
    }
    final appDir = await getApplicationDocumentsDirectory();
    final downloadDir = Directory('${appDir.path}/downloads');
    if (!await downloadDir.exists()) {
      await downloadDir.create(recursive: true);
    }
    return downloadDir;
  }

  Future<Directory> _getChapterDir(int manhuaId, int chapter) async {
    final base = await _getBaseDir();
    return Directory('${base.path}/$manhuaId/chapter_$chapter');
  }

  Future<bool> hasChapter(int manhuaId, int chapter) async {
    final dir = await _getChapterDir(manhuaId, chapter);
    if (!await dir.exists()) return false;
    final files = dir.listSync().whereType<File>().toList();
    return files.isNotEmpty;
  }

  Future<List<String>> getChapterImagePaths(int manhuaId, int chapter) async {
    final dir = await _getChapterDir(manhuaId, chapter);
    if (!await dir.exists()) return [];
    final files = dir.listSync().whereType<File>().toList();
    files.sort((a, b) => a.path.compareTo(b.path));
    return files.map((f) => f.path).toList();
  }

  Future<void> saveChapterImage(int manhuaId, int chapter, int pageIndex, List<int> bytes) async {
    final dir = await _getChapterDir(manhuaId, chapter);
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    final formattedIndex = pageIndex.toString().padLeft(4, '0');
    final file = File('${dir.path}/page_$formattedIndex.jpg');
    await file.writeAsBytes(bytes);
  }

  Future<void> deleteChapter(int manhuaId, int chapter) async {
    final dir = await _getChapterDir(manhuaId, chapter);
    if (await dir.exists()) {
      await dir.delete(recursive: true);
    }
  }

  Future<void> deleteAllForManhua(int manhuaId) async {
    final base = await _getBaseDir();
    final manhuaDir = Directory('${base.path}/$manhuaId');
    if (await manhuaDir.exists()) {
      await manhuaDir.delete(recursive: true);
    }
  }

  Future<void> clearAllDownloads() async {
    final base = await _getBaseDir();
    if (await base.exists()) {
      await base.delete(recursive: true);
      await base.create(recursive: true);
    }
  }

  Future<List<int>> getDownloadedChapters(int manhuaId) async {
    final base = await _getBaseDir();
    final manhuaDir = Directory('${base.path}/$manhuaId');
    if (!await manhuaDir.exists()) return [];
    final list = <int>[];
    for (final entity in manhuaDir.listSync()) {
      if (entity is Directory) {
        final name = entity.uri.pathSegments.where((s) => s.isNotEmpty).last;
        if (name.startsWith('chapter_')) {
          final numStr = name.replaceFirst('chapter_', '');
          final n = int.tryParse(numStr);
          if (n != null) list.add(n);
        }
      }
    }
    list.sort();
    return list;
  }

  Future<int> getTotalDownloadedCount() async {
    final base = await _getBaseDir();
    if (!await base.exists()) return 0;
    int count = 0;
    for (final entity in base.listSync()) {
      if (entity is Directory) {
        for (final chapDir in entity.listSync()) {
          if (chapDir is Directory) count++;
        }
      }
    }
    return count;
  }
}
```

- [ ] **Step 4: Run unit test to verify it passes**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/services/download_service_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mobile_app/lib/services/download_service.dart mobile_app/test/services/download_service_test.dart
git commit -m "feat(mobile): implement DownloadService for filesystem storage and offline manifest"
```

---

### Task 7: Mobile - Batch Chapter Images API & `DownloadManhuaDialog`

**Files:**
- Modify: `mobile_app/lib/services/api_service.dart`
- Create: `mobile_app/lib/screens/widgets/download_manhua_dialog.dart`
- Modify: `mobile_app/lib/screens/home_screen.dart`
- Test: `mobile_app/test/services/api_service_batch_test.dart`

**Interfaces:**
- Consumes: `ApiService`, `DownloadService`, `Manhua`
- Produces: 
  - `ApiService.fetchBatchChapterImages(int manhuaId, int start, int end): Future<Map<String, dynamic>>`
  - `DownloadManhuaDialog`: Diálogo para escolher range, baixar e gerenciar capítulos salvos.

- [ ] **Step 1: Write test for `fetchBatchChapterImages` in `ApiService`**

Criar `mobile_app/test/services/api_service_batch_test.dart`:
```dart
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile_app/services/api_service.dart';

void main() {
  test('fetchBatchChapterImages envia id, start e end e retorna json', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.path, '/api/manhuas/1/batch-chapter-images');
      expect(request.url.queryParameters['start'], '10');
      expect(request.url.queryParameters['end'], '12');
      return http.Response(jsonEncode({
        'manhuaId': 1,
        'chapters': [
          {'chapter': 10, 'images': ['https://test/1.jpg']}
        ]
      }), 200);
    });

    final api = ApiService(client: mockClient);
    final res = await api.fetchBatchChapterImages(1, 10, 12);
    expect(res['manhuaId'], 1);
    expect(res['chapters'].length, 1);
  });
}
```

- [ ] **Step 2: Implement `fetchBatchChapterImages` and bytes fetch in `ApiService`**

Em `mobile_app/lib/services/api_service.dart`:
```dart
Future<Map<String, dynamic>> fetchBatchChapterImages(int manhuaId, int start, int end) async {
  final base = await _baseUrl();
  final uri = Uri.parse('$base/api/manhuas/$manhuaId/batch-chapter-images').replace(
    queryParameters: {
      'start': start.toString(),
      'end': end.toString(),
    },
  );
  final res = await _client.get(uri);
  if (res.statusCode == 200) {
    return jsonDecode(res.body) as Map<String, dynamic>;
  } else {
    throw Exception('Falha ao buscar lote de capítulos: ${res.statusCode}');
  }
}

Future<List<int>> downloadImageBytes(String proxyUrl) async {
  final res = await _client.get(Uri.parse(proxyUrl));
  if (res.statusCode == 200) {
    return res.bodyBytes;
  } else {
    throw Exception('Falha ao baixar imagem: ${res.statusCode}');
  }
}
```

- [ ] **Step 3: Create `DownloadManhuaDialog` widget**

Criar `mobile_app/lib/screens/widgets/download_manhua_dialog.dart`:
- Formulário com `_startController` e `_endController` (inicializados com `widget.manhua.currentChapter`).
- Exibe lista de capítulos baixados obtida de `downloadService.getDownloadedChapters(widget.manhua.id)`.
- Ao clicar em "Baixar":
  - Valida os valores de start e end.
  - Chama `apiService.fetchBatchChapterImages`.
  - Para cada capítulo e para cada imagem:
    - Busca a URL proxy via `apiService.getProxyImageUrl(img)`.
    - Baixa os bytes via `apiService.downloadImageBytes(proxy)`.
    - Salva com `downloadService.saveChapterImage(...)`.
    - Atualiza `LinearProgressIndicator` com status: `Capítulo X: Imagem Y de Z`.
  - Recarrega a lista de capítulos salvos com botão de lixeira para exclusão manual.
  - Botão "Excluir todos os baixados desta obra".

- [ ] **Step 4: Add "Downloads Offline" option to `HomeScreen` popup menu**

Em `mobile_app/lib/screens/home_screen.dart`, adicionar item no `PopupMenuButton` de cada card para abrir o `DownloadManhuaDialog`.

- [ ] **Step 5: Run tests**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add mobile_app/lib/services/api_service.dart mobile_app/lib/screens/widgets/download_manhua_dialog.dart mobile_app/lib/screens/home_screen.dart mobile_app/test/services/api_service_batch_test.dart
git commit -m "feat(mobile): add fetchBatchChapterImages and DownloadManhuaDialog"
```

---

### Task 8: Mobile - Local-First Offline Reading in `ReaderScreen`

**Files:**
- Modify: `mobile_app/lib/screens/reader_screen.dart`
- Test: `mobile_app/test/reader_screen_offline_test.dart`

**Interfaces:**
- Consumes: `DownloadService`, `Manhua`
- Produces: `ReaderScreen` renderiza `Image.file(File(path))` quando capítulo existe localmente, sem chamar a API.

- [ ] **Step 1: Write widget test for local-first reader loading**

Criar `mobile_app/test/reader_screen_offline_test.dart`:
- Simular mock do `DownloadService` retornando `hasChapter == true` e caminhos de imagens locais.
- Verificar que o `ReaderScreen` renderiza o indicador offline e não tenta chamar a rede.

- [ ] **Step 2: Update `_loadPages()` in `ReaderScreen` to check local storage first**

Em `mobile_app/lib/screens/reader_screen.dart`:
```dart
final downloadService = DownloadService();
bool _isLocalChapter = false;

Future<void> _loadPages() async {
  setState(() {
    _isLoading = true;
    _errorMessage = null;
    _imageUrls = [];
    _isLocalChapter = false;
  });

  if (_scrollController.hasClients) {
    _scrollController.jumpTo(0);
  }

  // 1. Sempre verificar se existe o episódio localmente antes de tentar chamar o backend
  try {
    final hasLocal = await downloadService.hasChapter(_currentManhua.id, _currentChapter);
    if (hasLocal) {
      final localPaths = await downloadService.getChapterImagePaths(_currentManhua.id, _currentChapter);
      if (localPaths.isNotEmpty && mounted) {
        setState(() {
          _imageUrls = localPaths;
          _isLocalChapter = true;
          _isLoading = false;
        });
        return; // Retorna imediatamente sem chamada de rede!
      }
    }
  } catch (e) {
    // Se falhar a leitura local, tenta a rede
  }

  // 2. Se não estiver salvo localmente, chama o backend
  try {
    final controller = context.read<ManhuaController>();
    final targetUrl = _currentManhua.targetUrlForChapter(_currentChapter);
    final rawImages = await controller.apiService.fetchChapterImages(targetUrl);

    final List<String> proxyImages = [];
    for (final img in rawImages) {
      final proxy = await controller.apiService.getProxyImageUrl(img);
      proxyImages.add(proxy);
    }

    if (mounted) {
      setState(() {
        _imageUrls = proxyImages;
        _isLoading = false;
      });
    }
  } catch (e) {
    if (mounted) {
      setState(() {
        _errorMessage = 'Erro ao carregar capítulo:\n$e\n(Capítulo não salvo localmente)';
        _isLoading = false;
      });
    }
  }
}
```

- [ ] **Step 3: Update `_buildBody()` to render local files or network images**

No leitor:
```dart
if (_isLocalChapter) {
  return Image.file(
    File(url),
    fit: BoxFit.fitWidth,
    errorBuilder: (ctx, err, stack) => const Icon(Icons.broken_image, size: 48),
  );
} else {
  return CachedNetworkImage(...);
}
```
Exibir badge `💾 Offline` na `AppBar` quando `_isLocalChapter == true`.

- [ ] **Step 4: Run flutter tests**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mobile_app/lib/screens/reader_screen.dart mobile_app/test/reader_screen_offline_test.dart
git commit -m "feat(mobile): verify and render downloaded chapters offline in ReaderScreen"
```

---

### Task 9: Mobile - Permission Request on First Launch & Settings Clear UI

**Files:**
- Modify: `mobile_app/lib/screens/home_screen.dart`
- Modify: `mobile_app/lib/screens/widgets/settings_dialog.dart`

**Interfaces:**
- Produces: Solicitação de permissão de disco na inicialização do app e seção de limpeza de downloads no `SettingsDialog`.

- [ ] **Step 1: Request storage permission on app first launch in `HomeScreen`**

Em `mobile_app/lib/screens/home_screen.dart`:
```dart
import 'package:permission_handler/permission_handler.dart';

@override
void initState() {
  super.initState();
  WidgetsBinding.instance.addPostFrameCallback((_) {
    _requestStoragePermissionOnStartup();
    context.read<ManhuaController>().loadManhuas();
  });
}

Future<void> _requestStoragePermissionOnStartup() async {
  try {
    if (Platform.isAndroid) {
      final status = await Permission.storage.status;
      if (!status.isGranted) {
        await Permission.storage.request();
      }
    }
  } catch (_) {}
}
```

- [ ] **Step 2: Add Clear All Downloads section to `SettingsDialog`**

Em `mobile_app/lib/screens/widgets/settings_dialog.dart`:
- Adicionar contador de capítulos baixados via `DownloadService().getTotalDownloadedCount()`.
- Botão "Limpar todos os downloads locais":
  - Confirmação via diálogo.
  - Executa `await DownloadService().clearAllDownloads()`.
  - Exibe SnackBar de confirmação.

- [ ] **Step 3: Run flutter tests**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add mobile_app/lib/screens/home_screen.dart mobile_app/lib/screens/widgets/settings_dialog.dart
git commit -m "feat(mobile): add first launch storage permission request and settings clear downloads UI"
```

---

### Task 10: Verification and End-to-End System Health

**Files:**
- Verify backend tests: `./.venv/bin/pytest tests/`
- Verify mobile tests: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`

- [ ] **Step 1: Run complete backend pytest suite**

Run: `./.venv/bin/pytest tests/`
Expected: All tests pass (>= 54 tests).

- [ ] **Step 2: Run complete mobile flutter test suite**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`
Expected: All tests pass.

- [ ] **Step 3: Verify git status and commit any remaining changes**

Run: `git status`
Expected: clean working directory or only expected untracked files.
