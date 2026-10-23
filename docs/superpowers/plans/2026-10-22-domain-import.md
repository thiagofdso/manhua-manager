# Domain Import (Asura Scans) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement domain-based work importing starting with `asurascans.com`, featuring 1-week file caching per domain, clean compact selection list displaying only title and chapter count, bulk selection, default registration values (Sunday update, episode 1, extracted last episode, `{chapter}` template), and duplicate prevention across Backend, Web, and Mobile Flutter interfaces.

**Architecture:** A modular `importers/` package handles domain-specific scraping and caching to `.cache/import_cache_<domain>.json` with a 7-day TTL. `server.py` exposes REST endpoints (`/api/import/domains`, `/api/import/browse`, `/api/import`), matching existing works in `database.json` to prevent overwriting. The Web interface (`index.html`) provides a responsive modal, and the Flutter app (`mobile_app`) provides a dedicated `ImportManhuaScreen` accessible from `AppDrawer`.

**Tech Stack:** Python 3 (Flask, Requests, Pytest), HTML5/JavaScript (Vanilla ES6), Dart/Flutter (Provider, Flutter Test).

## Global Constraints

- Backend test execution: `./.venv/bin/python` and `./.venv/bin/pytest tests/`
- Mobile test execution: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`
- Systemd service restart: `systemctl --user restart manhua-manager.service`
- Work template standard: preserve `{chapter}` placeholder (e.g. `https://asurascans.com/comics/{slug}/chapter/{chapter}`)
- Default update day: `6` (Domingo)
- Initial chapter: `1`
- Selection list display: only work title, chapter count/last chapter, and "Já cadastrada" badge (no cover images in the selection list)
- Cache: file-based per domain with 1-week (7 days = 604,800s) TTL
- Duplicate handling: do not overwrite manual entries (mark `alreadyExists: true` in search, skip during import)

---

### Task 1: Domain Importers Architecture and Asura Scans Importer with 1-Week File Caching

**Files:**
- Create: `importers/__init__.py`
- Create: `importers/base.py`
- Create: `importers/registry.py`
- Create: `importers/asurascans.py`
- Create: `tests/test_importers.py`

**Interfaces:**
- Produces:
  - `importers.registry.get_registered_domains() -> list[dict]`
  - `importers.registry.get_importer(domain: str) -> BaseDomainImporter | None`
  - `importers.asurascans.AsurascansImporter.search_or_browse(query: str = None, page: int = 1, force_refresh: bool = False) -> dict`

- [ ] **Step 1: Write the failing tests for domain importers and cache**

Create `tests/test_importers.py`:
```python
import os
import json
import time
from unittest.mock import patch, MagicMock
from importers.registry import get_registered_domains, get_importer
from importers.asurascans import AsurascansImporter

def test_registry_lists_domains():
    domains = get_registered_domains()
    asura = next((d for d in domains if d["domain"] == "asurascans.com"), None)
    assert asura is not None
    assert asura["supported"] is True
    assert asura["name"] == "Asura Scans"

    unsupported = next((d for d in domains if d["domain"] == "mangafire.to"), None)
    assert unsupported is not None
    assert unsupported["supported"] is False

def test_asurascans_parsing():
    sample_html = """
    <div class="series-card group" data-series-id="101">
      <a href="/comics/test-comic-11fe7da3">
        <img src="https://cdn.example.com/cover.webp" alt="Test Comic" />
      </a>
      <div class="p-3">
        <a href="/comics/test-comic-11fe7da3">
          <h3 class="text-sm font-semibold">Test Comic &amp; Adventure</h3>
        </a>
        <div class="flex items-center gap-2 mt-2">
          <span class="text-xs">45 <!-- --> <span>Chapters</span></span>
        </div>
      </div>
    </div>
    <nav id="pagination-nav">
      <button aria-label="Page 1">1</button>
      <button aria-label="Page 2">2</button>
    </nav>
    """
    importer = AsurascansImporter()
    items, total_pages = importer._parse_html(sample_html)
    assert len(items) == 1
    assert items[0]["title"] == "Test Comic & Adventure"
    assert items[0]["urlTemplate"] == "https://asurascans.com/comics/test-comic-11fe7da3/chapter/{chapter}"
    assert items[0]["lastChapter"] == 45
    assert total_pages == 2

def test_asurascans_cache_ttl(tmp_path):
    cache_file = tmp_path / "import_cache_asurascans_com.json"
    importer = AsurascansImporter(cache_file=str(cache_file))

    # Pre-populate cache with timestamp 8 days ago (expired)
    old_time = time.time() - (8 * 86400)
    old_data = {
        "timestamp": old_time,
        "catalog": {"": {"1": [{"title": "Old Comic", "urlTemplate": "old", "lastChapter": 10}]}},
        "totalPages": {"": {"1": 1}}
    }
    with open(cache_file, "w") as f:
        json.dump(old_data, f)

    assert importer._is_cache_valid() is False

    # Pre-populate with timestamp 2 days ago (valid)
    new_time = time.time() - (2 * 86400)
    old_data["timestamp"] = new_time
    with open(cache_file, "w") as f:
        json.dump(old_data, f)

    assert importer._is_cache_valid() is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/test_importers.py`
Expected: FAIL (ModuleNotFoundError: No module named 'importers')

- [ ] **Step 3: Implement `importers/base.py`, `importers/registry.py`, and `importers/asurascans.py`**

Create `importers/__init__.py`:
```python
# Importers package
```

Create `importers/base.py`:
```python
from abc import ABC, abstractmethod

class BaseDomainImporter(ABC):
    domain: str = ""
    name: str = ""

    def is_supported(self) -> bool:
        return True

    @abstractmethod
    def search_or_browse(self, query: str = None, page: int = 1, force_refresh: bool = False) -> dict:
        pass
```

