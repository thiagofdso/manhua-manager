# Embedded Reader, Eye View Button & Edit Modal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar o leitor embutido com iframe (`#readerView`), botão de visualização rápida (`👁️`), botão e modal de edição completa (`✏️`), e suporte backend para atualização de título, url e capítulo.

**Architecture:** O backend Flask atualiza `PATCH /api/manhuas/<id>` para permitir edição de título, template de URL e capítulo. O frontend em `index.html` ganha uma nova tela de leitura embutida (`#readerView`) com `iframe` e barra de ferramentas, botões de ação nos cards da lista, e modal responsivo de edição (`#editModal`).

**Tech Stack:** Python, Flask, Pytest, Vanilla JS, CSS3, HTML5, Systemd.

## Global Constraints
- Diretório de trabalho: `/home/thiagofdso/Projetos/manhua-manager`
- Manter o tema escuro moderno e responsividade mobile (PWA).
- Assegurar que `event.stopPropagation()` evite abrir o leitor quando os botões de ação (👁️, ✏️) forem clicados.
- Serviço systemd de usuário: `manhua-manager.service`.

---

### Task 1: Backend Full Edit in `PATCH /api/manhuas/<id>`

**Files:**
- Modify: `tests/test_server.py`
- Modify: `server.py`

**Interfaces:**
- Produces: `PATCH /api/manhuas/<int:item_id>` aceitando `{ "title": ..., "urlTemplate": ..., "chapter": ... }`.

- [ ] **Step 1: Write test for full edit in `tests/test_server.py`**

```python
def test_patch_full_edit(client):
    payload = {
        "title": "Overgeared (Renomeado)",
        "urlTemplate": "https://novo-site.com/obra/chapter-{chapter}/",
        "chapter": 200
    }
    res = client.patch("/api/manhuas/100", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["item"]["title"] == "Overgeared (Renomeado)"
    assert data["item"]["urlTemplate"] == "https://novo-site.com/obra/chapter-{chapter}/"
    assert data["item"]["currentChapter"] == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_server.py::test_patch_full_edit -v`
Expected: FAIL (title and urlTemplate not updated by current implementation).

- [ ] **Step 3: Update `update_chapter` in `server.py`**

```python
@app.route("/api/manhuas/<int:item_id>", methods=["PATCH"])
def update_chapter(item_id):
    payload = request.get_json() or {}
    data = load_data()
    for m in data:
        if m["id"] == item_id:
            if "title" in payload and str(payload["title"]).strip():
                m["title"] = str(payload["title"]).strip()
            if "urlTemplate" in payload and str(payload["urlTemplate"]).strip():
                m["urlTemplate"] = str(payload["urlTemplate"]).strip()
            if "chapter" in payload:
                m["currentChapter"] = max(1, int(payload["chapter"]))
            elif "delta" in payload:
                m["currentChapter"] = max(1, m["currentChapter"] + int(payload["delta"]))
            m["updatedAt"] = int(time.time())
            save_data(data)
            return jsonify({"status": "ok", "item": m})
    return jsonify({"error": "Item não encontrado"}), 404
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_server.py -v`
Expected: PASS (all server tests pass).

- [ ] **Step 5: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat: support full edit (title, urlTemplate, chapter) in PATCH endpoint"
```

---

### Task 2: Frontend SPA Enhancements (`index.html`)

**Files:**
- Modify: `tests/test_pwa_assets.py`
- Modify: `index.html`

**Interfaces:**
- Produces: Visualização de lista com botões de leitura direta, visualizar (👁️), e editar (✏️).
- Produces: Modal de edição `#editModal` com campos e botões Salvar / Cancelar.
- Produces: `#readerView` contendo barra de navegação e `iframe` responsivo.

- [ ] **Step 1: Write test for new UI components in `tests/test_pwa_assets.py`**

```python
def test_embedded_reader_and_edit_modal_in_index(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "readerView" in html
    assert "editModal" in html
    assert "openReader" in html
    assert "openEditModal" in html
    assert "iframe" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_pwa_assets.py::test_embedded_reader_and_edit_modal_in_index -v`
Expected: FAIL.

- [ ] **Step 3: Update `index.html`**

Implement:
1. Styles for `#readerView`, toolbar, action buttons (`.action-btn`), modal backdrop (`.modal-backdrop`), and modal dialog.
2. Markup:
   - `#listView`: cada card exibe título e badge à esquerda (clicáveis para abrir `#readerView`), e à direita botões `👁️` e `✏️`.
   - `#detailView`: adicionado botão `✏️ Editar` e botão `📖 Ler Capítulo Atual` abrindo `#readerView`.
   - `#readerView`: tela com barra fixa contendo `← Voltar`, título da obra, capítulo, controles `◀`, `▶`, e `↗ Abrir Externo`, mais `iframe` ocupando a área inferior.
   - `#editModal`: diálogo com Nome, URL / Template e Capítulo Atual, além de validação para `{chapter}`.
3. JavaScript:
   - Funções: `openReader(id, event)`, `closeReader()`, `openEditModal(id, event)`, `closeEditModal()`, `saveEditManhua()`, `changeReaderChapter(delta)`.

- [ ] **Step 4: Run tests to verify**

Run: `.venv/bin/pytest tests/test_pwa_assets.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add index.html tests/test_pwa_assets.py
git commit -m "feat: add embedded iframe reader, eye view button and edit modal to UI"
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

- [ ] **Step 3: Verify HTTP responses and UI content**

Run:
```bash
curl -s http://localhost:5000/ | grep -E "readerView|editModal"
```
Expected: Output showing readerView and editModal.

- [ ] **Step 4: Commit**

```bash
git commit --allow-empty -m "chore: verify embedded reader and edit modal implementation"
```
