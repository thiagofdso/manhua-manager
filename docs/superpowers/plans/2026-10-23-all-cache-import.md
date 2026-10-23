# Importação com Opção "Todos" Baseada em Cache Multi-Domínio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar a opção "Todos" no seletor de domínios do módulo de importação, realizando busca em memória sobre todos os arquivos de cache locais (`.cache/import_cache_*.json`) existentes, exibindo a identificação do domínio de origem de cada obra no Mobile e na Web.

**Architecture:** A classe `AllCacheImporter` em `importers/all_cache.py` estende `BaseDomainImporter` e realiza varredura no diretório `.cache/`, agregando e desduplicando obras de todos os caches existentes, filtrando por título e paginando em memória (40 itens por página). O backend propaga `domain` e `domainName` no payload de `/api/import/browse`, e as interfaces Flutter e Web exibem a identificação visual da origem de cada obra.

**Tech Stack:** Python 3.14 (Flask, pytest), Flutter / Dart (Mobile App), HTML/JavaScript (Web Interface), Systemd (User service).

## Global Constraints
- Python virtualenv em `./.venv/bin/python` e `./.venv/bin/pytest`.
- Flutter em `/home/thiagofdso/development/flutter/bin/flutter`.
- Preservar `{chapter}` em todos os `urlTemplate`.
- Manter formatação restrita: Checkbox, Título, Último Capítulo, Domínio e badge "Já cadastrada".
- 100% dos testes do Pytest (88+) e Flutter (49+) devem passar.
- Serviço gerenciado via `systemctl --user restart manhua-manager.service`.

---

### Task 1: Criar `AllCacheImporter` e Registrar em `importers/registry.py`

**Files:**
- Create: `importers/all_cache.py`
- Modify: `importers/registry.py`
- Test: `tests/test_importers.py`

**Interfaces:**
- Produces: `AllCacheImporter` implementing `BaseDomainImporter` with `search_or_browse(query: Optional[str] = None, page: int = 1, force_refresh: bool = False) -> dict` returning `{"items": [...], "page": int, "totalPages": int, "domain": "all"}`.
- Items contain `{"title": str, "urlTemplate": str, "lastChapter": int|float|None, "domain": str, "domainName": str}`.

- [ ] **Step 1: Write unit tests for `AllCacheImporter` in `tests/test_importers.py`**

Adicionar testes em `tests/test_importers.py` testando a agregação de múltiplos caches em diretório temporário, filtro de título case-insensitive, desduplicação por `urlTemplate`, cálculo de `totalPages` e presença de `domain` e `domainName`:

```python
def test_all_cache_importer_aggregates_caches(tmp_path):
    from importers.all_cache import AllCacheImporter

    # Cache 1: asurascans
    c1 = {
        "timestamp": time.time(),
        "catalog": {
            "": {"1": [
                {"title": "Solo Necromancer", "urlTemplate": "https://asurascans.com/comics/solo-necromancer/chapter/{chapter}", "lastChapter": 100},
                {"title": "Reaper of the Drifting Moon", "urlTemplate": "https://asurascans.com/comics/reaper/chapter/{chapter}", "lastChapter": 50}
            ]},
            "solo": {"1": [
                {"title": "Solo Necromancer", "urlTemplate": "https://asurascans.com/comics/solo-necromancer/chapter/{chapter}", "lastChapter": 100}
            ]}
        }
    }
    with open(tmp_path / "import_cache_asurascans_com.json", "w") as f:
        json.dump(c1, f)

    # Cache 2: mangafire
    c2 = {
        "timestamp": time.time(),
        "catalog": {
            "": {"1": [
                {"title": "Solo Leveling", "urlTemplate": "https://mangafire.to/title/solo-leveling/chapter/{chapter}", "lastChapter": 200}
            ]}
        }
    }
    with open(tmp_path / "import_cache_mangafire_to.json", "w") as f:
        json.dump(c2, f)

    importer = AllCacheImporter(cache_dir=str(tmp_path))

    # Test browse all (no query)
    res_all = importer.search_or_browse(query=None, page=1)
    assert len(res_all["items"]) == 3
    assert res_all["totalPages"] == 1
    # Check domain identification
    domains = {it["domainName"] for it in res_all["items"]}
    assert "Asura Scans" in domains
    assert "MangaFire" in domains

    # Test search query "solo" (should match Solo Necromancer and Solo Leveling, deduplicated)
    res_solo = importer.search_or_browse(query="solo", page=1)
    assert len(res_solo["items"]) == 2
    titles = [it["title"] for it in res_solo["items"]]
    assert "Solo Leveling" in titles
    assert "Solo Necromancer" in titles
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/test_importers.py::test_all_cache_importer_aggregates_caches -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'importers.all_cache'`