Create `importers/registry.py`:
```python
from typing import Optional
from importers.base import BaseDomainImporter
from importers.asurascans import AsurascansImporter

DOMAINS_CATALOG = [
    {"domain": "asurascans.com", "name": "Asura Scans", "supported": True},
    {"domain": "mangafire.to", "name": "MangaFire", "supported": False},
    {"domain": "comix.to", "name": "Comix", "supported": False},
    {"domain": "manhuaus.com", "name": "ManhuaUS", "supported": False},
    {"domain": "manhuatop.org", "name": "ManhuaTop", "supported": False},
    {"domain": "ravenscans.org", "name": "RavenScans", "supported": False},
    {"domain": "arenascan.com", "name": "ArenaScan", "supported": False},
    {"domain": "mgeko.cc", "name": "MGeko", "supported": False},
    {"domain": "levelingwithgods.com", "name": "Leveling with Gods", "supported": False},
    {"domain": "pickmeupgacha.com", "name": "Pick Me Up Gacha", "supported": False},
    {"domain": "magicemperor.online", "name": "Magic Emperor", "supported": False},
]

_IMPORTERS = {
    "asurascans.com": AsurascansImporter()
}

def get_registered_domains() -> list[dict]:
    return DOMAINS_CATALOG

def get_importer(domain: str) -> Optional[BaseDomainImporter]:
    clean_domain = domain.lower().replace("www.", "").strip()
    return _IMPORTERS.get(clean_domain)
```

Create `importers/asurascans.py`:
```python
import os
import json
import time
import re
import html
import requests
from importers.base import BaseDomainImporter

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache")
DEFAULT_CACHE_FILE = os.path.join(CACHE_DIR, "import_cache_asurascans_com.json")
CACHE_TTL = 7 * 86400  # 1 week in seconds

class AsurascansImporter(BaseDomainImporter):
    domain = "asurascans.com"
    name = "Asura Scans"

    def __init__(self, cache_file: str = None):
        self.cache_file = cache_file or DEFAULT_CACHE_FILE

    def _is_cache_valid(self) -> bool:
        if not os.path.exists(self.cache_file):
            return False
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            ts = data.get("timestamp", 0)
            return (time.time() - ts) < CACHE_TTL
        except Exception:
            return False

    def _load_cache(self) -> dict:
        if not os.path.exists(self.cache_file):
            return {"timestamp": 0, "catalog": {}, "totalPages": {}}
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"timestamp": 0, "catalog": {}, "totalPages": {}}

    def _save_cache(self, data: dict):
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _parse_html(self, html_text: str) -> tuple[list[dict], int]:
        cards = re.findall(r'<div class="series-card [^>]+>.*?</div>\s*</div>\s*</div>', html_text, re.DOTALL)
        if not cards:
            cards = re.findall(r'<div class="series-card .*?(?=(?:<div class="series-card |<nav id="pagination-nav"|$))', html_text, re.DOTALL)

        items = []
        for c in cards:
            href_m = re.search(r'href=["\'](/comics/[^"\']+)["\']', c)
            title_m = re.search(r'<h3[^>]*>(.*?)</h3>', c)
            chs_m = re.search(r'(\d+)\s*(?:<!-- -->)?\s*<span[^>]*>(?:Chs\.|Chapters)', c)

            if href_m and title_m:
                href = href_m.group(1).strip().rstrip("/")
                title = html.unescape(title_m.group(1).strip())
                url_template = f"https://asurascans.com{href}/chapter/{{chapter}}"
                last_chapter = int(chs_m.group(1)) if chs_m else None

                items.append({
                    "title": title,
                    "urlTemplate": url_template,
                    "lastChapter": last_chapter
                })

        pages = [int(p) for p in re.findall(r'page=(\d+)', html_text)]
        # Also check page numbers in aria-label
        aria_pages = [int(p) for p in re.findall(r'aria-label="Page (\d+)"', html_text)]
        all_pages = pages + aria_pages
        total_pages = max(all_pages) if all_pages else 1

        return items, total_pages

    def search_or_browse(self, query: str = None, page: int = 1, force_refresh: bool = False) -> dict:
        q_key = (query or "").strip().lower()
        p_key = str(page)

        cache = self._load_cache()
        if not force_refresh and self._is_cache_valid():
            catalog = cache.get("catalog", {})
            total_pages_dict = cache.get("totalPages", {})
            if q_key in catalog and p_key in catalog[q_key]:
                return {
                    "items": catalog[q_key][p_key],
                    "page": page,
                    "totalPages": total_pages_dict.get(q_key, {}).get(p_key, 1)
                }

        # Request to asurascans
        url = "https://asurascans.com/browse/comics"
        params = {}
        if q_key:
            params["q"] = q_key
        if page > 1:
            params["page"] = page

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            html_text = resp.content.decode("utf-8", errors="replace")
            items, total_pages = self._parse_html(html_text)
        except Exception as e:
            # Fallback to cache if available
            catalog = cache.get("catalog", {})
            if q_key in catalog and p_key in catalog[q_key]:
                return {
                    "items": catalog[q_key][p_key],
                    "page": page,
                    "totalPages": cache.get("totalPages", {}).get(q_key, {}).get(p_key, 1),
                    "warning": f"Erro de rede: {str(e)}. Usando dados locais em cache."
                }
            raise

        # Update cache
        if not self._is_cache_valid():
            cache["timestamp"] = time.time()
        if "catalog" not in cache:
            cache["catalog"] = {}
        if "totalPages" not in cache:
            cache["totalPages"] = {}

        if q_key not in cache["catalog"]:
            cache["catalog"][q_key] = {}
        if q_key not in cache["totalPages"]:
            cache["totalPages"][q_key] = {}

        cache["catalog"][q_key][p_key] = items
        cache["totalPages"][q_key][p_key] = total_pages
        self._save_cache(cache)

        return {
            "items": items,
            "page": page,
            "totalPages": total_pages
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/bin/pytest tests/test_importers.py`
Expected: 3 passed

- [ ] **Step 5: Commit Task 1**

```bash
git add importers/ tests/test_importers.py
git commit -m "feat: add domain importer architecture and asurascans parser with 1-week cache"
```

---

### Task 2: Backend REST API Endpoints and Duplicate Prevention

**Files:**
- Modify: `server.py`
- Create: `tests/test_import_api.py`

