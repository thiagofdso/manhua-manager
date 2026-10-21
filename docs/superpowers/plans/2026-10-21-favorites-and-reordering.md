# Favoritos e Reordenação Manual Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar o sistema de favoritos com ícone de estrela e a reordenação manual de obras nas interfaces Web e Mobile (Flutter), assegurando no backend e frontend que obras favoritas nunca fiquem abaixo de não-favoritas e que atualizações de leitura promovam o item ao topo do seu respectivo grupo.

**Architecture:** O backend (`server.py`) passa a armazenar `isFavorite` (bool) e `customOrder` (int) para cada obra em `database.json`, ordenando a lista por `(not isFavorite, customOrder, -updatedAt)`. A interface Web (`index.html`) ganha um botão de estrela com ação imediata e um modo de movimentação inline em dois cliques com marcadores restritos ao grupo permitido. O app Flutter (`mobile_app`) ganha o botão de estrela nos cards e um modo "Editar Ordem" na `HomeScreen` com duas seções segregadas usando `ReorderableListView` ("★ Favoritas" e "Demais Obras"), impedindo nativamente o cruzamento de categorias.

**Tech Stack:** Python 3 (Flask, Pytest), HTML5/JavaScript vanilla (PWA), Dart / Flutter (Provider, Material 3, `ReorderableListView`).

## Global Constraints

- **Python Virtualenv:** Sempre executar testes backend com `./.venv/bin/pytest tests/`.
- **Flutter SDK:** Sempre executar comandos e testes Flutter com `/home/thiagofdso/development/flutter/bin/flutter`.
- **Regra de Ouro:** Obras favoritas (`isFavorite == true`) NUNCA podem aparecer abaixo de obras não-favoritas (`isFavorite == false`).
- **Regra Híbrida de Leitura:** Ao atualizar o capítulo de uma obra (`delta` ou `chapter`), a obra deve ir para o topo do seu respectivo grupo (`customOrder` recebe menor valor do grupo - 1).
- **Templates de URL:** Preservar rigorosamente o placeholder `{chapter}` em templates existentes e compatibilidade de provedores.
- **Serviço Systemd:** Gerenciado sem sudo via `systemctl --user restart manhua-manager.service`.

---

### Task 1: Backend Data Model, Helper Functions & Sorting in `server.py`

**Files:**
- Modify: `server.py:18-45`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `load_data()`, `save_data(data)`
- Produces: `sort_manhuas(data) -> list[dict]`, `GET /api/manhuas` ordenando por `isFavorite DESC, customOrder ASC, updatedAt DESC`.

- [ ] **Step 1: Write the failing test for sorting with favorites and customOrder**

Adicionar em `tests/test_server.py`:
```python
def test_get_manhuas_sorted_by_favorite_and_custom_order(client, temp_db):
    items = [
        {"id": 1, "title": "Obra Comum A", "urlTemplate": "https://example.com/{chapter}", "currentChapter": 10, "updatedAt": 100, "isFavorite": False, "customOrder": 2},
        {"id": 2, "title": "Obra Favorita 1", "urlTemplate": "https://example.com/{chapter}", "currentChapter": 20, "updatedAt": 50, "isFavorite": True, "customOrder": 1},
        {"id": 3, "title": "Obra Comum B", "urlTemplate": "https://example.com/{chapter}", "currentChapter": 30, "updatedAt": 150, "isFavorite": False, "customOrder": 0},
        {"id": 4, "title": "Obra Favorita 0", "urlTemplate": "https://example.com/{chapter}", "currentChapter": 40, "updatedAt": 80, "isFavorite": True, "customOrder": 0},
    ]
    with open(temp_db, "w", encoding="utf-8") as f:
        json.dump(items, f)

    res = client.get("/api/manhuas")
    assert res.status_code == 200
    data = res.get_json()
    ids = [m["id"] for m in data]
    # Esperado: Favoritas primeiro (ordenadas por customOrder 0, 1), depois Comuns (customOrder 0, 2)
    assert ids == [4, 2, 3, 1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/test_server.py -k test_get_manhuas_sorted_by_favorite_and_custom_order -v`  
Expected: FAIL (assertion error porque a lista atualmente ordena apenas por `updatedAt DESC`).

- [ ] **Step 3: Write minimal implementation in `server.py`**

