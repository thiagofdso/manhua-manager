Aqui está a **síntese completa dos requisitos**, arquitetura e o **código pronto** (Frontend + Backend + PWA) com todas as funcionalidades que você pediu:

---

### 1. Síntese dos Requisitos

1. **Gestão de Manhuas:**
* Cadastrar obra com Nome, URL do capítulo atual e número do capítulo.
* Decomposição automática do número do episódio na URL para um template dinâmico (`.../chapter-{chapter}/`).
* Excluir e editar obras.


2. **Controle de Episódios/Capítulos:**
* Avançar (+1) ou Voltar (-1).
* **Digitar/selecionar um capítulo específico** diretamente por um campo numérico com confirmação.
* Atualização e persistência automática no servidor (`database.json` no notebook).


3. **Fluxo de Navegação & Leitura:**
* **Tela Principal:** Lista de todos os manhuas cadastrados com status atual, data de última leitura e atalhos rápidos.
* **Tela/Modo de Leitura e Gerenciamento do Manhua:** Foco na obra selecionada, permitindo abrir o link exato do episódio, trocar de capítulo sem sair da visualização e voltar para a lista geral com um clique.


4. **Hospedagem Local & PWA (Brave no Celular):**
* Servidor Python leve rodando no notebook em `0.0.0.0:5000` (acessível pelo Wi-Fi).
* Suporte a PWA (`manifest.json` + `sw.js` com `display: standalone`).
* Liberação no Brave Android via `brave://flags` (`unsafely-treat-insecure-origin-as-secure`).



---

### 2. Estrutura dos Arquivos no Notebook

Crie uma pasta no notebook (ex: `manhua-app`) com a seguinte estrutura:

```text
manhua-app/
├── server.py
├── index.html
├── manifest.json
├── sw.js
├── icon-192.png (opcional para o ícone)
└── icon-512.png (opcional para o ícone)

```

---

### 3. Código do Backend (`server.py`)

Garante a persistência em arquivo JSON para sincronizar notebook e celular:

```python
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json, os, time

app = Flask(__name__, static_folder=".")
CORS(app)
DB_FILE = "database.json"

def load_data():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(".", filename)

@app.route("/api/manhuas", methods=["GET"])
def get_manhuas():
    # Retorna ordenado pela última leitura
    data = load_data()
    data.sort(key=lambda x: x.get("updatedAt", 0), reverse=True)
    return jsonify(data)

@app.route("/api/manhuas", methods=["POST"])
def add_manhua():
    payload = request.json
    data = load_data()
    new_item = {
        "id": int(time.time() * 1000),
        "title": payload["title"],
        "urlTemplate": payload["urlTemplate"],
        "currentChapter": int(payload["currentChapter"]),
        "updatedAt": int(time.time())
    }
    data.append(new_item)
    save_data(data)
    return jsonify({"status": "ok", "item": new_item})

@app.route("/api/manhuas/<int:item_id>", methods=["PATCH"])
def update_chapter(item_id):
    payload = request.json
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
    app.run(host="0.0.0.0", port=5000, debug=True)

```

---

### 4. PWA Configuração

#### `manifest.json`

```json
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

#### `sw.js`

```javascript
const CACHE_NAME = 'manhua-v2';
self.addEventListener('install', (e) => self.skipWaiting());
self.addEventListener('activate', (e) => clients.claim());
self.addEventListener('fetch', (e) => {
  if (e.request.url.includes('/api/')) return;
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});