**Interfaces:**
- Produces:
  - `GET /api/import/domains` -> `list[dict]`
  - `GET /api/import/browse?domain=<dom>&q=<query>&page=<page>` -> `{"status": "ok", "domain": str, "page": int, "totalPages": int, "items": list[dict]}`
  - `POST /api/import` -> `{"status": "ok", "imported": int, "skipped": int}`

- [ ] **Step 1: Write failing tests for import API endpoints and duplicate prevention**

Create `tests/test_import_api.py`:
```python
import json
import pytest
from server import app

@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db = tmp_path / "test_db.json"
    initial_data = [
        {
            "id": 1,
            "title": "Existing Overgeared",
            "urlTemplate": "https://asurascans.com/comics/overgeared-11fe7da3/chapter/{chapter}",
            "currentChapter": 100,
            "lastChapter": 300,
            "updateDay": 4
        }
    ]
    with open(test_db, "w", encoding="utf-8") as f:
        json.dump(initial_data, f)

    monkeypatch.setattr("server.DB_FILE", str(test_db))
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

def test_get_import_domains(client):
    res = client.get("/api/import/domains")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)
    asura = next((d for d in data if d["domain"] == "asurascans.com"), None)
    assert asura is not None
    assert asura["supported"] is True

def test_browse_domain_with_duplicate_detection(client, monkeypatch):
    mock_data = {
        "items": [
            {
                "title": "Existing Overgeared",
                "urlTemplate": "https://asurascans.com/comics/overgeared-11fe7da3/chapter/{chapter}",
                "lastChapter": 350
            },
            {
                "title": "Brand New Series",
                "urlTemplate": "https://asurascans.com/comics/brand-new-11fe7da3/chapter/{chapter}",
                "lastChapter": 20
            }
        ],
        "page": 1,
        "totalPages": 3
    }

    class MockImporter:
        def search_or_browse(self, query=None, page=1):
            return mock_data

    monkeypatch.setattr("server.get_importer", lambda d: MockImporter())

    res = client.get("/api/import/browse?domain=asurascans.com")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert len(data["items"]) == 2
    # First item should be detected as already existing
    assert data["items"][0]["alreadyExists"] is True
    # Second item should be brand new
    assert data["items"][1]["alreadyExists"] is False

def test_post_import_prevents_overwrite_and_sets_defaults(client):
    payload = {
        "items": [
            {
                "title": "Existing Overgeared",
                "urlTemplate": "https://asurascans.com/comics/overgeared-11fe7da3/chapter/{chapter}",
                "lastChapter": 350
            },
            {
                "title": "Brand New Series",
                "urlTemplate": "https://asurascans.com/comics/brand-new-11fe7da3/chapter/{chapter}",
                "lastChapter": 20
            }
        ]
    }
    res = client.post("/api/import", json=payload)
    assert res.status_code == 200
    res_data = res.get_json()
    assert res_data["status"] == "ok"
    assert res_data["imported"] == 1
    assert res_data["skipped"] == 1

    # Check manhuas in DB
    list_res = client.get("/api/manhuas")
    manhuas = list_res.get_json()
    assert len(manhuas) == 2

    existing = next(m for m in manhuas if m["title"] == "Existing Overgeared")
    assert existing["currentChapter"] == 100  # Untouched!
    assert existing["updateDay"] == 4          # Untouched!

    new_work = next(m for m in manhuas if m["title"] == "Brand New Series")
    assert new_work["currentChapter"] == 1    # Default 1
    assert new_work["updateDay"] == 6         # Default Sunday (6)
    assert new_work["lastChapter"] == 20
    assert "{chapter}" in new_work["urlTemplate"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/test_import_api.py`
Expected: FAIL (404 Not Found on `/api/import/domains`)

- [ ] **Step 3: Implement import endpoints in `server.py`**

In `server.py`, import the registry helpers:
```python
from importers.registry import get_registered_domains, get_importer
```

Add endpoints to `server.py`:
```python
@app.route("/api/import/domains", methods=["GET"])
def get_import_domains():
    return jsonify(get_registered_domains())

@app.route("/api/import/browse", methods=["GET"])
def browse_import():
    domain = request.args.get("domain", "").strip()
    query = request.args.get("q", "").strip() or None
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1

    importer = get_importer(domain)
    if not importer:
        return jsonify({"error": f"Domínio '{domain}' não suportado para importação"}), 400

    try:
        data = importer.search_or_browse(query=query, page=page)
        db_data = load_data()

        # Build duplicate lookup sets
        existing_urls = {
            m.get("urlTemplate", "").lower().strip()
            for m in db_data if m.get("urlTemplate")
        }
        existing_titles = {
            m.get("title", "").lower().strip()
            for m in db_data if m.get("title")
        }

        # Annotate items with alreadyExists
        annotated_items = []
        for item in data.get("items", []):
            url_tmpl = item.get("urlTemplate", "").lower().strip()
            title = item.get("title", "").lower().strip()
            already_exists = (url_tmpl in existing_urls) or (title in existing_titles)

            annotated_items.append({
                "title": item["title"],
                "urlTemplate": item["urlTemplate"],
                "lastChapter": item.get("lastChapter"),
                "alreadyExists": already_exists
            })

        return jsonify({
            "status": "ok",
            "domain": domain,
            "page": data.get("page", page),
            "totalPages": data.get("totalPages", 1),
            "items": annotated_items
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/import", methods=["POST"])
def import_works():
    payload = request.get_json() or {}
    items = payload.get("items", [])
    if not isinstance(items, list) or not items:
        return jsonify({"error": "Nenhum item fornecido para importação"}), 400

    data = load_data()
    existing_urls = {
        m.get("urlTemplate", "").lower().strip()
        for m in data if m.get("urlTemplate")
    }
    existing_titles = {
        m.get("title", "").lower().strip()
        for m in data if m.get("title")
    }

    group_orders = [m.get("customOrder", 0) for m in data if not bool(m.get("isFavorite", False))]
    min_order = min(group_orders) if group_orders else 0

    imported_count = 0
    skipped_count = 0

    for item in items:
        title = item.get("title", "").strip()
        url_template = item.get("urlTemplate", "").strip()
        last_chapter = item.get("lastChapter")

        if not title or not url_template:
            continue

        norm_url = url_template.lower().strip()
        norm_title = title.lower().strip()

        if norm_url in existing_urls or norm_title in existing_titles:
            skipped_count += 1
            continue

        min_order -= 1
        new_manhua = {
            "id": int(time.time() * 1000) + imported_count,
            "title": title,
            "urlTemplate": url_template,
            "currentChapter": 1,
            "updatedAt": int(time.time()),
            "isFavorite": False,
            "customOrder": min_order,
            "isHiatus": False,
            "updateDay": 6  # Domingo
        }
        if last_chapter is not None:
            try:
                new_manhua["lastChapter"] = int(last_chapter)
            except (ValueError, TypeError):
                pass

        data.append(new_manhua)
        existing_urls.add(norm_url)
        existing_titles.add(norm_title)
        imported_count += 1

    if imported_count > 0:
        save_data(data)

    return jsonify({
        "status": "ok",
        "imported": imported_count,
        "skipped": skipped_count
    })
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/bin/pytest tests/test_import_api.py`
Expected: 3 passed