Em `server.py`, adicione a função auxiliar `sort_manhuas` e atualize `get_manhuas`:
```python
def sort_manhuas(data):
    return sorted(
        data,
        key=lambda x: (
            not bool(x.get("isFavorite", False)),
            int(x.get("customOrder", 0)),
            -int(x.get("updatedAt", 0))
        )
    )

@app.route("/api/manhuas", methods=["GET"])
def get_manhuas():
    data = load_data()
    return jsonify(sort_manhuas(data))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/pytest tests/test_server.py -k test_get_manhuas_sorted_by_favorite_and_custom_order -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat(backend): add sorting by isFavorite and customOrder"
```

---

### Task 2: Backend Favorite Toggle & Hybrid Chapter Update Logic in `server.py`

**Files:**
- Modify: `server.py:100-185`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `PATCH /api/manhuas/<int:item_id>`
- Produces: 
  - Suporte a `{"isFavorite": bool}` promovendo a obra para o topo do seu grupo (`customOrder = min_group_order - 1`).
  - Suporte a `chapter` e `delta` aplicando a regra híbrida (`customOrder = min_group_order - 1`).

- [ ] **Step 1: Write the failing tests for favorite toggle and hybrid reading update**

Adicionar em `tests/test_server.py`:
```python
def test_patch_favorite_toggle(client, temp_db):
    items = [
        {"id": 1, "title": "Obra A", "urlTemplate": "https://example.com/{chapter}", "currentChapter": 10, "updatedAt": 100, "isFavorite": False, "customOrder": 0},
        {"id": 2, "title": "Obra B", "urlTemplate": "https://example.com/{chapter}", "currentChapter": 20, "updatedAt": 100, "isFavorite": True, "customOrder": 0},
    ]
    with open(temp_db, "w", encoding="utf-8") as f:
        json.dump(items, f)

    # Favorita Obra A -> deve virar favorita e receber customOrder menor que Obra B (topo das favoritas)
    res = client.patch("/api/manhuas/1", json={"isFavorite": True})
    assert res.status_code == 200
    data = res.get_json()["item"]
    assert data["isFavorite"] is True
    assert data["customOrder"] <= 0

    # Desfavorita Obra B -> deve virar comum
    res2 = client.patch("/api/manhuas/2", json={"isFavorite": False})
    assert res2.status_code == 200
    assert res2.get_json()["item"]["isFavorite"] is False


def test_patch_chapter_moves_to_top_of_group(client, temp_db):
    items = [
        {"id": 10, "title": "Fav 1", "urlTemplate": "https://example.com/{chapter}", "currentChapter": 5, "updatedAt": 100, "isFavorite": True, "customOrder": 0},
        {"id": 11, "title": "Fav 2", "urlTemplate": "https://example.com/{chapter}", "currentChapter": 8, "updatedAt": 90, "isFavorite": True, "customOrder": 1},
    ]
    with open(temp_db, "w", encoding="utf-8") as f:
        json.dump(items, f)

    # Ao avançar capítulo da Fav 2, ela deve ir para o topo das favoritas (menor customOrder)
    res = client.patch("/api/manhuas/11", json={"delta": 1})
    assert res.status_code == 200
    fav2 = res.get_json()["item"]
    assert fav2["currentChapter"] == 9

    res_list = client.get("/api/manhuas")
    manhuas = res_list.get_json()
    assert manhuas[0]["id"] == 11
    assert manhuas[1]["id"] == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/test_server.py -k "test_patch_favorite_toggle or test_patch_chapter_moves_to_top_of_group" -v`  
Expected: FAIL

- [ ] **Step 3: Implement favorite toggle and hybrid reading update in `server.py`**

Em `server.py`, dentro de `update_chapter(item_id)`:
```python
            # Tratar atualização de isFavorite
            if "isFavorite" in payload:
                new_fav = bool(payload["isFavorite"])
                m["isFavorite"] = new_fav
                # Calcula menor customOrder entre as obras do novo grupo para colocar no topo
                same_group_orders = [other.get("customOrder", 0) for other in data if other["id"] != m["id"] and bool(other.get("isFavorite", False)) == new_fav]
                min_order = min(same_group_orders) if same_group_orders else 0
                m["customOrder"] = min_order - 1

            # Ao alterar capítulo (chapter ou delta), aplicar regra híbrida: sobe para o topo do seu grupo
            if "chapter" in payload or "delta" in payload:
                cur_fav = bool(m.get("isFavorite", False))
                same_group_orders = [other.get("customOrder", 0) for other in data if other["id"] != m["id"] and bool(other.get("isFavorite", False)) == cur_fav]
                min_order = min(same_group_orders) if same_group_orders else 0
                m["customOrder"] = min_order - 1
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/pytest tests/test_server.py -k "test_patch_favorite_toggle or test_patch_chapter_moves_to_top_of_group" -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat(backend): implement favorite toggle and hybrid chapter promotion"
```