- [ ] **Step 3: Implement `AllCacheImporter` in `importers/all_cache.py`**

Criar `importers/all_cache.py`:
```python
import os
import json
import math
from typing import Optional
from importers.base import BaseDomainImporter

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache")

DOMAIN_FILENAME_MAP = {
    "import_cache_asurascans_com.json": ("asurascans.com", "Asura Scans"),
    "import_cache_ravenscans_org.json": ("ravenscans.org", "RavenScans"),
    "import_cache_comix_to.json": ("comix.to", "Comix"),
    "import_cache_manhuaus_com.json": ("manhuaus.com", "ManhuaUS"),
    "import_cache_arenascan_com.json": ("arenascan.com", "ArenaScan"),
    "import_cache_manhuatop_org.json": ("manhuatop.org", "ManhuaTop"),
    "import_cache_mgeko_cc.json": ("mgeko.cc", "MGeko"),
    "import_cache_mangak_io.json": ("mangak.io", "MangaK"),
    "import_cache_mangafire_to.json": ("mangafire.to", "MangaFire"),
}


class AllCacheImporter(BaseDomainImporter):
    domain = "all"
    name = "Todos"

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or CACHE_DIR

    def _infer_domain_info(self, filename: str) -> tuple[str, str]:
        if filename in DOMAIN_FILENAME_MAP:
            return DOMAIN_FILENAME_MAP[filename]
        # Fallback based on filename pattern import_cache_<key>.json
        base = filename.replace("import_cache_", "").replace(".json", "")
        domain_name = base.replace("_", ".")
        return domain_name, domain_name

    def search_or_browse(self, query: Optional[str] = None, page: int = 1, force_refresh: bool = False) -> dict:
        if not os.path.exists(self.cache_dir):
            return {"items": [], "page": 1, "totalPages": 1, "domain": "all"}

        q_clean = (query or "").strip().lower()
        unique_works: dict[str, dict] = {}

        # Scan all cache files in cache_dir
        for fname in sorted(os.listdir(self.cache_dir)):
            if not fname.startswith("import_cache_") or not fname.endswith(".json") or fname == "import_cache_all.json":
                continue

            filepath = os.path.join(self.cache_dir, fname)
            domain_id, domain_name = self._infer_domain_info(fname)

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                catalog = data.get("catalog", {})
            except Exception:
                continue

            # Iterate all queries and pages in the cache
            for q_key, pages in catalog.items():
                if not isinstance(pages, dict):
                    continue
                for p_key, items in pages.items():
                    if not isinstance(items, list):
                        continue
                    for it in items:
                        if not isinstance(it, dict):
                            continue
                        tmpl = it.get("urlTemplate", "").strip()
                        title = it.get("title", "").strip()
                        if not tmpl or not title:
                            continue

                        # Deduplicate by urlTemplate within domain
                        if tmpl not in unique_works:
                            unique_works[tmpl] = {
                                "title": title,
                                "urlTemplate": tmpl,
                                "lastChapter": it.get("lastChapter"),
                                "domain": domain_id,
                                "domainName": domain_name
                            }

        # Filter by search term if provided
        all_items = list(unique_works.values())
        if q_clean:
            all_items = [it for it in all_items if q_clean in it["title"].lower()]

        # Sort alphabetically by title
        all_items.sort(key=lambda x: x["title"].lower())

        # Pagination (40 items per page)
        limit = 40
        total_items = len(all_items)
        total_pages = max(1, math.ceil(total_items / limit))
        page = max(1, min(page, total_pages)) if total_items > 0 else 1

        start = (page - 1) * limit
        end = start + limit
        paged_items = all_items[start:end]

        return {
            "items": paged_items,
            "page": page,
            "totalPages": total_pages,
            "domain": "all"
        }
```