- [ ] **Step 5: Run full pytest suite to verify no regressions**

Run: `./.venv/bin/pytest tests/`
Expected: All tests pass

- [ ] **Step 6: Commit Task 2**

```bash
git add server.py tests/test_import_api.py
git commit -m "feat: implement import API endpoints with duplicate prevention"
```

---

### Task 3: Web Interface (`index.html`) - Import Modal, Domain Selector, Compact List and Bulk Actions

**Files:**
- Modify: `index.html`
- Modify: `tests/test_web_interface.py`

**Interfaces:**
- Produces:
  - Header button: `📥 Importar Obras` (`openImportModal()`)
  - Modal `#importModal` containing:
    - Domain selector `#importDomainSelect` with support badge `#importDomainSupportBadge`
    - Search input `#importSearchInput` + button `Pesquisar` (`searchImportWorks()`)
    - "Selecionar todos" checkbox `#importSelectAll` + counter `#importSelectedCount`
    - Compact scrollable list `#importWorkList` with only Checkbox, Title, Chapter Count, and "Já cadastrada" badge
    - Pagination `#importPagination` (`importChangePage(-1 / +1)`)
    - Confirm button `#btnConfirmImport` (`submitImportWorks()`)

- [ ] **Step 1: Write test for Web Interface elements**

In `tests/test_web_interface.py`, append tests verifying the presence of `#importModal`, `#importDomainSelect`, `#importSelectAll`, `#btnConfirmImport`, and the header import button.
```python
def test_import_elements_in_html():
    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()
    assert "openImportModal()" in content
    assert 'id="importModal"' in content
    assert 'id="importDomainSelect"' in content
    assert 'id="importSelectAll"' in content
    assert 'id="btnConfirmImport"' in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/test_web_interface.py`
Expected: FAIL

- [ ] **Step 3: Update `index.html` with markup, styles, and JavaScript functions**

1. Add button to header (around line 212):
```html
<button class="btn btn-secondary btn-sm" onclick="openImportModal()" title="Importar obras por domínio">📥 Importar Obras</button>
```

2. Add modal structure `#importModal`:
```html
  <!-- MODAL DE IMPORTAÇÃO DE OBRAS -->
  <div id="importModal" class="modal-backdrop">
    <div class="modal-box" style="max-width: 650px; max-height: 90vh; display: flex; flex-direction: column;">
      <div class="modal-header">
        <h2>📥 Importar Obras</h2>
        <button class="action-btn" onclick="closeImportModal()">✕</button>
      </div>

      <!-- Seletor de Domínio -->
      <div style="margin-bottom: 12px;">
        <label style="display: flex; justify-content: space-between; align-items: center;">
          <span>Domínio da Fonte</span>
          <span id="importDomainSupportBadge" class="badge" style="background: rgba(39,201,63,0.2); color: #27c93f;">Suportado</span>
        </label>
        <select id="importDomainSelect" onchange="onImportDomainChange()" style="width: 100%; padding: 10px; background: var(--bg); border: 1px solid var(--card-border); color: #fff; border-radius: 6px;">
        </select>
      </div>

      <!-- Barra de Busca -->
      <div style="display: flex; gap: 8px; margin-bottom: 12px;">
        <input type="text" id="importSearchInput" placeholder="Pesquisar por nome (opcional)..." style="flex: 1; margin-bottom: 0;" onkeydown="if(event.key==='Enter') searchImportWorks(1)" />
        <button id="btnSearchImport" class="btn btn-secondary" onclick="searchImportWorks(1)">Pesquisar</button>
      </div>

      <!-- Barra de Ações em Lote -->
      <div id="importBulkBar" style="display: none; justify-content: space-between; align-items: center; padding: 8px 12px; background: #202024; border-radius: 6px; margin-bottom: 8px;">
        <label style="display: flex; align-items: center; gap: 8px; margin-bottom: 0; cursor: pointer; font-size: 0.9rem;">
          <input type="checkbox" id="importSelectAll" onchange="toggleSelectAllImport(this.checked)" style="margin: 0; width: auto;" />
          <span>Selecionar todos</span>
        </label>
        <span id="importSelectedCount" style="color: var(--muted); font-size: 0.85rem;">0 selecionadas</span>
      </div>

      <!-- Lista de Obras (Scrollável e Compacta) -->
      <div id="importWorkListContainer" style="flex: 1; overflow-y: auto; min-height: 200px; max-height: 360px; border: 1px solid var(--card-border); border-radius: 6px; padding: 4px;">
        <div id="importWorkListPlaceholder" style="text-align: center; color: var(--muted); padding: 40px 16px;">
          Selecione o domínio e clique em <strong>Pesquisar</strong> para carregar as obras.
        </div>
        <div id="importWorkListLoading" style="display: none; text-align: center; padding: 40px 16px;">
          <div class="reader-spinner" style="margin: 0 auto 12px;"></div>
          <p style="color: var(--muted);">Buscando obras...</p>
        </div>
        <div id="importWorkList"></div>
      </div>

      <!-- Paginação -->
      <div id="importPagination" style="display: none; justify-content: space-between; align-items: center; margin-top: 10px;">
        <button id="btnImportPrevPage" class="btn btn-secondary btn-sm" onclick="changeImportPage(-1)">◀ Anterior</button>
        <span id="importPageIndicator" style="font-size: 0.85rem; color: var(--muted);">Página 1 de 1</span>
        <button id="btnImportNextPage" class="btn btn-secondary btn-sm" onclick="changeImportPage(1)">Próxima ▶</button>
      </div>

      <!-- Rodapé com Botão de Importação -->
      <div class="modal-actions" style="margin-top: 14px;">
        <button class="btn btn-secondary" onclick="closeImportModal()">Cancelar</button>
        <button id="btnConfirmImport" class="btn" style="flex: 1;" onclick="submitImportWorks()" disabled>Importar (0)</button>
      </div>
    </div>
  </div>
```

