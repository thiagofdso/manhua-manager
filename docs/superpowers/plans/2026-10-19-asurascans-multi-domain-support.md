# Suporte Multi-Domínio (Asura Scans e ManhuaTop) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar suporte à extração de imagens do Asura Scans e despacho dinâmico por domínio no leitor contínuo, preservando a extração do ManhuaTop e atualizando o template de Overgeared no banco.

**Architecture:** Módulo de extração baseado em estratégia de domínio no `server.py` com extratores dedicados para `manhuatop.org` e `asurascans.com`. Headers de proxy ajustados para evitar bloqueio anti-hotlinking.

**Tech Stack:** Python 3, Flask, pytest, unittest.mock, JSON, systemd.

## Global Constraints

- Manter retrocompatibilidade total com URLs de `manhuatop.org`.
- Não adicionar dependências externas (sem `beautifulsoup4`, usar `re` e `urllib` da biblioteca padrão).
- Manter ordem estrita de leitura e remover duplicatas de imagens.
- Seguir TDD rigoroso (teste falhando -> implementação mínima -> teste passando -> commit).

---

### Task 1: Funções Extratoras e Despachante por Domínio

**Files:**
- Modify: `server.py:86-121`
- Test: `tests/test_server.py`

**Interfaces:**
- Produces:
  - `extract_manhuatop_images(html: str) -> list[str]`
  - `extract_asurascans_images(html: str) -> list[str]`
  - `extract_chapter_images_by_domain(html: str, target_url: str) -> list[str]`

- [x] **Step 1: Write the failing tests**

Adicionar em `tests/test_server.py`:
```python
def test_extract_manhuatop_images():
    html = """
    <img src="https://manhuatop.org/about_manhuatop.webp" class="wp-manga-chapter-img" />
    <img src="https://s2.manhuatop.org/page1.jpg" class="wp-manga-chapter-img" />
    <img src="https://s2.manhuatop.org/page2.jpg" class="wp-manga-chapter-img" />
    """
    imgs = server.extract_manhuatop_images(html)
    assert imgs == ["https://s2.manhuatop.org/page1.jpg", "https://s2.manhuatop.org/page2.jpg"]

def test_extract_asurascans_images():
    html = """
    <img src="https://cdn.asurascans.com/asura-images/covers/overgeared.905990.webp" />
    <img src="https://cdn.asurascans.com/asura-images/chapters-merged/overgeared/162615/001.webp?v=1791877385" alt="Page 1" class="w-full" />
    <img src="https://cdn.asurascans.com/asura-images/chapters-merged/overgeared/162615/002.webp?v=1791877385" alt="Page 2" class="w-full" />
    """
    imgs = server.extract_asurascans_images(html)
    assert len(imgs) == 2
    assert imgs[0] == "https://cdn.asurascans.com/asura-images/chapters-merged/overgeared/162615/001.webp?v=1791877385"
    assert imgs[1] == "https://cdn.asurascans.com/asura-images/chapters-merged/overgeared/162615/002.webp?v=1791877385"

def test_extract_chapter_images_by_domain_dispatch():
    asura_html = '<img src="https://cdn.asurascans.com/asura-images/chapters-merged/test/1/001.webp" />'
    imgs = server.extract_chapter_images_by_domain(asura_html, "https://asurascans.com/comics/test/chapter/1")
    assert len(imgs) == 1
    assert "001.webp" in imgs[0]
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_server.py -k "extract_" -v`  
Expected: FAIL with `AttributeError: module 'server' has no attribute 'extract_manhuatop_images'`

- [x] **Step 3: Write minimal implementation**

Implementar em `server.py`:
```python
def extract_manhuatop_images(html: str) -> list[str]:
    raw_imgs = re.findall(r'<img[^>]+src=[\"\']([^\"\']+)[\"\'][^>]*class=[\"\'][^\"\']*wp-manga-chapter-img[^\"\']*[\"\']', html, re.IGNORECASE)
    raw_imgs += re.findall(r'<img[^>]+class=[\"\'][^\"\']*wp-manga-chapter-img[^\"\']*[\"\'][^>]+src=[\"\']([^\"\']+)[\"\']', html, re.IGNORECASE)
    seen = set()
    chapter_imgs = []
    for img in raw_imgs:
        clean = img.strip()
        if clean and clean not in seen and "about_manhuatop" not in clean:
            seen.add(clean)
            chapter_imgs.append(clean)
    return chapter_imgs

def extract_asurascans_images(html: str) -> list[str]:
    # Extrai URLs de páginas sob o padrão chapters-merged do CDN Asura Scans
    pattern = r'https://cdn\.asurascans\.com/asura-images/chapters-merged/[^\s"\'<>&]+(?:\?[^\s"\'<>&]*)?'
    raw_matches = re.findall(pattern, html)
    # Deduplica preservando a ordem
    unique = list(dict.fromkeys(raw_matches))
    return unique

def extract_generic_images(html: str) -> list[str]:
    imgs = extract_manhuatop_images(html)
    if imgs:
        return imgs
    return extract_asurascans_images(html)

def extract_chapter_images_by_domain(html: str, target_url: str) -> list[str]:
    parsed = urllib.parse.urlparse(target_url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]

    extractors = {
        "asurascans.com": extract_asurascans_images,
        "manhuatop.org": extract_manhuatop_images,
    }
    extractor = extractors.get(domain, extract_generic_images)
    return extractor(html)
```

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_server.py -k "extract_" -v`  
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat: add domain-based image extractors for manhuatop and asurascans"
```

---