- [ ] **Step 4: Register `AllCacheImporter` in `importers/registry.py`**

Adicionar `"all"` no topo de `DOMAINS_CATALOG` e `_IMPORTERS`:
```python
from importers.all_cache import AllCacheImporter

DOMAINS_CATALOG = [
    {"domain": "all", "name": "Todos", "supported": True},
    {"domain": "asurascans.com", "name": "Asura Scans", "supported": True},
    ...
]

_IMPORTERS = {
    "all": AllCacheImporter(),
    "asurascans.com": AsurascansImporter(),
    ...
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `./.venv/bin/pytest tests/test_importers.py -v`
Expected: PASS (all tests pass)

- [ ] **Step 6: Commit changes**

```bash
git add importers/all_cache.py importers/registry.py tests/test_importers.py
git commit -m "feat(importers): add AllCacheImporter for multi-domain cache search"
```

---

### Task 2: Propagar `domain` e `domainName` no Endpoint `/api/import/browse` em `server.py`

**Files:**
- Modify: `server.py:133-156`
- Test: `tests/test_import_api.py`

**Interfaces:**
- Consumes: `AllCacheImporter` output with `domain` and `domainName`.
- Produces: JSON response for `GET /api/import/browse` with items containing `{"title": str, "urlTemplate": str, "lastChapter": ..., "alreadyExists": bool, "domain": str, "domainName": str}`.

- [ ] **Step 1: Write test for `/api/import/browse?domain=all` in `tests/test_import_api.py`**

Adicionar teste em `tests/test_import_api.py`:
```python
def test_browse_all_cache_endpoint(client, tmp_path):
    from importers.registry import _IMPORTERS
    from importers.all_cache import AllCacheImporter

    # Mock AllCacheImporter pointing to tmp_path
    c_data = {
        "catalog": {
            "": {"1": [
                {"title": "Test Work From Cache", "urlTemplate": "https://test.com/chapter/{chapter}", "lastChapter": 12}
            ]}
        }
    }
    with open(tmp_path / "import_cache_asurascans_com.json", "w") as f:
        json.dump(c_data, f)

    original_importer = _IMPORTERS.get("all")
    _IMPORTERS["all"] = AllCacheImporter(cache_dir=str(tmp_path))
    try:
        res = client.get("/api/import/browse?domain=all")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "ok"
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Test Work From Cache"
        assert data["items"][0]["domainName"] == "Asura Scans"
        assert "alreadyExists" in data["items"][0]
    finally:
        if original_importer:
            _IMPORTERS["all"] = original_importer
```

- [ ] **Step 2: Run test to verify it passes or fails**

Run: `./.venv/bin/pytest tests/test_import_api.py::test_browse_all_cache_endpoint -v`
Expected: If `server.py` does not propagate `domain` or `domainName`, test will fail on `assert data["items"][0]["domainName"] == "Asura Scans"`.

- [ ] **Step 3: Update `server.py` to propagate `domain` and `domainName`**

Em `server.py` na rota `/api/import/browse`:
```python
        annotated_items = []
        for item in data.get("items", []):
            url_tmpl = item.get("urlTemplate", "").lower().strip()
            title = item.get("title", "").lower().strip()
            already_exists = (url_tmpl in existing_urls) or (title in existing_titles)

            annotated_item = {
                "title": item["title"],
                "urlTemplate": item["urlTemplate"],
                "lastChapter": item.get("lastChapter"),
                "alreadyExists": already_exists
            }
            if "domain" in item:
                annotated_item["domain"] = item["domain"]
            if "domainName" in item:
                annotated_item["domainName"] = item["domainName"]

            annotated_items.append(annotated_item)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/pytest tests/test_import_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add server.py tests/test_import_api.py