3. Add JavaScript logic in `index.html`:
- `let importDomains = []`
- `let currentImportDomain = null`
- `let importCurrentPage = 1`
- `let importTotalPages = 1`
- `let importLoadedItems = []`
- `let importSelectedMap = {}`
- Functions: `openImportModal()`, `closeImportModal()`, `onImportDomainChange()`, `searchImportWorks(page)`, `renderImportWorkList()`, `toggleSelectImportItem(index, checked)`, `toggleSelectAllImport(checked)`, `changeImportPage(delta)`, `submitImportWorks()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/pytest tests/test_web_interface.py`
Expected: PASS

- [ ] **Step 5: Commit Task 3**

```bash
git add index.html tests/test_web_interface.py
git commit -m "feat: add import works modal and bulk selector to web interface"
```

---

### Task 4: Mobile App Service and Model Integration

**Files:**
- Create: `mobile_app/lib/models/import_domain.dart`
- Create: `mobile_app/lib/models/import_work_item.dart`
- Modify: `mobile_app/lib/services/api_service.dart`
- Create: `mobile_app/test/services/api_service_import_test.dart`

**Interfaces:**
- Produces:
  - `ImportDomain` model (`domain`, `name`, `supported`)
  - `ImportWorkItem` model (`title`, `urlTemplate`, `lastChapter`, `alreadyExists`)
  - `ApiService.fetchImportDomains() -> Future<List<ImportDomain>>`
  - `ApiService.browseImportWorks({required String domain, String? query, int page = 1}) -> Future<ImportBrowseResult>`
  - `ApiService.importWorks(List<ImportWorkItem> items) -> Future<ImportResponse>`

- [ ] **Step 1: Write failing tests for ApiService import methods**

Create `mobile_app/test/services/api_service_import_test.dart`:
```dart
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:manhua_manager/models/import_domain.dart';
import 'package:manhua_manager/models/import_work_item.dart';
import 'package:manhua_manager/services/api_service.dart';

void main() {
  group('ApiService Import Tests', () {
    test('fetchImportDomains parses domains correctly', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode([
            {"domain": "asurascans.com", "name": "Asura Scans", "supported": true},
            {"domain": "mangafire.to", "name": "MangaFire", "supported": false}
          ]),
          200,
        );
      });

      final api = ApiService(client: mockClient);
      final domains = await api.fetchImportDomains();
      expect(domains.length, 2);
      expect(domains[0].domain, 'asurascans.com');
      expect(domains[0].supported, true);
      expect(domains[1].supported, false);
    });

    test('browseImportWorks returns items and pagination', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({
            "status": "ok",
            "domain": "asurascans.com",
            "page": 1,
            "totalPages": 4,
            "items": [
              {
                "title": "Solo Comic",
                "urlTemplate": "https://asurascans.com/comics/solo/chapter/{chapter}",
                "lastChapter": 40,
                "alreadyExists": false
              },
              {
                "title": "Existing Comic",
                "urlTemplate": "https://asurascans.com/comics/existing/chapter/{chapter}",
                "lastChapter": 100,
                "alreadyExists": true
              }
            ]
          }),
          200,
        );
      });

      final api = ApiService(client: mockClient);
      final result = await api.browseImportWorks(domain: 'asurascans.com');
      expect(result.page, 1);
      expect(result.totalPages, 4);
      expect(result.items.length, 2);
      expect(result.items[0].alreadyExists, false);
      expect(result.items[1].alreadyExists, true);
    });

    test('importWorks sends selected items and parses response', () async {
      final mockClient = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body['items'].length, 1);
        return http.Response(
          jsonEncode({"status": "ok", "imported": 1, "skipped": 0}),
          200,
        );
      });

      final api = ApiService(client: mockClient);
      final res = await api.importWorks([
        ImportWorkItem(
          title: 'Solo Comic',
          urlTemplate: 'https://asurascans.com/comics/solo/chapter/{chapter}',
          lastChapter: 40,
          alreadyExists: false,
        )
      ]);
      expect(res.imported, 1);
      expect(res.skipped, 0);
    });
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/services/api_service_import_test.dart`
Expected: Compilation FAIL (classes missing)

- [ ] **Step 3: Create models and update `ApiService`**

Create `mobile_app/lib/models/import_domain.dart`:
```dart
class ImportDomain {
  final String domain;
  final String name;
  final bool supported;

  ImportDomain({
    required this.domain,
    required this.name,
    required this.supported,
  });

  factory ImportDomain.fromJson(Map<String, dynamic> json) {
    return ImportDomain(
      domain: json['domain'] ?? '',
      name: json['name'] ?? '',
      supported: json['supported'] ?? false,
    );
  }
}
```