### Task 2: Atualização dos Endpoints `/api/chapter-images` e `/api/proxy-image`

**Files:**
- Modify: `server.py:86-145`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `extract_chapter_images_by_domain`
- Produces:
  - `GET /api/chapter-images?url=...` utilizando o despachante por domínio.
  - `GET /api/proxy-image?url=...` utilizando cabeçalho `Referer: https://asurascans.com/` para domínios Asura Scans.

- [x] **Step 1: Write the failing tests**

Adicionar em `tests/test_server.py`:
```python
def test_get_chapter_images_endpoint_asurascans(client):
    from unittest.mock import patch, MagicMock
    mock_html = """
    <html>
      <body>
        <astro-island props="{&quot;seriesSlug&quot;:[0,&quot;overgeared&quot;]}">
          <img src="https://cdn.asurascans.com/asura-images/chapters-merged/overgeared/162615/001.webp?v=1" />
          <img src="https://cdn.asurascans.com/asura-images/chapters-merged/overgeared/162615/002.webp?v=1" />
        </astro-island>
      </body>
    </html>
    """.encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.read.return_value = mock_html
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = client.get("/api/chapter-images?url=https://asurascans.com/comics/overgeared-11fe7da3/chapter/197")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "ok"
        assert len(data["images"]) == 2
        assert "001.webp" in data["images"][0]

def test_proxy_image_asurascans_referer(client):
    from unittest.mock import patch, MagicMock
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"fake-webp-binary"
    mock_resp.headers = {"Content-Type": "image/webp"}
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        res = client.get("/api/proxy-image?url=https://cdn.asurascans.com/asura-images/chapters-merged/test/1/001.webp")
        assert res.status_code == 200
        assert res.data == b"fake-webp-binary"
        req_arg = mock_urlopen.call_args[0][0]
        assert req_arg.get_header("Referer") == "https://asurascans.com/"
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_server.py -k "asurascans" -v`  
Expected: FAIL on `test_proxy_image_asurascans_referer` (Referer is currently `https://cdn.asurascans.com/`)

- [x] **Step 3: Write minimal implementation**

No `server.py`:
Atualizar `get_chapter_images()`:
```python
@app.route("/api/chapter-images", methods=["GET"])
def get_chapter_images():
    target_url = request.args.get("url")
    if not target_url:
        return jsonify({"error": "Parâmetro url é obrigatório"}), 400

    try:
        req = urllib.request.Request(
            target_url,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        chapter_imgs = extract_chapter_images_by_domain(html, target_url)

        return jsonify({
            "status": "ok",
            "count": len(chapter_imgs),
            "images": chapter_imgs
        })
    except Exception as e:
        return jsonify({"error": str(e), "images": []}), 500
```

Atualizar `proxy_image()`:
```python
@app.route("/api/proxy-image", methods=["GET"])
def proxy_image():
    img_url = request.args.get("url")
    if not img_url:
        return jsonify({"error": "Parâmetro url é obrigatório"}), 400

    parsed = urllib.parse.urlparse(img_url)
    if "asurascans.com" in parsed.netloc.lower():
        referer = "https://asurascans.com/"
    else:
        referer = f"{parsed.scheme}://{parsed.netloc}/"

    try:
        req = urllib.request.Request(
            img_url,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": referer
            }
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read()
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            return Response(content, mimetype=content_type, headers={"Cache-Control": "public, max-age=86400"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_server.py -v`  
Expected: PASS (all tests in `test_server.py`)

- [x] **Step 5: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat: route chapter extraction and proxy referer by domain"
```

---

### Task 3: Atualização do Banco de Dados e Teste de Seed

**Files:**
- Modify: `database.json`
- Modify: `tests/test_database_seed.py`

**Interfaces:**
- Produces: Atualização de Overgeared para Asura Scans no `database.json`.

- [x] **Step 1: Write failing test**

Atualizar `tests/test_database_seed.py`:
```python
def test_database_initial_seed_content():
    db_file = os.path.join(os.path.dirname(__file__), "..", "database.json")
    with open(db_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) >= 1
    overgeared = next((item for item in data if item["title"] == "Overgeared"), None)
    assert overgeared is not None
    assert overgeared["currentChapter"] == 197
    assert "https://asurascans.com/comics/overgeared-11fe7da3/chapter/{chapter}" in overgeared["urlTemplate"]
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_database_seed.py -v`  
Expected: FAIL

- [x] **Step 3: Update database.json**

Atualizar `database.json`:
```json
[
  {
    "id": 1,
    "title": "Overgeared",
    "urlTemplate": "https://asurascans.com/comics/overgeared-11fe7da3/chapter/{chapter}",
    "currentChapter": 197,
    "updatedAt": 1792461210
  }
]
```

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_database_seed.py -v`  
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add database.json tests/test_database_seed.py
git commit -m "chore: update overgeared url template and chapter in database.json"
```

---

### Task 4: Validação do Sistema e Reinicialização do Serviço

**Files:**
- N/A

- [x] **Step 1: Run full test suite**

Run: `make test`  
Expected: PASS all tests with 0 failures.

- [x] **Step 2: Restart systemd user service**

Run: `systemctl --user restart manhua-manager.service`  
Run: `systemctl --user status manhua-manager.service`  
Expected: `Active: active (running)`

- [x] **Step 3: Test live API response**

Run: `curl -s http://localhost:5000/api/manhuas | grep -o 'https://asurascans.com[^"]*'`  
Expected: `https://asurascans.com/comics/overgeared-11fe7da3/chapter/{chapter}`