git commit -m "feat(api): propagate domain and domainName in import browse endpoint"
```

---

### Task 3: Atualizar Modelo e Tela Flutter no Aplicativo Mobile

**Files:**
- Modify: `mobile_app/lib/models/import_work_item.dart`
- Modify: `mobile_app/lib/screens/import_manhua_screen.dart`
- Test: `mobile_app/test/services/api_service_import_test.dart`
- Test: `mobile_app/test/screens/import_manhua_screen_test.dart`

**Interfaces:**
- Produces: `ImportWorkItem` with `final String? domain;` and `final String? domainName;`.
- Screen displays subtitle as `"${item.domainName} • ${chText}"` when `item.domainName` is not null.

- [ ] **Step 1: Write tests in Flutter test suite**

Em `mobile_app/test/services/api_service_import_test.dart`:
Adicionar asserção verificando que `domain` e `domainName` são deserializados.

Em `mobile_app/test/screens/import_manhua_screen_test.dart`:
Adicionar teste verificando que a tela renderiza o nome do domínio no subtítulo quando fornecido.

- [ ] **Step 2: Update `ImportWorkItem` in `mobile_app/lib/models/import_work_item.dart`**

```dart
class ImportWorkItem {
  final String title;
  final String urlTemplate;
  final num? lastChapter;
  final bool alreadyExists;
  final String? domain;
  final String? domainName;

  ImportWorkItem({
    required this.title,
    required this.urlTemplate,
    this.lastChapter,
    this.alreadyExists = false,
    this.domain,
    this.domainName,
  });

  factory ImportWorkItem.fromJson(Map<String, dynamic> json) {
    return ImportWorkItem(
      title: json['title'] as String? ?? '',
      urlTemplate: json['urlTemplate'] as String? ?? '',
      lastChapter: json['lastChapter'] as num?,
      alreadyExists: json['alreadyExists'] as bool? ?? false,
      domain: json['domain'] as String?,
      domainName: json['domainName'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'title': title,
      'urlTemplate': urlTemplate,
      if (lastChapter != null) 'lastChapter': lastChapter,
      'alreadyExists': alreadyExists,
      if (domain != null) 'domain': domain,
      if (domainName != null) 'domainName': domainName,
    };
  }
}
```

- [ ] **Step 3: Update `ImportManhuaScreen` in `mobile_app/lib/screens/import_manhua_screen.dart`**

Atualizar a renderização do subtítulo do `ListTile`:
```dart
String chInfo = item.lastChapter != null ? 'Cap. ${item.lastChapter}' : 'Sem capítulos';
String subtitleText = (item.domainName != null && item.domainName!.isNotEmpty)
    ? '${item.domainName} • $chInfo'
    : chInfo;
```

- [ ] **Step 4: Run Flutter test suite**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`
Expected: 49+ tests PASS

- [ ] **Step 5: Commit changes**

```bash
git add mobile_app/lib/models/import_work_item.dart mobile_app/lib/screens/import_manhua_screen.dart mobile_app/test/
git commit -m "feat(mobile): support domain origin display in import work items"
```

---

### Task 4: Atualizar Interface Web (`index.html`)

**Files:**
- Modify: `index.html`

- [ ] **Step 1: Update `renderImportWorkList` in `index.html`**

No loop de exibição dos itens, incluir o prefixo do domínio caso `item.domainName` exista:
```javascript
        const domainPrefix = item.domainName ? `[${item.domainName}] ` : '';
        const chSpan = document.createElement('div');
        chSpan.textContent = item.lastChapter != null ? `${domainPrefix}Último: Cap. ${item.lastChapter}` : `${domainPrefix}Sem capítulos`;
        chSpan.style.fontSize = '0.78rem';
        chSpan.style.color = 'var(--muted)';
```

- [ ] **Step 2: Test web interface test suite**

Run: `./.venv/bin/pytest tests/test_web_interface.py -v`
Expected: PASS

- [ ] **Step 3: Commit changes**

```bash
git add index.html
git commit -m "feat(web): display domain tag in import work list"
```

---

### Task 5: Validação Completa e Reinício do Serviço

- [ ] **Step 1: Run all backend tests**
Run: `./.venv/bin/pytest tests/`
Expected: 89+ PASS

- [ ] **Step 2: Run all mobile tests**
Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`
Expected: All tests pass

- [ ] **Step 3: Restart user systemd service**
Run: `systemctl --user restart manhua-manager.service && systemctl --user status manhua-manager.service --no-pager`
Expected: Active (running)

- [ ] **Step 4: Live API test**
Run: `curl -s "http://127.0.0.1:5000/api/import/browse?domain=all" | jq '{total_items: (.items | length), sample: .items[0]}'`
Expected: Status 200 with items containing `domainName`