---

### Task 3: Backend Reorder Endpoint (`PUT /api/manhuas/reorder`) in `server.py`

**Files:**
- Modify: `server.py`
- Test: `tests/test_server.py`

**Interfaces:**
- Produces: `PUT /api/manhuas/reorder` com payload `{"order": [id1, id2, ...]}`
- Retorna `{"status": "ok", "items": [...]}` com integridade de favoritas preservada.

- [ ] **Step 1: Write failing tests for reorder endpoint and constraint enforcement**

Adicionar em `tests/test_server.py`:
```python
def test_put_reorder_valid(client, temp_db):
    items = [
        {"id": 1, "title": "A", "urlTemplate": "https://example.com/{chapter}", "currentChapter": 1, "isFavorite": True, "customOrder": 0},
        {"id": 2, "title": "B", "urlTemplate": "https://example.com/{chapter}", "currentChapter": 1, "isFavorite": True, "customOrder": 1},
        {"id": 3, "title": "C", "urlTemplate": "https://example.com/{chapter}", "currentChapter": 1, "isFavorite": False, "customOrder": 2},
    ]
    with open(temp_db, "w", encoding="utf-8") as f:
        json.dump(items, f)

    # Inverte as favoritas [2, 1, 3]
    res = client.put("/api/manhuas/reorder", json={"order": [2, 1, 3]})
    assert res.status_code == 200
    ordered = client.get("/api/manhuas").get_json()
    assert [m["id"] for m in ordered] == [2, 1, 3]


def test_put_reorder_enforces_favorites_on_top(client, temp_db):
    items = [
        {"id": 1, "title": "Fav", "urlTemplate": "https://example.com/{chapter}", "currentChapter": 1, "isFavorite": True, "customOrder": 0},
        {"id": 2, "title": "Comum", "urlTemplate": "https://example.com/{chapter}", "currentChapter": 1, "isFavorite": False, "customOrder": 1},
    ]
    with open(temp_db, "w", encoding="utf-8") as f:
        json.dump(items, f)

    # Tenta colocar a Comum antes da Fav [2, 1]
    res = client.put("/api/manhuas/reorder", json={"order": [2, 1]})
    assert res.status_code == 200
    ordered = client.get("/api/manhuas").get_json()
    # A regra de ouro deve autocorrigir garantindo que Fav sempre fique antes de Comum
    assert [m["id"] for m in ordered] == [1, 2]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/test_server.py -k "test_put_reorder_valid or test_put_reorder_enforces_favorites_on_top" -v`  
Expected: FAIL (404/405 endpoint não existe).

- [ ] **Step 3: Implement `PUT /api/manhuas/reorder` in `server.py`**

Adicionar em `server.py`:
```python
@app.route("/api/manhuas/reorder", methods=["PUT"])
def reorder_manhuas():
    payload = request.get_json() or {}
    order_ids = payload.get("order")
    if not isinstance(order_ids, list):
        return jsonify({"error": "Campo 'order' deve ser uma lista de IDs"}), 400

    data = load_data()
    id_map = {m["id"]: m for m in data}

    # Separar itens informados entre favoritos e não-favoritos preservando a ordem relativa enviada
    fav_items = []
    non_fav_items = []

    for item_id in order_ids:
        if item_id in id_map:
            item = id_map.pop(item_id)
            if item.get("isFavorite", False):
                fav_items.append(item)
            else:
                non_fav_items.append(item)

    # Adicionar itens remanescentes (que não estavam na lista enviada)
    for rem in id_map.values():
        if rem.get("isFavorite", False):
            fav_items.append(rem)
        else:
            non_fav_items.append(rem)

    # Regra de Ouro: Todas as favoritas SEMPRE precedem as não-favoritas
    final_ordered = fav_items + non_fav_items

    for idx, item in enumerate(final_ordered):
        item["customOrder"] = idx

    save_data(data)
    return jsonify({"status": "ok", "items": sort_manhuas(data)})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/pytest tests/test_server.py -k "test_put_reorder_valid or test_put_reorder_enforces_favorites_on_top" -v`  
