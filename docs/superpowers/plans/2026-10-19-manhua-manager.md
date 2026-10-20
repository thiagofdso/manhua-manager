# Manhua Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir uma aplicação web local (Flask + SPA + PWA) para gerenciar o progresso de leitura de manhuas/mangás (iniciando com Overgeared cap. 197), com controle via Makefile, integração com systemd (`systemctl --user`) e atalho na Área de Trabalho (`~/Área de trabalho`).

**Architecture:** O backend em Python Flask expõe rotas REST persistidas em `database.json` e serve o frontend SPA em Vanilla HTML/CSS/JS. Suporta PWA (`manifest.json` + `sw.js` + ícones PNG). Um script shell e um Makefile fornecem alvos de inicialização, controle de serviço via systemd de usuário e criação de atalho na Área de Trabalho com abertura de navegador.

**Tech Stack:** Python 3, Flask, Flask-CORS, Pytest, Vanilla JS/HTML5/CSS3 (Dark Theme), Systemd User Services, Linux Desktop Entry (.desktop).

## Global Constraints
- Diretório de trabalho do projeto: `/home/thiagofdso/Projetos/manhua-manager`
- Obra inicial pré-cadastrada: Overgeared com `https://manhuatop.org/manhua/overgeared-org/chapter-{chapter}/` e capítulo 197.
- Porta padrão: `5000` escutando em `0.0.0.0` para permitir acesso Wi-Fi.
- Ambiente virtual local: `.venv` criado na raiz do projeto.
- Atalho na Área de Trabalho: `/home/thiagofdso/Área de trabalho/manhua-tracker.desktop`.
- Serviço de Usuário Systemd: `~/.config/systemd/user/manhua-manager.service`.

---

### Task 1: Environment & Initial Database Seed

**Files:**
- Create: `requirements.txt`
- Create: `database.json`
- Test: `tests/test_database_seed.py`

**Interfaces:**
- Produces: `requirements.txt` com as dependências `flask`, `flask-cors`, `pytest`, `pillow`.
- Produces: `database.json` contendo o registro inicial de Overgeared no capítulo 197.

- [ ] **Step 1: Write test for database seed structure**

```python
# tests/test_database_seed.py
import json
import os

def test_initial_database_seed():
    db_path = os.path.join(os.path.dirname(__file__), "..", "database.json")
    assert os.path.exists(db_path), "database.json must exist"
    
    with open(db_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    assert isinstance(data, list)
    assert len(data) >= 1
    overgeared = next((item for item in data if "Overgeared" in item.get("title", "")), None)
    assert overgeared is not None
    assert overgeared["currentChapter"] == 197
    assert "https://manhuatop.org/manhua/overgeared-org/chapter-{chapter}/" in overgeared["urlTemplate"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_database_seed.py -v` (ou execute via venv quando criado).
Expected: FAIL (file `database.json` does not exist yet).

- [ ] **Step 3: Create requirements.txt and database.json**

```text
# requirements.txt
flask>=3.0.0
flask-cors>=4.0.0
pytest>=8.0.0
pillow>=10.0.0
```

```json
[
  {
    "id": 1,
    "title": "Overgeared",
    "urlTemplate": "https://manhuatop.org/manhua/overgeared-org/chapter-{chapter}/",
    "currentChapter": 197,
    "updatedAt": 1792454400
  }
]
```

- [ ] **Step 4: Create virtual environment and install requirements**

Run:
```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_database_seed.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add requirements.txt database.json tests/test_database_seed.py
git commit -m "chore: setup dependencies and initial database seed"
```

---

### Task 2: Backend API & Static Server (`server.py`)

**Files:**
- Create: `server.py`
- Create: `tests/test_server.py`

**Interfaces:**
- Consumes: `database.json`
- Produces: Flask application instance `app` com rotas:
  - `GET /api/manhuas` -> Retorna lista ordenada por `updatedAt` decrescente
  - `POST /api/manhuas` -> Insere novo manhua `{ title, urlTemplate, currentChapter }`
  - `PATCH /api/manhuas/<int:item_id>` -> Atualiza `{ chapter }` ou `{ delta }`
  - `DELETE /api/manhuas/<int:item_id>` -> Remove manhua
  - `GET /` e `GET /<path:filename>` -> Entrega arquivos estáticos