Create `mobile_app/lib/models/import_work_item.dart`:
```dart
class ImportWorkItem {
  final String title;
  final String urlTemplate;
  final int? lastChapter;
  final bool alreadyExists;

  ImportWorkItem({
    required this.title,
    required this.urlTemplate,
    this.lastChapter,
    required this.alreadyExists,
  });

  factory ImportWorkItem.fromJson(Map<String, dynamic> json) {
    return ImportWorkItem(
      title: json['title'] ?? '',
      urlTemplate: json['urlTemplate'] ?? '',
      lastChapter: json['lastChapter'] != null ? (json['lastChapter'] as num).toInt() : null,
      alreadyExists: json['alreadyExists'] ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'title': title,
      'urlTemplate': urlTemplate,
      if (lastChapter != null) 'lastChapter': lastChapter,
    };
  }
}

class ImportBrowseResult {
  final String domain;
  final int page;
  final int totalPages;
  final List<ImportWorkItem> items;

  ImportBrowseResult({
    required this.domain,
    required this.page,
    required this.totalPages,
    required this.items,
  });

  factory ImportBrowseResult.fromJson(Map<String, dynamic> json) {
    final rawList = json['items'] as List<dynamic>? ?? [];
    return ImportBrowseResult(
      domain: json['domain'] ?? '',
      page: (json['page'] as num?)?.toInt() ?? 1,
      totalPages: (json['totalPages'] as num?)?.toInt() ?? 1,
      items: rawList.map((e) => ImportWorkItem.fromJson(e)).toList(),
    );
  }
}

class ImportResponse {
  final String status;
  final int imported;
  final int skipped;

  ImportResponse({
    required this.status,
    required this.imported,
    required this.skipped,
  });

  factory ImportResponse.fromJson(Map<String, dynamic> json) {
    return ImportResponse(
      status: json['status'] ?? 'ok',
      imported: (json['imported'] as num?)?.toInt() ?? 0,
      skipped: (json['skipped'] as num?)?.toInt() ?? 0,
    );
  }
}
```

In `mobile_app/lib/services/api_service.dart`, add:
```dart
  Future<List<ImportDomain>> fetchImportDomains() async {
    final uri = Uri.parse('$baseUrl/api/import/domains');
    final response = await _client.get(uri).timeout(timeout);
    if (response.statusCode == 200) {
      final List<dynamic> list = jsonDecode(response.body);
      return list.map((e) => ImportDomain.fromJson(e)).toList();
    }
    throw Exception('Falha ao carregar domínios para importação');
  }

  Future<ImportBrowseResult> browseImportWorks({
    required String domain,
    String? query,
    int page = 1,
  }) async {
    final queryParams = {'domain': domain, 'page': page.toString()};
    if (query != null && query.trim().isNotEmpty) {
      queryParams['q'] = query.trim();
    }
    final uri = Uri.parse('$baseUrl/api/import/browse').replace(queryParameters: queryParams);
    final response = await _client.get(uri).timeout(timeout);
    if (response.statusCode == 200) {
      return ImportBrowseResult.fromJson(jsonDecode(response.body));
    }
    final err = jsonDecode(response.body)['error'] ?? 'Falha ao buscar obras para importação';
    throw Exception(err);
  }

  Future<ImportResponse> importWorks(List<ImportWorkItem> items) async {
    final uri = Uri.parse('$baseUrl/api/import');
    final response = await _client.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'items': items.map((e) => e.toJson()).toList()}),
    ).timeout(timeout);

    if (response.statusCode == 200) {
      return ImportResponse.fromJson(jsonDecode(response.body));
    }
    final err = jsonDecode(response.body)['error'] ?? 'Falha ao importar obras';
    throw Exception(err);
  }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/services/api_service_import_test.dart`
Expected: 3 passed

- [ ] **Step 5: Commit Task 4**

```bash
git add mobile_app/lib/models/import_domain.dart mobile_app/lib/models/import_work_item.dart mobile_app/lib/services/api_service.dart mobile_app/test/services/api_service_import_test.dart
git commit -m "feat: add import models and api service methods in mobile app"
```

---

### Task 5: Mobile App UI (`ImportManhuaScreen` and `AppDrawer` Integration)

**Files:**
- Create: `mobile_app/lib/screens/import_manhua_screen.dart`
- Modify: `mobile_app/lib/screens/widgets/app_drawer.dart`
- Create: `mobile_app/test/screens/import_manhua_screen_test.dart`

**Interfaces:**
- Produces:
  - `ImportManhuaScreen` widget
  - Menu item in `AppDrawer` leading to `ImportManhuaScreen`
  - Compact work row displaying only title, chapter count, and "Já cadastrada" badge

- [ ] **Step 1: Write widget test for `ImportManhuaScreen`**

Create `mobile_app/test/screens/import_manhua_screen_test.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:manhua_manager/controllers/manhua_controller.dart';
import 'package:manhua_manager/models/import_domain.dart';
import 'package:manhua_manager/models/import_work_item.dart';
import 'package:manhua_manager/screens/import_manhua_screen.dart';
import 'package:manhua_manager/services/api_service.dart';

class FakeApiService extends Fake implements ApiService {
  @override
  Future<List<ImportDomain>> fetchImportDomains() async {
    return [
      ImportDomain(domain: 'asurascans.com', name: 'Asura Scans', supported: true),
      ImportDomain(domain: 'mangafire.to', name: 'MangaFire', supported: false),
    ];
  }

  @override
  Future<ImportBrowseResult> browseImportWorks({required String domain, String? query, int page = 1}) async {
    return ImportBrowseResult(
      domain: domain,
      page: 1,
      totalPages: 1,
      items: [
        ImportWorkItem(title: 'Solo Comic', urlTemplate: 'solo_url', lastChapter: 40, alreadyExists: false),
        ImportWorkItem(title: 'Existing Comic', urlTemplate: 'exist_url', lastChapter: 100, alreadyExists: true),
      ],
    );
  }

  @override
  Future<ImportResponse> importWorks(List<ImportWorkItem> items) async {
    return ImportResponse(status: 'ok', imported: items.length, skipped: 0);
  }
}

void main() {
  testWidgets('ImportManhuaScreen renders domain selector, search, and work items', (tester) async {
    final fakeApi = FakeApiService();

    await tester.pumpWidget(
      MaterialApp(
        home: ImportManhuaScreen(apiService: fakeApi),
      ),
    );

    // Initial pump and wait for domains to load
    await tester.pumpAndSettle();

    expect(find.text('Importar Obras'), findsOneWidget);
    expect(find.text('Asura Scans'), findsWidgets);

    // Tap Pesquisar
    await tester.tap(find.text('Pesquisar'));
    await tester.pumpAndSettle();

    // Check items displayed in compact list
    expect(find.text('Solo Comic'), findsOneWidget);
    expect(find.text('Cap. 40'), findsOneWidget);
    expect(find.text('Existing Comic'), findsOneWidget);
    expect(find.text('Já cadastrada'), findsOneWidget);

    // Check Select All
    expect(find.text('Selecionar todos'), findsOneWidget);
    await tester.tap(find.text('Selecionar todos'));
    await tester.pumpAndSettle();

    // Check Import button enabled with 1 selected (since Existing Comic is disabled)
    expect(find.text('Importar (1)'), findsOneWidget);
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/screens/import_manhua_screen_test.dart`
Expected: Compilation FAIL (ImportManhuaScreen does not exist)