Expected: PASS

- [ ] **Step 5: Run all backend tests to guarantee zero regression**

Run: `./.venv/bin/pytest tests/`  
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat(backend): add reorder endpoint enforcing favorites constraint"
```

---

### Task 4: Web Interface - Star Toggle, Dividers & Inline Reorder Mode in `index.html`

**Files:**
- Modify: `index.html`
- Test: `tests/test_pwa_assets.py` (ou teste dedicado de integração Web)

**Interfaces:**
- Produces:
  - Botão de estrela `★`/`☆` com clique direto chamando `toggleFavorite(id, event)`.
  - Cabeçalhos de seção visual ("★ Favoritas" e "Todas as Obras").
  - Botão `↕` nos cards abrindo modo de movimentação com marcadores `[+ Mover para cá]`.
  - Cancelamento via tecla `Esc` ou botão cancelar.
  - Persistência chamando `PUT /api/manhuas/reorder`.

- [ ] **Step 1: Add HTML/CSS for favorites, section titles, and move mode in `index.html`**

Adicionar estilos CSS em `index.html`:
```css
.star-btn { background: none; border: none; font-size: 1.3rem; cursor: pointer; padding: 4px; line-height: 1; transition: transform 0.2s, color 0.2s; }
.star-btn:hover { transform: scale(1.2); }
.star-btn.active { color: #f59e0b; }
.star-btn.inactive { color: #52525b; }
.star-btn.inactive:hover { color: #e4e4e7; }

.section-header { font-size: 0.95rem; font-weight: 600; color: var(--muted); margin: 20px 0 10px 4px; display: flex; align-items: center; gap: 8px; }
.section-header span { background: #29292e; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; }

.move-banner { background: #8257e622; border: 1px solid var(--primary); border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; }
.move-marker { display: flex; justify-content: center; align-items: center; margin: 8px 0; }
.move-marker-btn { background: #202024; border: 1px dashed var(--primary); color: #fff; padding: 6px 16px; border-radius: 20px; font-size: 0.85rem; cursor: pointer; transition: all 0.2s; }
.move-marker-btn:hover { background: var(--primary); transform: scale(1.05); }

.card.moving-selected { border-color: var(--primary); box-shadow: 0 0 15px rgba(130, 87, 230, 0.4); }
```

- [ ] **Step 2: Update JavaScript rendering logic in `index.html`**

Implementar no `<script>` de `index.html`:
- Estado `movingItem = null;`
- Função `toggleFavorite(id, event)`: faz `PATCH /api/manhuas/:id` com `{ isFavorite: !m.isFavorite }`, depois `loadData()`.
- Função `startMoveItem(id, event)`: define `movingItem`, chama `renderList()`.
- Função `cancelMove()`: limpa `movingItem`, chama `renderList()`.
- Função `moveItemTo(targetIndex)`: calcula nova ordem, envia `PUT /api/manhuas/reorder`, limpa `movingItem` e recarrega.
- Renderização dividida em Seções (Favoritas e Comuns) com inserção de marcadores apenas no bloco da obra selecionada.
- Handler do `keydown` para cancelar com tecla `Escape`.

- [ ] **Step 3: Test Web behavior manually or via pytest endpoint checks**

Verificar se `index.html` carrega corretamente e possui os identificadores esperados via teste em `tests/test_server.py`:
```python
def test_web_index_contains_reorder_and_favorite_elements(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "toggleFavorite" in html
    assert "startMoveItem" in html
    assert "/api/manhuas/reorder" in html
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/pytest tests/test_server.py -k test_web_index_contains_reorder_and_favorite_elements -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add index.html tests/test_server.py
git commit -m "feat(web): add favorite stars and inline manual reorder mode"
```

---

### Task 5: Flutter App - Models & ApiService in `mobile_app`

**Files:**
- Modify: `mobile_app/lib/models/manhua.dart`
- Modify: `mobile_app/lib/services/api_service.dart`
- Create: `mobile_app/test/manhua_model_test.dart`
- Create: `mobile_app/test/api_service_test.dart`

**Interfaces:**
- `Manhua`: `bool isFavorite`, `int? customOrder`, `copyWith`, `toJson`, `fromJson`.
- `ApiService`:
  - `Future<Manhua> toggleFavorite(int id, bool isFavorite)`
  - `Future<void> reorderManhuas(List<int> orderedIds)`

- [ ] **Step 1: Write failing tests for `Manhua` model**

Criar `mobile_app/test/manhua_model_test.dart`:
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/models/manhua.dart';

void main() {
  group('Manhua Model', () {
    test('fromJson and toJson with isFavorite and customOrder', () {
      final json = {
        'id': 123,
        'title': 'Solo Leveling',
        'urlTemplate': 'https://example.com/chapter/{chapter}',
        'currentChapter': 50,
        'isFavorite': true,
        'customOrder': 3,
      };

      final manhua = Manhua.fromJson(json);
      expect(manhua.isFavorite, true);
      expect(manhua.customOrder, 3);

      final encoded = manhua.toJson();
      expect(encoded['isFavorite'], true);
      expect(encoded['customOrder'], 3);
    });

    test('defaults isFavorite to false when null or absent', () {
      final json = {
        'id': 123,
        'title': 'Solo Leveling',
        'urlTemplate': 'https://example.com/chapter/{chapter}',
        'currentChapter': 50,
      };

      final manhua = Manhua.fromJson(json);
      expect(manhua.isFavorite, false);
      expect(manhua.customOrder, null);
    });
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/manhua_model_test.dart`  
Expected: FAIL (compilation error: `isFavorite` not found).

- [ ] **Step 3: Update `mobile_app/lib/models/manhua.dart`**

Adicionar campos `isFavorite` (default `false`) e `customOrder` (opcional `int?`) em `Manhua`, construtor, `fromJson`, `toJson` e `copyWith`.

- [ ] **Step 4: Update `mobile_app/lib/services/api_service.dart`**

Adicionar os métodos:
```dart
Future<Manhua> toggleFavorite(int id, bool isFavorite) async {
  final base = await _baseUrl();
  final res = await _client.patch(
    Uri.parse('$base/api/manhuas/$id'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({'isFavorite': isFavorite}),
  );
  if (res.statusCode == 200) {
    final data = jsonDecode(res.body);
    return Manhua.fromJson(data['item'] as Map<String, dynamic>);
  } else {
    throw Exception('Falha ao alternar favorito: ${res.statusCode}');
  }
}

Future<void> reorderManhuas(List<int> orderedIds) async {
  final base = await _baseUrl();
  final res = await _client.put(
    Uri.parse('$base/api/manhuas/reorder'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({'order': orderedIds}),
  );
  if (res.statusCode != 200) {
    throw Exception('Falha ao reordenar manhuas: ${res.statusCode}');
  }
}
```

- [ ] **Step 5: Run flutter test to verify it passes**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/manhua_model_test.dart`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add mobile_app/lib/models/manhua.dart mobile_app/lib/services/api_service.dart mobile_app/test/manhua_model_test.dart
git commit -m "feat(mobile): add isFavorite and customOrder to model and api service"
```

---

### Task 6: Flutter App - Controller & State Management in `mobile_app`

**Files:**
- Modify: `mobile_app/lib/controllers/manhua_controller.dart`
- Create: `mobile_app/test/manhua_controller_test.dart`

**Interfaces:**
- Produces:
  - `Future<void> toggleFavorite(int id)`: atualiza estado e sincroniza.
  - `Future<void> saveReorder(List<int> orderedIds)`: envia nova ordem e recarrega lista.

- [ ] **Step 1: Write failing tests for `ManhuaController`**

Criar `mobile_app/test/manhua_controller_test.dart` mockando `ApiService`:
Testar alternância de favoritos e reordenação.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/manhua_controller_test.dart`  
Expected: FAIL (`toggleFavorite` e `saveReorder` indefinidos no controller).

- [ ] **Step 3: Implement methods in `ManhuaController`**

Adicionar em `mobile_app/lib/controllers/manhua_controller.dart`:
```dart
Future<void> toggleFavorite(int id) async {
  final index = _manhuas.indexWhere((m) => m.id == id);
  if (index == -1) return;
  final current = _manhuas[index];
  final newStatus = !current.isFavorite;

  try {
    await _apiService.toggleFavorite(id, newStatus);
    await loadManhuas();
  } catch (e) {
    _errorMessage = 'Erro ao alternar favorito: $e';
    notifyListeners();
  }
}

Future<void> saveReorder(List<int> orderedIds) async {
  _isLoading = true;
  notifyListeners();
  try {
    await _apiService.reorderManhuas(orderedIds);
    await loadManhuas();
  } catch (e) {
    _errorMessage = 'Erro ao salvar reordenação: $e';
    notifyListeners();
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/manhua_controller_test.dart`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mobile_app/lib/controllers/manhua_controller.dart mobile_app/test/manhua_controller_test.dart
git commit -m "feat(mobile): add toggleFavorite and saveReorder in controller"
```

---

### Task 7: Flutter App - UI in `HomeScreen` with Normal & Edit Order Modes

**Files:**
- Modify: `mobile_app/lib/screens/home_screen.dart`
- Create: `mobile_app/test/home_screen_reorder_test.dart`

**Interfaces:**
- Produces:
  - Botão de estrela em cada card da `HomeScreen`.
  - Botão no `AppBar` para entrar no modo `isEditingOrder`.
  - Duas seções visuais segregadas com `ReorderableListView`:
    - `★ Obras Favoritas (X)`
    - `Demais Obras (Y)`
  - Botões `Concluir` (salva união das listas) e `Cancelar`.

- [ ] **Step 1: Write widget test for `HomeScreen` favorite star and edit mode button**

Criar `mobile_app/test/home_screen_reorder_test.dart` verificando a presença do botão de editar ordem e das estrelas nos cards.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/home_screen_reorder_test.dart`  
Expected: FAIL.

- [ ] **Step 3: Implement UI in `mobile_app/lib/screens/home_screen.dart`**

1. Adicionar estado:
   ```dart
   bool _isEditingOrder = false;
   List<Manhua> _editingFavorites = [];
   List<Manhua> _editingOthers = [];
   ```
2. Adicionar métodos `_enterEditOrderMode()`, `_cancelEditOrder()`, `_saveEditOrder()`.
3. No `AppBar`, alternar ações conforme `_isEditingOrder`:
   - Se `true`: botão Cancelar (`Icons.close`), título *"Editar Ordem"*, botão Concluir (`Icons.check`).
   - Se `false`: botão Reordenar (`Icons.sort_rounded`), Configurações, Atualizar.
4. No card normal:
   - Adicionar `IconButton` com `manhua.isFavorite ? Icons.star : Icons.star_border`, cor `#F59E0B` quando favorita, chamando `controller.toggleFavorite(manhua.id)`.
5. No corpo quando `_isEditingOrder == true`:
   - Exibir lista/coluna contendo:
     - Cabeçalho de Favoritas com contador.
     - `ReorderableListView.builder` contendo apenas `_editingFavorites`.
     - Cabeçalho de Demais Obras com contador.
     - `ReorderableListView.builder` contendo apenas `_editingOthers`.
   - Garantindo que o usuário só pode arrastar itens dentro do seu próprio bloco.

- [ ] **Step 4: Run flutter tests to verify they pass**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`  
Expected: All Flutter tests pass.

- [ ] **Step 5: Run flutter analyze to verify zero lint errors**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter analyze`  
Expected: No issues found.

- [ ] **Step 6: Commit**

```bash
git add mobile_app/lib/screens/home_screen.dart mobile_app/test/home_screen_reorder_test.dart
git commit -m "feat(mobile): add favorites and separate reorderable sections in HomeScreen"
```

---

### Task 8: End-to-End Verification, Service Restart & Summary

**Files:**
- None (verificação e reinício do serviço)

- [ ] **Step 1: Run all Python tests**

Run: `./.venv/bin/pytest tests/ -v`  
Expected: All backend tests pass.

- [ ] **Step 2: Run all Flutter tests**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`  
Expected: All mobile tests pass.

- [ ] **Step 3: Restart and verify systemd service**

Run: `systemctl --user restart manhua-manager.service`  
Run: `systemctl --user status manhua-manager.service --no-pager`  
Expected: Service is active (running).

- [ ] **Step 4: Commit any remaining updates**

```bash
git status
```