- [ ] **Step 1: Write tests for Flask API endpoints**

```python
# tests/test_server.py
import pytest
import json
import os
import tempfile
import server

@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db = tmp_path / "test_db.json"
    initial_data = [
        {
            "id": 100,
            "title": "Overgeared",
            "urlTemplate": "https://manhuatop.org/manhua/overgeared-org/chapter-{chapter}/",
            "currentChapter": 197,
            "updatedAt": 1000
        }
    ]
    test_db.write_text(json.dumps(initial_data), encoding="utf-8")
    monkeypatch.setattr(server, "DB_FILE", str(test_db))
    server.app.config["TESTING"] = True
    with server.app.test_client() as client:
        yield client

def test_get_manhuas(client):
    res = client.get("/api/manhuas")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data) == 1
    assert data[0]["title"] == "Overgeared"
    assert data[0]["currentChapter"] == 197

def test_add_manhua(client):
    payload = {
        "title": "Solo Leveling",
        "urlTemplate": "https://exemplo.com/chapter-{chapter}/",
        "currentChapter": 10
    }
    res = client.post("/api/manhuas", json=payload)
    assert res.status_code == 200
    res_data = res.get_json()
    assert res_data["status"] == "ok"
    assert res_data["item"]["title"] == "Solo Leveling"

def test_patch_chapter_delta(client):
    res = client.patch("/api/manhuas/100", json={"delta": 1})
    assert res.status_code == 200
    data = res.get_json()
    assert data["item"]["currentChapter"] == 198

def test_patch_chapter_specific(client):
    res = client.patch("/api/manhuas/100", json={"chapter": 205})
    assert res.status_code == 200
    data = res.get_json()
    assert data["item"]["currentChapter"] == 205

def test_delete_manhua(client):
    res = client.delete("/api/manhuas/100")
    assert res.status_code == 200
    list_res = client.get("/api/manhuas")
    assert len(list_res.get_json()) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_server.py -v`
Expected: FAIL (No module named `server`)

- [ ] **Step 3: Implement `server.py`**

```python
# server.py
import os
import json
import time
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "database.json")

app = Flask(__name__, static_folder=BASE_DIR)
CORS(app)

def load_data():
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(BASE_DIR, filename)

@app.route("/api/manhuas", methods=["GET"])
def get_manhuas():
    data = load_data()
    data.sort(key=lambda x: x.get("updatedAt", 0), reverse=True)
    return jsonify(data)

@app.route("/api/manhuas", methods=["POST"])
def add_manhua():
    payload = request.get_json() or {}
    if not payload.get("title") or not payload.get("urlTemplate") or payload.get("currentChapter") is None:
        return jsonify({"error": "Dados inválidos"}), 400
    
    data = load_data()
    new_item = {
        "id": int(time.time() * 1000),
        "title": payload["title"].strip(),
        "urlTemplate": payload["urlTemplate"].strip(),
        "currentChapter": max(1, int(payload["currentChapter"])),
        "updatedAt": int(time.time())
    }
    data.append(new_item)
    save_data(data)
    return jsonify({"status": "ok", "item": new_item})

@app.route("/api/manhuas/<int:item_id>", methods=["PATCH"])
def update_chapter(item_id):
    payload = request.get_json() or {}
    data = load_data()
    for m in data:
        if m["id"] == item_id:
            if "chapter" in payload:
                m["currentChapter"] = max(1, int(payload["chapter"]))
            elif "delta" in payload:
                m["currentChapter"] = max(1, m["currentChapter"] + int(payload["delta"]))
            m["updatedAt"] = int(time.time())
            save_data(data)
            return jsonify({"status": "ok", "item": m})
    return jsonify({"error": "Item não encontrado"}), 404

@app.route("/api/manhuas/<int:item_id>", methods=["DELETE"])
def delete_manhua(item_id):
    data = [m for m in load_data() if m["id"] != item_id]
    save_data(data)
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_server.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat: implement backend API and static server"
```

---

### Task 3: PWA Assets & Frontend SPA (`index.html`, `manifest.json`, `sw.js`, icons)