- [ ] **Step 3: Implement `ImportManhuaScreen` and add to `AppDrawer`**

Create `mobile_app/lib/screens/import_manhua_screen.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../controllers/manhua_controller.dart';
import '../models/import_domain.dart';
import '../models/import_work_item.dart';
import '../services/api_service.dart';

class ImportManhuaScreen extends StatefulWidget {
  final ApiService? apiService;

  const ImportManhuaScreen({super.key, this.apiService});

  @override
  State<ImportManhuaScreen> createState() => _ImportManhuaScreenState();
}

class _ImportManhuaScreenState extends State<ImportManhuaScreen> {
  late final ApiService _apiService;
  final TextEditingController _searchController = TextEditingController();

  List<ImportDomain> _domains = [];
  ImportDomain? _selectedDomain;
  bool _isLoadingDomains = true;

  bool _isSearching = false;
  List<ImportWorkItem> _items = [];
  final Set<int> _selectedIndexes = {};
  int _currentPage = 1;
  int _totalPages = 1;
  String? _errorMessage;
  bool _isSubmitting = false;

  @override
  void initState() {
    super.initState();
    _apiService = widget.apiService ?? ApiService();
    _loadDomains();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadDomains() async {
    try {
      final domains = await _apiService.fetchImportDomains();
      if (mounted) {
        setState(() {
          _domains = domains;
          if (domains.isNotEmpty) {
            _selectedDomain = domains.firstWhere(
              (d) => d.supported,
              orElse: () => domains.first,
            );
          }
          _isLoadingDomains = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = 'Falha ao carregar domínios: $e';
          _isLoadingDomains = false;
        });
      }
    }
  }

  Future<void> _search({int page = 1}) async {
    if (_selectedDomain == null || !_selectedDomain!.supported) return;

    setState(() {
      _isSearching = true;
      _errorMessage = null;
      _currentPage = page;
      _selectedIndexes.clear();
    });

    try {
      final result = await _apiService.browseImportWorks(
        domain: _selectedDomain!.domain,
        query: _searchController.text.trim().isEmpty ? null : _searchController.text.trim(),
        page: page,
      );
      if (mounted) {
        setState(() {
          _items = result.items;
          _currentPage = result.page;
          _totalPages = result.totalPages;
          _isSearching = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString().replaceFirst('Exception: ', '');
          _isSearching = false;
        });
      }
    }
  }

  void _toggleSelectAll(bool? value) {
    setState(() {
      _selectedIndexes.clear();
      if (value == true) {
        for (int i = 0; i < _items.length; i++) {
          if (!_items[i].alreadyExists) {
            _selectedIndexes.add(i);
          }
        }
      }
    });
  }

  Future<void> _submitImport() async {
    final toImport = _selectedIndexes.map((i) => _items[i]).toList();
    if (toImport.isEmpty) return;

    setState(() {
      _isSubmitting = true;
    });

    try {
      final res = await _apiService.importWorks(toImport);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${res.imported} obras importadas com sucesso! (${res.skipped} ignoradas)'),
            backgroundColor: Colors.green,
          ),
        );
        try {
          context.read<ManhuaController>().loadManhuas();
        } catch (_) {}
        // Refresh current list to mark newly imported as alreadyExists
        _search(page: _currentPage);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Erro ao importar: $e'),
            backgroundColor: Colors.redAccent,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final canSelectCount = _items.where((i) => !i.alreadyExists).length;
    final allSelected = canSelectCount > 0 && _selectedIndexes.length == canSelectCount;

    return Scaffold(
      backgroundColor: const Color(0xFF121214),
      appBar: AppBar(
        title: const Text('Importar Obras'),
        backgroundColor: const Color(0xFF202024),
      ),
      body: _isLoadingDomains
          ? const Center(child: CircularProgressIndicator())
          : Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Dropdown de Domínios
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    decoration: BoxDecoration(
                      color: const Color(0xFF202024),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: const Color(0xFF323238)),
                    ),
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<ImportDomain>(
                        value: _selectedDomain,
                        isExpanded: true,
                        dropdownColor: const Color(0xFF202024),
                        items: _domains.map((d) {
                          return DropdownMenuItem<ImportDomain>(
                            value: d,
                            child: Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    d.name.isNotEmpty ? d.name : d.domain,
                                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w500),
                                  ),
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: d.supported ? Colors.green.withOpacity(0.2) : Colors.redAccent.withOpacity(0.2),
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: Text(
                                    d.supported ? 'Suportado' : 'Sem suporte',
                                    style: TextStyle(
                                      color: d.supported ? Colors.greenAccent : Colors.redAccent,
                                      fontSize: 11,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          );
                        }).toList(),
                        onChanged: (val) {
                          setState(() {
                            _selectedDomain = val;
                            _items.clear();
                            _selectedIndexes.clear();
                            _errorMessage = null;
                          });
                        },
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // Barra de Busca + Botão Pesquisar
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _searchController,
                          decoration: InputDecoration(
                            hintText: 'Pesquisar obra...',
                            hintStyle: const TextStyle(color: Colors.grey),
                            filled: true,
                            fillColor: const Color(0xFF202024),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8),
                              borderSide: const BorderSide(color: Color(0xFF323238)),
                            ),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8),
                              borderSide: const BorderSide(color: Color(0xFF323238)),
                            ),
                          ),
                          onSubmitted: (_) => _search(page: 1),
                        ),
                      ),
                      const SizedBox(width: 8),
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF8257E6),
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                        onPressed: (_selectedDomain?.supported ?? false) && !_isSearching
                            ? () => _search(page: 1)
                            : null,
                        child: _isSearching
                            ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                            : const Text('Pesquisar', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),

                  // Barra "Selecionar todos"
                  if (_items.isNotEmpty)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: const Color(0xFF202024),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Row(
                        children: [
                          Checkbox(
                            value: allSelected,
                            onChanged: canSelectCount > 0 ? _toggleSelectAll : null,
                            activeColor: const Color(0xFF8257E6),
                          ),
                          const Text('Selecionar todos', style: TextStyle(color: Colors.white, fontSize: 13)),
                          const Spacer(),
                          Text(
                            '${_selectedIndexes.length} selecionadas',
                            style: const TextStyle(color: Colors.grey, fontSize: 12),
                          ),
                        ],
                      ),
                    ),
                  const SizedBox(height: 8),

                  // Lista de Obras
                  Expanded(
                    child: _errorMessage != null
                        ? Center(child: Text(_errorMessage!, style: const TextStyle(color: Colors.redAccent)))
                        : _items.isEmpty
                            ? Center(
                                child: Text(
                                  _selectedDomain?.supported == false
                                      ? 'Importação ainda não suportada para este domínio.'
                                      : 'Nenhuma obra carregada. Clique em Pesquisar.',
                                  style: const TextStyle(color: Colors.grey),
                                ),
                              )
                            : ListView.separated(
                                itemCount: _items.length,
                                separatorBuilder: (_, __) => const Divider(color: Color(0xFF29292E), height: 1),
                                itemBuilder: (context, index) {
                                  final item = _items[index];
                                  final isChecked = _selectedIndexes.contains(index);

                                  return ListTile(
                                    contentPadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 0),
                                    leading: Checkbox(
                                      value: item.alreadyExists ? false : isChecked,
                                      onChanged: item.alreadyExists
                                          ? null
                                          : (val) {
                                              setState(() {
                                                if (val == true) {
                                                  _selectedIndexes.add(index);
                                                } else {
                                                  _selectedIndexes.remove(index);
                                                }
                                              });
                                            },
                                      activeColor: const Color(0xFF8257E6),
                                    ),
                                    title: Text(
                                      item.title,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(
                                        color: item.alreadyExists ? Colors.grey : Colors.white,
                                        fontWeight: FontWeight.w500,
                                        fontSize: 14,
                                      ),
                                    ),
                                    subtitle: Text(
                                      item.lastChapter != null ? 'Cap. ${item.lastChapter}' : 'Sem capítulos',
                                      style: const TextStyle(color: Colors.grey, fontSize: 12),
                                    ),
                                    trailing: item.alreadyExists
                                        ? Container(
                                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                            decoration: BoxDecoration(
                                              color: const Color(0xFF29292E),
                                              borderRadius: BorderRadius.circular(4),
                                            ),
                                            child: const Text('Já cadastrada', style: TextStyle(color: Colors.grey, fontSize: 11)),
                                          )
                                        : null,
                                  );
                                },
                              ),
                  ),

                  // Paginação
                  if (_items.isNotEmpty && _totalPages > 1)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 8.0),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          ElevatedButton(
                            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF202024)),
                            onPressed: _currentPage > 1 ? () => _search(page: _currentPage - 1) : null,
                            child: const Text('◀ Anterior', style: TextStyle(color: Colors.white, fontSize: 12)),
                          ),
                          Text('Página $_currentPage de $_totalPages', style: const TextStyle(color: Colors.grey, fontSize: 12)),
                          ElevatedButton(
                            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF202024)),
                            onPressed: _currentPage < _totalPages ? () => _search(page: _currentPage + 1) : null,
                            child: const Text('Próxima ▶', style: TextStyle(color: Colors.white, fontSize: 12)),
                          ),
                        ],
                      ),
                    ),

                  // Botão Importar
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF8257E6),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    onPressed: _selectedIndexes.isNotEmpty && !_isSubmitting ? _submitImport : null,
                    child: _isSubmitting
                        ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                        : Text(
                            'Importar (${_selectedIndexes.length})',
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
                          ),
                  ),
                ],
              ),
            ),
    );
  }
}
```