```

---

### 5. Interface Completa (`index.html`)

Possui duas visões: **Lista de Manhuas** e **Detalhe da Obra Selecionada** (com controles de navegação direta, avançar, voltar e seleção manual de capítulo).

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <title>Manhua Tracker</title>
  <link rel="manifest" href="manifest.json" />
  <meta name="theme-color" content="#121214" />
  <style>
    :root {
      --bg: #121214;
      --card: #202024;
      --card-border: #323238;
      --primary: #8257e6;
      --primary-hover: #9466ff;
      --text: #e1e1e6;
      --muted: #a8a8b3;
      --danger: #e57878;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background-color: var(--bg); color: var(--text); padding: 16px; min-height: 100vh; }
    .container { max-width: 600px; margin: 0 auto; }
    header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
    h1 { font-size: 1.4rem; }
    
    .view { display: none; }
    .view.active { display: block; }

    /* Cards e Formulário */
    .card { background: var(--card); border: 1px solid var(--card-border); border-radius: 12px; padding: 16px; margin-bottom: 16px; }
    label { font-size: 0.85rem; color: var(--muted); margin-bottom: 4px; display: block; }
    input { width: 100%; padding: 12px; background: #18181b; border: 1px solid var(--card-border); border-radius: 8px; color: #fff; margin-bottom: 12px; font-size: 1rem; }
    
    .btn { background: var(--primary); color: #fff; border: none; padding: 12px; border-radius: 8px; font-weight: 600; cursor: pointer; text-align: center; text-decoration: none; display: inline-flex; align-items: center; justify-content: center; gap: 8px; }
    .btn:active { opacity: 0.85; }
    .btn-secondary { background: #29292e; color: #fff; }
    .btn-danger { background: transparent; color: var(--danger); border: 1px solid var(--danger); }
    .w-full { width: 100%; }

    /* Lista de Obras */
    .manhua-item { display: flex; justify-content: space-between; align-items: center; cursor: pointer; }
    .manhua-item:hover { border-color: var(--primary); }
    .badge { background: #29292e; color: #a8a8b3; padding: 4px 8px; border-radius: 6px; font-size: 0.8rem; }

    /* Tela de Detalhes / Leitura */
    .detail-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
    .nav-buttons { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 16px 0; }
    .chapter-selector { display: flex; gap: 8px; margin-top: 12px; }
    .chapter-selector input { margin-bottom: 0; text-align: center; font-size: 1.1rem; }
  </style>
</head>
<body>
  <div class="container">

    <!-- TELA 1: LISTA DE MANHUAS -->
    <div id="listView" class="view active">
      <header>
        <h1>Meus Manhuas</h1>
        <button class="btn btn-secondary" onclick="toggleForm()">+ Novo</button>
      </header>

      <!-- Formulário de Cadastro (Recolhível) -->
      <div id="formSection" class="card" style="display: none;">
        <label>Nome do Manhua</label>
        <input type="text" id="title" placeholder="Ex: Overgeared" />
        <label>URL do Capítulo Atual</label>
        <input type="url" id="rawUrl" placeholder="https://exemplo.com/manga/chapter-197/" />
        <label>Capítulo Atual</label>
        <input type="number" id="chapter" placeholder="197" />
        <button class="btn w-full" onclick="saveNewManhua()">Cadastrar</button>
      </div>

      <div id="manhuaList"></div>
    </div>

    <!-- TELA 2: GERENCIAMENTO E LEITURA DA OBRA SELECIONADA -->
    <div id="detailView" class="view">
      <div class="detail-header">
        <button class="btn btn-secondary" onclick="showListView()">← Voltar</button>
        <h2 id="detailTitle" style="font-size: 1.2rem; flex: 1; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;"></h2>
      </div>

      <div class="card" style="text-align: center;">
        <p style="color: var(--muted); font-size: 0.9rem;">Capítulo Atual</p>
        <h1 id="detailChapter" style="font-size: 3rem; margin: 8px 0; color: var(--primary);"></h1>

        <!-- Botão Principal de Leitura -->
        <a id="btnReadNow" class="btn w-full" style="padding: 16px; font-size: 1.1rem; margin-bottom: 8px;" target="_blank">
          📖 Ler Capítulo Atual
        </a>

        <!-- Controles de Avançar / Voltar -->
        <div class="nav-buttons">
          <button class="btn btn-secondary" onclick="changeSelectedChapter(-1)">◀ Anterior</button>
          <button class="btn btn-secondary" onclick="changeSelectedChapter(1)">Próximo ▶</button>
        </div>

        <hr style="border: 0; border-top: 1px solid var(--card-border); margin: 16px 0;" />

        <!-- Seleção Direta de Capítulo -->
        <label>Ir diretamente para o capítulo:</label>
        <div class="chapter-selector">
          <input type="number" id="manualChapterInput" placeholder="Nº" />
          <button class="btn btn-secondary" onclick="setManualChapter()">Definir</button>
        </div>
      </div>

      <button class="btn btn-danger w-full" onclick="deleteCurrentManhua()">Remover Obra da Lista</button>
    </div>

  </div>

  <script>
    if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js');

    let manhuas = [];
    let selectedManhua = null;

    async function loadData() {
      const res = await fetch('/api/manhuas');
      manhuas = await res.json();
      renderList();
      if (selectedManhua) {
        selectedManhua = manhuas.find(m => m.id === selectedManhua.id) || null;
        if (selectedManhua) renderDetails();
        else showListView();
      }
    }

    function renderList() {
      const listEl = document.getElementById('manhuaList');
      if (!manhuas.length) {
        listEl.innerHTML = '<p style="text-align: center; color: var(--muted); margin-top: 40px;">Nenhum manhua salvo ainda.</p>';
        return;
      }
      listEl.innerHTML = manhuas.map(m => `
        <div class="card manhua-item" onclick="selectManhua(${m.id})">
          <div>
            <h3 style="font-size: 1.05rem; margin-bottom: 4px;">${m.title}</h3>
            <span class="badge">Capítulo ${m.currentChapter}</span>
          </div>
          <span style="color: var(--muted); font-size: 1.2rem;">›</span>
        </div>
      `).join('');
    }

    function toggleForm() {
      const form = document.getElementById('formSection');
      form.style.display = form.style.display === 'none' ? 'block' : 'none';
    }

    async function saveNewManhua() {
      const title = document.getElementById('title').value.trim();
      const rawUrl = document.getElementById('rawUrl').value.trim();
      const chapter = parseInt(document.getElementById('chapter').value, 10);

      if (!title || !rawUrl || isNaN(chapter)) return alert('Preencha todos os campos!');

      const regex = new RegExp(`(?<=[^0-9]|^)${chapter}(?=[^0-9]|$)`);
      if (!regex.test(rawUrl)) return alert('O número do capítulo não foi localizado na URL.');

      const urlTemplate = rawUrl.replace(regex, '{chapter}');
      await fetch('/api/manhuas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, urlTemplate, currentChapter: chapter })
      });

      toggleForm();
      document.getElementById('title').value = '';
      document.getElementById('rawUrl').value = '';
      document.getElementById('chapter').value = '';
      loadData();
    }

    function selectManhua(id) {
      selectedManhua = manhuas.find(m => m.id === id);
      renderDetails();
      document.getElementById('listView').classList.remove('active');
      document.getElementById('detailView').classList.add('active');
    }

    function showListView() {
      selectedManhua = null;
      document.getElementById('detailView').classList.remove('active');
      document.getElementById('listView').classList.add('active');
      loadData();
    }

    function renderDetails() {
      document.getElementById('detailTitle').innerText = selectedManhua.title;
      document.getElementById('detailChapter').innerText = selectedManhua.currentChapter;
      const targetUrl = selectedManhua.urlTemplate.replace('{chapter}', selectedManhua.currentChapter);
      
      const btnRead = document.getElementById('btnReadNow');
      btnRead.href = targetUrl;
      document.getElementById('manualChapterInput').value = selectedManhua.currentChapter;
    }

    async function changeSelectedChapter(delta) {
      const res = await fetch(`/api/manhuas/${selectedManhua.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ delta })
      });
      const data = await res.json();
      selectedManhua = data.item;
      renderDetails();
    }

    async function setManualChapter() {
      const input = document.getElementById('manualChapterInput');
      const val = parseInt(input.value, 10);
      if (isNaN(val) || val < 1) return;

      const res = await fetch(`/api/manhuas/${selectedManhua.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chapter: val })
      });
      const data = await res.json();
      selectedManhua = data.item;
      renderDetails();
    }

    async function deleteCurrentManhua() {
      if (!confirm(`Remover "${selectedManhua.title}" da sua lista?`)) return;
      await fetch(`/api/manhuas/${selectedManhua.id}`, { method: 'DELETE' });
      showListView();
    }

    loadData();
  </script>
</body>
</html>

```

---

### 6. Como Rodar e Instalar no Celular (Brave)

1. No terminal do seu notebook, instale as dependências:
```bash
pip install flask flask-cors

```


2. Inicie o servidor:
```bash
python server.py

```


3. Descubra o IP do notebook (`ipconfig` no Windows ou `ip a` no Linux/Mac).
4. No **Brave do celular**:
* Acesse `brave://flags` (ou `chrome://flags`).
* Procure por `unsafely-treat-insecure-origin-as-secure`.
* Mude para **Enabled**, preencha `[http://192.168.](http://192.168.)X.X:5000` e clique em **Relaunch**.


5. Abra `[http://192.168.](http://192.168.)X.X:5000` no Brave, toque no menu do navegador (três pontinhos) e selecione **"Instalar aplicativo"** ou **"Adicionar à tela inicial"**.