**Files:**
- Create: `generate_icons.py` (script helper para gerar os PNGs de ícone)
- Create: `icon-192.png`
- Create: `icon-512.png`
- Create: `manifest.json`
- Create: `sw.js`
- Create: `index.html`
- Create: `tests/test_pwa_assets.py`

**Interfaces:**
- Produces: `index.html` SPA completo com suporte PWA.
- Produces: `manifest.json` e `sw.js` servidos pela raiz.
- Produces: `icon-192.png` e `icon-512.png`.

- [ ] **Step 1: Write test for frontend and PWA assets availability**

```python
# tests/test_pwa_assets.py
import pytest
import server
import os

@pytest.fixture
def client():
    server.app.config["TESTING"] = True
    with server.app.test_client() as client:
        yield client

def test_index_html_exists_and_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Manhua Tracker" in res.data
    assert b"manifest.json" in res.data

def test_manifest_and_sw_served(client):
    res_manifest = client.get("/manifest.json")
    assert res_manifest.status_code == 200
    assert b"Manhua Tracker" in res_manifest.data

    res_sw = client.get("/sw.js")
    assert res_sw.status_code == 200

def test_icons_exist(client):
    res_192 = client.get("/icon-192.png")
    assert res_192.status_code == 200
    res_512 = client.get("/icon-512.png")
    assert res_512.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_pwa_assets.py -v`
Expected: FAIL (files missing).

- [ ] **Step 3: Create icon generator and build `icon-192.png` and `icon-512.png`**

```python
# generate_icons.py
from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size, filename):
    img = Image.new("RGBA", (size, size), color=(18, 18, 20, 255))
    draw = ImageDraw.Draw(img)
    
    # Outer circle with accent color
    pad = int(size * 0.08)
    draw.rounded_rectangle([pad, pad, size - pad, size - pad], radius=int(size * 0.2), fill=(130, 87, 230, 255))
    
    # Book / Bookmark shape
    cx, cy = size // 2, size // 2
    w = int(size * 0.45)
    h = int(size * 0.5)
    left = cx - w // 2
    top = cy - h // 2
    draw.rectangle([left, top, cx - int(size * 0.02), top + h], fill=(255, 255, 255, 240))
    draw.rectangle([cx + int(size * 0.02), top, left + w, top + h], fill=(235, 235, 245, 240))
    
    # Bookmark ribbon
    ribbon_w = int(size * 0.1)
    ribbon_h = int(size * 0.25)
    rx = cx - ribbon_w // 2
    draw.rectangle([rx, top, rx + ribbon_w, top + ribbon_h], fill=(255, 180, 50, 255))
    
    img.save(filename, "PNG")

if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    create_icon(192, os.path.join(base, "icon-192.png"))
    create_icon(512, os.path.join(base, "icon-512.png"))
    print("Icons generated successfully.")
```
Run: `.venv/bin/python3 generate_icons.py`

- [ ] **Step 4: Create `manifest.json` and `sw.js`**