In `mobile_app/lib/screens/widgets/app_drawer.dart`:
Import `import_manhua_screen.dart` and add a ListTile for "Importar Obras" right after "Armazenamento Offline":
```dart
                  ListTile(
                    leading: const Icon(Icons.cloud_download_outlined, color: Color(0xFF8257E6)),
                    title: const Text('Importar Obras', style: TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: const Text('Importar de fontes online', style: TextStyle(fontSize: 12, color: Colors.grey)),
                    onTap: () {
                      Navigator.pop(context);
                      Navigator.push(
                        context,
                        MaterialPageRoute(builder: (_) => const ImportManhuaScreen()),
                      );
                    },
                  ),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/screens/import_manhua_screen_test.dart`
Expected: PASS

- [ ] **Step 5: Run full mobile test suite to verify no regressions**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`
Expected: All tests pass

- [ ] **Step 6: Commit Task 5**

```bash
git add mobile_app/lib/screens/import_manhua_screen.dart mobile_app/lib/screens/widgets/app_drawer.dart mobile_app/test/screens/import_manhua_screen_test.dart
git commit -m "feat: add ImportManhuaScreen and drawer navigation item"
```

---

### Task 6: Full Verification and Service Restart

**Files:**
- Verification only

- [ ] **Step 1: Run full Backend Pytest test suite**

Run: `./.venv/bin/pytest tests/`
Expected: 100% PASS

- [ ] **Step 2: Run full Mobile Flutter test suite**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`
Expected: 100% PASS

- [ ] **Step 3: Test live import integration via backend API**

Run scratch script calling `http://127.0.0.1:5000/api/import/browse?domain=asurascans.com` to verify live response and caching file creation in `.cache/import_cache_asurascans_com.json`.

- [ ] **Step 4: Restart user systemd service**

Run: `systemctl --user restart manhua-manager.service`
Run: `systemctl --user status manhua-manager.service --no-pager`
Expected: Active (running)

- [ ] **Step 5: Final Git commit and status check**

```bash
git status
```
