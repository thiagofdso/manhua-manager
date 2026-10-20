# Native Webtoon Continuous Image Reader & Image Proxy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar leitor nativo contínuo de webtoon/manhua com extração automática de páginas pelo backend Python e proxy de imagens com cabeçalho Referer, eliminando qualquer dependência de iframe e bloqueios de X-Frame-Options.

**Architecture:** O backend Flask ganha rotas `/api/chapter-images` (baixa HTML da fonte e extrai as URLs das páginas) e `/api/proxy-image` (faz proxy das imagens enviando Referer adequado). O frontend `index.html` remove o `iframe` e passa a renderizar as imagens em cascata vertical contínua com `loading="lazy"`.

**Tech Stack:** Python 3, Flask, Pytest, Vanilla JS, HTML5, CSS3, Systemd.

## Global Constraints
- Diretório de trabalho: `/home/thiagofdso/Projetos/manhua-manager`
- Manter o tema escuro responsivo para PC e celular.
- Serviço systemd de usuário: `manhua-manager.service`.

---

### Task 1: Backend Chapter Images Extraction and Image Proxy Endpoints

**Files:**
- Modify: `tests/test_server.py`
- Modify: `server.py`

**Interfaces:**
- Produces: `GET /api/chapter-images?url=...` -> `{ status: "ok", count: N, images: [...] }`
- Produces: `GET /api/proxy-image?url=...` -> image bytes com `Content-Type: image/jpeg` e cache headers

- [ ] **Step 1: Write tests for extraction and proxy in `tests/test_server.py`**

```python
from unittest.mock import patch, MagicMock

def test_get_chapter_images_endpoint(client):
    mock_html = """
    <html>
      <body>
        <img class="img-responsive" src="https://manhuatop.org/logo.png" />
        <img src="https://manhuatop.org/about_manhuatop.webp" class="wp-manga-chapter-img" />
        <img id="image-0" src="https://s2.manhuatop.org/chapter_197/page_1.jpg" class="wp-manga-chapter-img" />
        <img id="image-1" class="wp-manga-chapter-img" src="https://s2.manhuatop.org/chapter_197/page_2.jpg" />
      </body>
    </html>
    """.encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.read.return_value = mock_html
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = client.get("/api/chapter-images?url=https://manhuatop.org/manhua/test/chapter-1/")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "ok"
        assert len(data["images"]) == 2
        assert "page_1.jpg" in data["images"][0]
        assert "page_2.jpg" in data["images"][1]

def test_proxy_image_endpoint(client):
    mock_image_bytes = b"\xff\xd8\xff\xe0fake_jpeg_content"
    mock_resp = MagicMock()
    mock_resp.read.return_value = mock_image_bytes
    mock_resp.headers = {"Content-Type": "image/jpeg"}
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = client.get("/api/proxy-image?url=https://s2.manhuatop.org/test.jpg")
        assert res.status_code == 200
        assert res.data == mock_image_bytes
        assert res.content_type == "image/jpeg"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_server.py::test_get_chapter_images_endpoint -v`
Expected: FAIL (404 NOT FOUND).

- [ ] **Step 3: Implement extraction and proxy endpoints in `server.py`**

```python
import urllib.request
import urllib.parse
from flask import Response

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

        # Extract wp-manga-chapter-img occurrences
        raw_imgs = re.findall(r'<img[^>]+src=[\"\']([^\"\']+)[\"\'][^>]*class=[\"\'][^\"\']*wp-manga-chapter-img[^\"\']*[\"\']', html, re.IGNORECASE)
        raw_imgs += re.findall(r'<img[^>]+class=[\"\'][^\"\']*wp-manga-chapter-img[^\"\']*[\"\'][^>]+src=[\"\']([^\"\']+)[\"\']', html, re.IGNORECASE)

        # Remove duplicate preserving order and filter ads/promo
        seen = set()
        chapter_imgs = []
        for img in raw_imgs:
            clean = img.strip()
            if clean and clean not in seen and "about_manhuatop" not in clean:
                seen.add(clean)
                chapter_imgs.append(clean)

        return jsonify({
            "status": "ok",
            "count": len(chapter_imgs),
            "images": chapter_imgs
        })
    except Exception as e:
        return jsonify({"error": str(e), "images": []}), 500

@app.route("/api/proxy-image", methods=["GET"])
def proxy_image():
    img_url = request.args.get("url")
    if not img_url:
        return jsonify({"error": "Parâmetro url é obrigatório"}), 400

    parsed = urllib.parse.urlparse(img_url)
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

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_server.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat: add chapter images extractor and image proxy endpoints"
```

---

### Task 2: Frontend Native Continuous Webtoon Reader (`index.html`)

**Files:**
- Modify: `tests/test_pwa_assets.py`
- Modify: `index.html`

**Interfaces:**
- Produces: `#readerImagesContainer` com suporte a rolagem contínua vertical e lazy loading.
- Produces: Spinner de carregamento e mensagem de erro com fallback para site externo.

- [ ] **Step 1: Write tests for native reader in `tests/test_pwa_assets.py`**

```python
def test_native_continuous_reader_in_index(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "readerImagesContainer" in html
    assert "api/chapter-images" in html
    assert "api/proxy-image" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_pwa_assets.py::test_native_continuous_reader_in_index -v`
Expected: FAIL.

- [ ] **Step 3: Update `index.html` with continuous reader**

Implement:
1. Styles for `#readerView`:
   - `#readerImagesContainer`: vertical flex or block column, dark background `#0a0a0c`, images centered `max-width: 800px; width: 100%; display: block; margin: 0 auto; box-shadow: 0 4px 16px rgba(0,0,0,0.4);`.
2. Markup:
   - Remove `<iframe id="readerFrame">`.
   - Add `<div id="readerImagesContainer" class="reader-content-scroll"></div>`.
   - Add `<div id="readerLoading" class="reader-status-msg">Carregando páginas...</div>`.
   - Add `<div id="readerError" class="reader-status-msg" style="display:none;"></div>`.
3. JavaScript:
   - `openReader(id, event)`: fetches `/api/chapter-images?url=...`.
   - On success: renders `<img src="/api/proxy-image?url=${encodeURIComponent(img)}" loading="lazy" class="chapter-page-img" />` for each page.
   - On error: displays error message and button to open external link.
   - Smooth scroll to top on chapter change.

- [ ] **Step 4: Run tests to verify**

Run: `.venv/bin/pytest tests/test_pwa_assets.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add index.html tests/test_pwa_assets.py
git commit -m "feat: replace iframe with native continuous webtoon reader"
```

---

### Task 3: Final Verification & Service Reload

**Files:**
- Systemd: `systemctl --user restart manhua-manager.service`
- Tests: `make test`

- [ ] **Step 1: Restart systemd service**

Run: `systemctl --user restart manhua-manager.service && sleep 1 && systemctl --user status manhua-manager.service`
Expected: Service active (running).

- [ ] **Step 2: Run full test suite**

Run: `make test`
Expected: All tests pass.

- [ ] **Step 3: Test real live extraction on Overgeared Chapter 197**

Run:
```bash
curl -s "http://localhost:5000/api/chapter-images?url=https://manhuatop.org/manhua/overgeared-org/chapter-197/" | grep -o '"count":[0-9]*'
```
Expected: `"count":10` (confirms real pages extracted live).

- [ ] **Step 4: Commit**

```bash
git commit --allow-empty -m "chore: complete native continuous reader implementation"
```