```json
// manifest.json
{
  "name": "Manhua Tracker",
  "short_name": "Manhuas",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#121214",
  "theme_color": "#8257e6",
  "icons": [
    {
      "src": "icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

```javascript
// sw.js
const CACHE_NAME = 'manhua-v2';
self.addEventListener('install', (e) => self.skipWaiting());
self.addEventListener('activate', (e) => clients.claim());
self.addEventListener('fetch', (e) => {
  if (e.request.url.includes('/api/')) return;
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
```

- [ ] **Step 5: Create `index.html`**

Implement `index.html` including:
- Responsive styling, Dark Theme (`#121214`, cards `#202024`, primary `#8257e6`).
- List View (all saved manhuas, badge with current chapter, button "+ Novo").
- Detail View (title, large chapter number, "📖 Ler Capítulo Atual" direct link, Prev/Next buttons, direct chapter numeric input, delete option).
- Add form with dynamic `{chapter}` regex extraction.
- Automatic registration of `/sw.js`.

- [ ] **Step 6: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_pwa_assets.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add generate_icons.py icon-192.png icon-512.png manifest.json sw.js index.html tests/test_pwa_assets.py
git commit -m "feat: add frontend SPA, PWA manifest, service worker and icons"
```

---

### Task 4: Systemd Service, Desktop Shortcut & Control Script

**Files:**
- Create: `app.sh`
- Create: `manhua-manager.service`
- Create: `~/Área de trabalho/manhua-tracker.desktop`
- Modify: `tests/test_service_and_shortcut.py`

**Interfaces:**
- Produces: `app.sh` com subcomandos `start`, `stop`, `status`, `run`.
- Produces: `manhua-manager.service` pronto para instalação em `~/.config/systemd/user/`.
- Produces: `~/Área de trabalho/manhua-tracker.desktop` funcional e executável.

- [ ] **Step 1: Write test for script, service and desktop shortcut structure**

```python
# tests/test_service_and_shortcut.py
import os
import subprocess

def test_app_script_exists():
    script = os.path.join(os.path.dirname(__file__), "..", "app.sh")
    assert os.path.exists(script)
    assert os.access(script, os.X_OK)

def test_service_template_exists():
    service_file = os.path.join(os.path.dirname(__file__), "..", "manhua-manager.service")
    assert os.path.exists(service_file)
    content = open(service_file).read()
    assert "ExecStart=" in content
    assert "server.py" in content
    assert "Restart=always" in content

def test_desktop_shortcut_content():
    desktop_file = os.path.expanduser("~/Área de trabalho/manhua-tracker.desktop")
    if os.path.exists(os.path.expanduser("~/Área de trabalho")):
        assert os.path.exists(desktop_file)
        content = open(desktop_file).read()
        assert "[Desktop Entry]" in content
        assert "Name=Manhua Tracker" in content
        assert "http://localhost:5000" in content
```

- [ ] **Step 2: Create `app.sh`**

Implement `app.sh` allowing starting in background with PID tracking or foreground, stopping cleanly, and reporting status.
Run: `chmod +x app.sh`

- [ ] **Step 3: Create `manhua-manager.service`**

```ini
[Unit]
Description=Manhua Manager Tracker Service
After=network.target

[Service]
Type=simple
WorkingDirectory=%h/Projetos/manhua-manager
ExecStart=%h/Projetos/manhua-manager/.venv/bin/python3 %h/Projetos/manhua-manager/server.py
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
```

- [ ] **Step 4: Install desktop shortcut in `~/Área de trabalho`**

Create `~/Área de trabalho/manhua-tracker.desktop`:
```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=Manhua Tracker
Comment=Gerenciador de Manhuas e Leitura
Exec=sh -c "systemctl --user start manhua-manager.service 2>/dev/null || /home/thiagofdso/Projetos/manhua-manager/app.sh start; for i in $(seq 1 30); do curl -s http://localhost:5000 >/dev/null && break; sleep 0.2; done; xdg-open http://localhost:5000"
Icon=/home/thiagofdso/Projetos/manhua-manager/icon-192.png
Terminal=false
Categories=Utility;Application;
```
Run: `chmod +x ~/Área\ de\ trabalho/manhua-tracker.desktop`

- [ ] **Step 5: Run tests to verify**

Run: `.venv/bin/pytest tests/test_service_and_shortcut.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app.sh manhua-manager.service tests/test_service_and_shortcut.py
git commit -m "feat: add app control script, systemd user service unit and desktop shortcut"
```

---

### Task 5: Makefile & Systemd Automation

**Files:**
- Create: `Makefile`
- Test: execute Makefile targets: `make install`, `make test`, `make service-install`, `make service-start`, `make service-status`, `make service-stop`

**Interfaces:**
- Produces: `Makefile` com alvos:
  - `install`: Cria `.venv`, instala dependências e gera ícones
  - `run`: Inicia `server.py` no terminal
  - `start`: Inicia em background via `app.sh start`
  - `stop`: Encerra o servidor em background via `app.sh stop`
  - `status`: Exibe status do servidor
  - `service-install`: Instala unidade em `~/.config/systemd/user/` e faz `systemctl --user daemon-reload`
  - `service-enable`: Habilita serviço para inicialização com a sessão (`systemctl --user enable manhua-manager.service`)
  - `service-start`: Inicia serviço via `systemctl --user start manhua-manager.service`
  - `service-stop`: Para serviço via `systemctl --user stop manhua-manager.service`
  - `service-status`: Consulta status do serviço no systemctl
  - `shortcut`: Cria ou atualiza o atalho na Área de Trabalho
  - `test`: Executa suite completa de testes com pytest

- [ ] **Step 1: Create `Makefile`**

```makefile
.PHONY: help install run start stop status service-install service-enable service-start service-stop service-status shortcut test

VENV := .venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
DESKTOP_DIR := $(HOME)/Área de trabalho
SERVICE_DIR := $(HOME)/.config/systemd/user
SERVICE_NAME := manhua-manager.service

help:
	@echo "Comandos disponíveis:"
	@echo "  make install         - Cria venv e instala dependências"
	@echo "  make run             - Executa o servidor no terminal (foreground)"
	@echo "  make start           - Inicia o servidor em segundo plano"
	@echo "  make stop            - Para o servidor em segundo plano"
	@echo "  make status          - Verifica status do servidor"
	@echo "  make service-install - Instala o serviço systemd de usuário"
	@echo "  make service-enable  - Habilita inicialização automática com o sistema"
	@echo "  make service-start   - Inicia o serviço pelo systemd"
	@echo "  make service-stop    - Para o serviço pelo systemd"
	@echo "  make service-status  - Status do serviço no systemd"
	@echo "  make shortcut        - Cria o atalho na Área de Trabalho"
	@echo "  make test            - Roda os testes com pytest"

$(VENV)/bin/activate:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install: $(VENV)/bin/activate
	$(PYTHON) generate_icons.py
	@chmod +x app.sh
	@echo "Instalação concluída com sucesso."

run: install
	$(PYTHON) server.py

start: install
	./app.sh start

stop:
	./app.sh stop

status:
	./app.sh status

service-install: install
	mkdir -p "$(SERVICE_DIR)"
	cp $(SERVICE_NAME) "$(SERVICE_DIR)/$(SERVICE_NAME)"
	systemctl --user daemon-reload
	@echo "Serviço instalado em $(SERVICE_DIR)/$(SERVICE_NAME)"

service-enable: service-install
	systemctl --user enable $(SERVICE_NAME)

service-start:
	systemctl --user start $(SERVICE_NAME)

service-stop:
	systemctl --user stop $(SERVICE_NAME)

service-status:
	systemctl --user status $(SERVICE_NAME)

shortcut:
	@mkdir -p "$(DESKTOP_DIR)"
	@cp -f ~/Área\ de\ trabalho/manhua-tracker.desktop "$(DESKTOP_DIR)/manhua-tracker.desktop" 2>/dev/null || true
	@chmod +x "$(DESKTOP_DIR)/manhua-tracker.desktop"
	@echo "Atalho criado em: $(DESKTOP_DIR)/manhua-tracker.desktop"

test: install
	$(PYTEST) tests -v
```

- [ ] **Step 2: Test Makefile commands**

Run:
```bash
make test
make service-install
make service-start
make service-status
```
Expected: All tests pass, service starts and reports active (running).

- [ ] **Step 3: Test service stop**

Run: `make service-stop`
Expected: Service stops cleanly.

- [ ] **Step 4: Commit**

```bash
git add Makefile
git commit -m "feat: add Makefile with complete lifecycle, systemd and desktop targets"
```

---

### Task 6: Final Verification & Integration Check

**Files:**
- Verify: `database.json`, `server.py`, `index.html`, `manifest.json`, `sw.js`, `icon-192.png`, `icon-512.png`, `app.sh`, `Makefile`, `~/Área de trabalho/manhua-tracker.desktop`.

- [ ] **Step 1: Run full test suite**

Run: `make test`
Expected: All tests pass 100%.

- [ ] **Step 2: Enable and start systemd service**

Run: `make service-enable && make service-start`
Expected: Systemd service enabled and started.

- [ ] **Step 3: Verify HTTP responses**

Run:
```bash
curl -I http://localhost:5000/
curl -s http://localhost:5000/api/manhuas | grep "Overgeared"
```
Expected: HTTP 200 OK and JSON containing Overgeared at chapter 197.

- [ ] **Step 4: Commit all final artifacts**

```bash
git add .
git commit -m "chore: complete project implementation and verification"
```
