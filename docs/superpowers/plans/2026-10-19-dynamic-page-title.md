# Dynamic Page Title Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Atualizar dinamicamente o título da página (`document.title`) para o formato `<Título> <Capítulo>` (ex: `Overgeared 199`) durante a leitura e detalhes, retornando a `Manhua Tracker` na tela inicial.

**Architecture:** Modificação das funções de manipulação de visualização e cabeçalho em `index.html` (`updateReaderHeader`, `renderDetails`, `closeReader` e `showListView`).

**Tech Stack:** JavaScript (ES6+), HTML5, Python/pytest para testes estáticos e funcionais de assets.

## Global Constraints

- O formato deve ser exatamente `<Título> <Capítulo>` (sem caracteres extras, conforme escolha do usuário).
- Na lista principal e ao fechar o leitor, restaurar para `Manhua Tracker`.
- Seguir TDD rigoroso com verificação antes e depois da implementação.

---

### Task 1: Testes de Título Dinâmico

**Files:**
- Modify: `tests/test_pwa_assets.py`

**Interfaces:**
- Produces: Teste automatizado verificando a presença da lógica de título dinâmico em `index.html`.

- [ ] **Step 1: Write the failing test**

Adicionar em `tests/test_pwa_assets.py`:
```python
def test_dynamic_page_title_in_index():
    index_path = os.path.join(os.path.dirname(__file__), "..", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verifica atualização no leitor
    assert "document.title = `${readerManhua.title} ${readerManhua.currentChapter}`" in content
    # Verifica atualização nos detalhes
    assert "document.title = `${selectedManhua.title} ${selectedManhua.currentChapter}`" in content
    # Verifica restauração para o título padrão
    assert "document.title = 'Manhua Tracker'" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_pwa_assets.py -k "test_dynamic_page_title" -v`  
Expected: FAIL (AssertionError)

- [ ] **Step 3: Commit test change**

```bash
git add tests/test_pwa_assets.py
git commit -m "test: add test for dynamic page title in index.html"
```

---

### Task 2: Implementação em `index.html`

**Files:**
- Modify: `index.html`

**Interfaces:**
- Produces: `document.title` atualizado em `updateReaderHeader`, `renderDetails`, `showListView` e `closeReader`.

- [ ] **Step 1: Implement minimal changes in `index.html`**

No `index.html`:
1. Em `showListView()`:
   ```javascript
   function showListView() {
     selectedManhua = null;
     document.title = 'Manhua Tracker';
     switchView('listView');
     loadData();
   }
   ```
2. Em `renderDetails()`:
   ```javascript
   function renderDetails() {
     if (!selectedManhua) return;
     document.title = `${selectedManhua.title} ${selectedManhua.currentChapter}`;
     document.getElementById('detailTitle').innerText = selectedManhua.title;
   ...
   ```
3. Em `updateReaderHeader()`:
   ```javascript
   function updateReaderHeader() {
     if (!readerManhua) return;
     document.title = `${readerManhua.title} ${readerManhua.currentChapter}`;
     const url = readerManhua.urlTemplate.replace('{chapter}', readerManhua.currentChapter);
   ...
   ```
4. Em `closeReader()`:
   ```javascript
   function closeReader() {
     document.getElementById('readerImagesContainer').innerHTML = '';
     if (previousView === 'detailView' && selectedManhua) {
       document.title = `${selectedManhua.title} ${selectedManhua.currentChapter}`;
     } else {
       document.title = 'Manhua Tracker';
     }
     switchView(previousView || 'listView');
     loadData();
   }
   ```

- [ ] **Step 2: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_pwa_assets.py -k "test_dynamic_page_title" -v`  
Expected: PASS

- [ ] **Step 3: Commit implementation**

```bash
git add index.html
git commit -m "feat: dynamically update page title with manhua title and chapter"
```

---

### Task 3: Validação Completa do Sistema

**Files:**
- N/A

- [ ] **Step 1: Run full test suite**

Run: `make test`  
Expected: 24 passed in all test suites.

- [ ] **Step 2: Restart systemd user service**

Run: `systemctl --user restart manhua-manager.service`  
Run: `systemctl --user status manhua-manager.service --no-pager`  
Expected: `active (running)`.
