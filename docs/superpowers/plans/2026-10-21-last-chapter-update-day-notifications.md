# Implementação: Último Episódio, Dia de Atualização, Rotina 23:50 e Notificações (Web & Mobile)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar suporte a último episódio, dia de atualização semanal e status de hiato às obras, implementar bloqueio de acesso a episódios inexistentes nas interfaces Web e Mobile (inclusive offline), criar a rotina diária das 23:50 com disparo manual para detecção de novos episódios e um sistema unificado de notificações.

**Architecture:** 
1. Backend Flask em `server.py` armazena metadados de obras em `database.json` e notificações em `notifications.json`.
2. Uma *daemon thread* interna agenda e dispara a verificação diária às 23:50 para obras elegíveis do dia, testando novos episódios e gerando notificações compartilhadas.
3. Web (`index.html`) e Mobile Flutter (`mobile_app/`) fornecem seletores de dia da semana (7 botões de seleção única), controle de hiato e último episódio, bloqueio rígido de navegação além do `lastChapter`, e central de notificações com badge e botão de verificação manual imediata.

**Tech Stack:** Python 3.14 (Flask, pytest), HTML5 / Vanilla JS, Flutter / Dart (Provider, SharedPreferences).

## Global Constraints
- Backend Python: Utilizar `./.venv/bin/python` e `./.venv/bin/pytest`.
- Mobile Flutter: Executar testes em `mobile_app` via `/home/thiagofdso/development/flutter/bin/flutter test`.
- Serviço do Sistema: Gerenciar via `systemctl --user restart manhua-manager.service`.
- URLs e Templates: Preservar `{chapter}` e compatibilidade com provedores existentes.
- Sem placeholders ou código incompleto. TDD com testes antes de cada implementação.

---

### Task 1: Backend Model Extensions e API de Notificações

**Files:**
- Modify: `server.py`
- Test: `tests/test_notifications_and_fields.py`

**Interfaces:**
- Consumes: `load_data()`, `save_data()`
- Produces: 
  - `load_notifications() -> list[dict]`
  - `save_notifications(data: list[dict]) -> None`
  - `add_notification(manhua_id: int, title: str, chapter: int) -> dict`
  - `GET /api/notifications`
  - `DELETE /api/notifications/<int:notification_id>`
  - `DELETE /api/notifications`
  - Suporte a `lastChapter`, `updateDay`, `isHiatus` em `POST /api/manhuas` e `PATCH /api/manhuas/<id>`

- [ ] **Step 1: Escrever teste de falha para novos campos e endpoints de notificação**

Criar `tests/test_notifications_and_fields.py`:
```python
import os
import json
import pytest
import server

@pytest.fixture(autouse=True)
def clean_test_env(tmp_path, monkeypatch):
    test_db = tmp_path / "test_database.json"
    test_notifs = tmp_path / "test_notifications.json"
    test_db.write_text("[]", encoding="utf-8")
    test_notifs.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(server, "DB_FILE", str(test_db))
    monkeypatch.setattr(server, "NOTIFICATIONS_FILE", str(test_notifs))
    server.app.config["TESTING"] = True

def test_add_manhua_with_last_chapter_and_update_day():
    client = server.app.test_client()
    res = client.post("/api/manhuas", json={
        "title": "Solo Leveling",
        "urlTemplate": "https://asurascans.com/comics/solo/chapter/{chapter}",
        "currentChapter": 10,
        "lastChapter": 15,
        "updateDay": 2,
        "isHiatus": False
    })
    assert res.status_code == 200
    data = res.get_json()["item"]
    assert data["lastChapter"] == 15
    assert data["updateDay"] == 2
    assert data["isHiatus"] is False

def test_patch_manhua_update_fields():
    client = server.app.test_client()
    add_res = client.post("/api/manhuas", json={
        "title": "Tower of God",
        "urlTemplate": "https://asurascans.com/comics/tog/chapter/{chapter}",
        "currentChapter": 1
    })
    item_id = add_res.get_json()["item"]["id"]

    patch_res = client.patch(f"/api/manhuas/{item_id}", json={
        "lastChapter": 500,
        "updateDay": 4,
        "isHiatus": True
    })
    assert patch_res.status_code == 200
    updated = patch_res.get_json()["item"]
    assert updated["lastChapter"] == 500
    assert updated["updateDay"] == 4
    assert updated["isHiatus"] is True

    # Test clearing lastChapter and updateDay with None
    patch_res2 = client.patch(f"/api/manhuas/{item_id}", json={
        "lastChapter": None,
        "updateDay": None,
        "isHiatus": False
    })
    assert patch_res2.status_code == 200
    updated2 = patch_res2.get_json()["item"]
    assert updated2.get("lastChapter") is None
    assert updated2.get("updateDay") is None
    assert updated2["isHiatus"] is False

def test_notifications_crud():
    client = server.app.test_client()
    # Initial list is empty
    assert client.get("/api/notifications").get_json() == []

    # Add notification directly
    notif = server.add_notification(100, "Tower of God", 501)
    assert notif["manhuaId"] == 100
    assert notif["chapter"] == 501
    assert "Novo episódio 501" in notif["message"]

    # Verify listing
    res = client.get("/api/notifications")
    items = res.get_json()
    assert len(items) == 1
    assert items[0]["id"] == notif["id"]

    # Delete specific notification
    del_res = client.delete(f"/api/notifications/{notif['id']}")
    assert del_res.status_code == 200
    assert client.get("/api/notifications").get_json() == []

    # Clear all notifications
    server.add_notification(101, "Overgeared", 244)
    server.add_notification(102, "Nano Machine", 150)
    assert len(client.get("/api/notifications").get_json()) == 2
    clear_res = client.delete("/api/notifications")
    assert clear_res.status_code == 200
    assert client.get("/api/notifications").get_json() == []
```

- [ ] **Step 2: Executar teste para verificar que falha**

Run: `./.venv/bin/pytest tests/test_notifications_and_fields.py -v`
Expected: FAIL com AttributeError/404 em `/api/notifications` e `NOTIFICATIONS_FILE` não definido.

- [ ] **Step 3: Implementar persistência de notificações e novos campos em `server.py`**

Em `server.py`:
1. Definir:
```python
NOTIFICATIONS_FILE = os.path.join(BASE_DIR, "notifications.json")

def load_notifications():
    if not os.path.exists(NOTIFICATIONS_FILE):
        return []
    try:
        with open(NOTIFICATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_notifications(data):
    with open(NOTIFICATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_notification(manhua_id: int, title: str, chapter: int) -> dict:
    notifs = load_notifications()
    item = {
        "id": int(time.time() * 1000),
        "manhuaId": manhua_id,
        "title": title,
        "chapter": chapter,
        "message": f"Novo episódio {chapter} de {title} disponível!",
        "createdAt": int(time.time())
    }
    notifs.insert(0, item)
    save_notifications(notifs)
    return item
```
2. Adicionar rotas de notificação:
```python
@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    return jsonify(load_notifications())

@app.route("/api/notifications/<int:notification_id>", methods=["DELETE"])
def delete_notification(notification_id):
    notifs = [n for n in load_notifications() if n["id"] != notification_id]
    save_notifications(notifs)
    return jsonify({"status": "ok"})

@app.route("/api/notifications", methods=["DELETE"])
def clear_all_notifications():
    save_notifications([])
    return jsonify({"status": "ok"})
```
3. Em `POST /api/manhuas`:
Aceitar `lastChapter`, `updateDay` e `isHiatus`:
```python
    last_chapter = int(payload["lastChapter"]) if payload.get("lastChapter") is not None and str(payload.get("lastChapter")).strip() != "" else None
    update_day = int(payload["updateDay"]) if payload.get("updateDay") is not None and str(payload.get("updateDay")).strip() != "" else None
    is_hiatus = bool(payload.get("isHiatus", False))
```
E atribuir ao `new_item`:
```python
    if last_chapter is not None:
        new_item["lastChapter"] = last_chapter
    if update_day is not None:
        new_item["updateDay"] = update_day
    new_item["isHiatus"] = is_hiatus
```
4. Em `PATCH /api/manhuas/<int:item_id>`:
```python
    if "lastChapter" in payload:
        raw_lc = payload["lastChapter"]
        m["lastChapter"] = int(raw_lc) if raw_lc is not None and str(raw_lc).strip() != "" else None
    if "updateDay" in payload:
        raw_ud = payload["updateDay"]
        m["updateDay"] = int(raw_ud) if raw_ud is not None and str(raw_ud).strip() != "" else None
    if "isHiatus" in payload:
        m["isHiatus"] = bool(payload["isHiatus"])
```

- [ ] **Step 4: Executar testes para verificar aprovação**

Run: `./.venv/bin/pytest tests/test_notifications_and_fields.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Executar toda a suíte de testes do backend**

Run: `./.venv/bin/pytest tests/`
Expected: 59 passed

- [ ] **Step 6: Commit**

```bash
git add server.py tests/test_notifications_and_fields.py
git commit -m "feat(backend): add lastChapter, updateDay, isHiatus fields and notifications API"
```

---

### Task 2: Rotina de Verificação das 23:50 e Disparo Manual

**Files:**
- Modify: `server.py`
- Test: `tests/test_routine_check.py`

**Interfaces:**
- Produces:
  - `run_daily_update_check(check_all: bool = False, target_weekday: int = None) -> dict`
  - `POST /api/routine/run-check`
  - `start_routine_scheduler()` iniciando *daemon thread* para as 23:50

- [ ] **Step 1: Escrever teste de falha para a lógica de verificação e rotina**

Criar `tests/test_routine_check.py`:
```python
import pytest
from unittest.mock import patch
import server

@pytest.fixture(autouse=True)
def clean_env(tmp_path, monkeypatch):
    test_db = tmp_path / "test_database.json"
    test_notifs = tmp_path / "test_notifications.json"
    test_db.write_text("[]", encoding="utf-8")
    test_notifs.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(server, "DB_FILE", str(test_db))
    monkeypatch.setattr(server, "NOTIFICATIONS_FILE", str(test_notifs))
    server.app.config["TESTING"] = True

def test_run_daily_update_check_detects_new_chapter():
    # Setup database with 3 obras:
    # Obra 1: Wednesday (updateDay=2), lastChapter=10, isHiatus=False -> Deve atualizar
    # Obra 2: Wednesday (updateDay=2), lastChapter=5, isHiatus=True -> Deve ignorar (hiato)
    # Obra 3: Friday (updateDay=4), lastChapter=20, isHiatus=False -> Deve ignorar (outro dia)
    server.save_data([
        {
            "id": 1,
            "title": "Manga 1",
            "urlTemplate": "https://example.com/ch/{chapter}",
            "currentChapter": 10,
            "lastChapter": 10,
            "updateDay": 2,
            "isHiatus": False
        },
        {
            "id": 2,
            "title": "Manga 2",
            "urlTemplate": "https://example.com/manga2/{chapter}",
            "currentChapter": 5,
            "lastChapter": 5,
            "updateDay": 2,
            "isHiatus": True
        },
        {
            "id": 3,
            "title": "Manga 3",
            "urlTemplate": "https://example.com/manga3/{chapter}",
            "currentChapter": 20,
            "lastChapter": 20,
            "updateDay": 4,
            "isHiatus": False
        }
    ])

    def mock_extract(url):
        # Only return images for Manga 1 chapter 11
        if "example.com/ch/11" in url:
            return ["https://example.com/img1.jpg", "https://example.com/img2.jpg"]
        return []

    with patch.object(server, "extract_images_from_url", side_effect=mock_extract):
        result = server.run_daily_update_check(check_all=False, target_weekday=2)

    assert result["checkedCount"] == 1
    assert result["newChaptersFound"] == 1
    assert len(result["results"]) == 1
    assert result["results"][0]["id"] == 1
    assert result["results"][0]["newChapter"] == 11

    # Verify database updated
    db = server.load_data()
    m1 = next(m for m in db if m["id"] == 1)
    assert m1["lastChapter"] == 11

    # Verify notification created
    notifs = server.load_notifications()
    assert len(notifs) == 1
    assert notifs[0]["manhuaId"] == 1
    assert notifs[0]["chapter"] == 11

def test_api_run_check_endpoint():
    client = server.app.test_client()
    server.save_data([
        {
            "id": 1,
            "title": "Manga Check",
            "urlTemplate": "https://example.com/{chapter}",
            "currentChapter": 1,
            "lastChapter": 1,
            "updateDay": 3,
            "isHiatus": False
        }
    ])

    with patch.object(server, "extract_images_from_url", return_value=["https://img.jpg"]):
        res = client.post("/api/routine/run-check", json={"checkAll": True})
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "ok"
        assert data["checkedCount"] == 1
        assert data["newChaptersFound"] == 1
```

- [ ] **Step 2: Executar teste para verificar que falha**

Run: `./.venv/bin/pytest tests/test_routine_check.py -v`
Expected: FAIL com AttributeError `run_daily_update_check` em `server`.

- [ ] **Step 3: Implementar rotina e thread agendada em `server.py`**

Em `server.py`:
1. Implementar `run_daily_update_check`:
```python
import threading
from datetime import datetime

def run_daily_update_check(check_all: bool = False, target_weekday: int = None) -> dict:
    if target_weekday is None:
        target_weekday = datetime.now().weekday()

    db_data = load_data()
    eligible = []
    for m in db_data:
        if m.get("isHiatus", False):
            continue
        if m.get("lastChapter") is None:
            continue
        if check_all or m.get("updateDay") == target_weekday:
            eligible.append(m)

    results = []
    new_found = 0

    for m in eligible:
        current_last = int(m["lastChapter"])
        next_candidate = current_last + 1
        url_template = m.get("urlTemplate", "")
        if not url_template:
            continue
        target_url = url_template.replace("{chapter}", str(next_candidate))
        try:
            images = extract_images_from_url(target_url)
            if images and len(images) > 0:
                m["lastChapter"] = next_candidate
                m["updatedAt"] = int(time.time())
                add_notification(m["id"], m.get("title", ""), next_candidate)
                new_found += 1
                results.append({
                    "id": m["id"],
                    "title": m.get("title", ""),
                    "newChapter": next_candidate,
                    "status": "updated"
                })
        except Exception as e:
            results.append({
                "id": m["id"],
                "title": m.get("title", ""),
                "attemptedChapter": next_candidate,
                "status": "error",
                "error": str(e)
            })

    if new_found > 0:
        save_data(db_data)

    return {
        "status": "ok",
        "checkedCount": len(eligible),
        "newChaptersFound": new_found,
        "results": results
    }
```
2. Endpoint `POST /api/routine/run-check`:
```python
@app.route("/api/routine/run-check", methods=["POST"])
def trigger_update_check():
    payload = request.get_json(silent=True) or {}
    check_all = bool(payload.get("checkAll", False))
    result = run_daily_update_check(check_all=check_all)
    return jsonify(result)
```
3. Thread agendada para 23:50:
```python
_last_run_date = None

def _routine_scheduler_loop():
    global _last_run_date
    while True:
        try:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            if now.hour == 23 and now.minute == 50 and _last_run_date != today_str:
                _last_run_date = today_str
                run_daily_update_check(check_all=False, target_weekday=now.weekday())
        except Exception:
            pass
        time.sleep(30)

def start_routine_scheduler():
    t = threading.Thread(target=_routine_scheduler_loop, daemon=True)
    t.start()
```
E ao final de `server.py`, antes de `app.run` ou no carregamento do módulo, chamar `start_routine_scheduler()`.

- [ ] **Step 4: Executar testes de rotina e suíte backend**

Run: `./.venv/bin/pytest tests/test_routine_check.py -v`
Expected: PASS (2 passed)

Run: `./.venv/bin/pytest tests/`
Expected: 61 passed

- [ ] **Step 5: Commit**

```bash
git add server.py tests/test_routine_check.py
git commit -m "feat(backend): add daily 23:50 routine check and manual trigger endpoint"
```

---

### Task 3: Interface Web (`index.html`)

**Files:**
- Modify: `index.html`
- Test: `tests/test_web_interface.py` (ou teste com Playwright / BeautifulSoup / regex em pytest)

**Interfaces:**
- Produces:
  - Botões do dia da semana (Seg a Dom) no modal de adicionar e editar
  - Campo numérico de Último Episódio e Checkbox de Hiato
  - Badges visuais de dia da semana, hiato e `Capítulo X / Y`
  - Bloqueio de navegação:
    - Botão `+1` / Próximo desativado se `currentChapter >= lastChapter`
    - Input manual bloqueando números maiores que `lastChapter`
    - Leitor web: seta direita e botão Próximo bloqueados se `currentChapter >= lastChapter`
  - Central de Notificações:
    - Ícone de sino com badge na barra de navegação
    - Modal de notificações com lista, botão de dispensar individual, botão limpar todas e botão "Verificar Atualizações Agora"

- [ ] **Step 1: Escrever teste de asserção para os elementos da Web**

Criar `tests/test_web_interface.py`:
```python
import pytest

def test_web_index_contains_last_chapter_and_notification_elements():
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Campos nos formulários
    assert 'id="updateDayGroup"' in html or 'data-day' in html
    assert 'id="lastChapter"' in html
    assert 'id="isHiatus"' in html
    assert 'id="editLastChapter"' in html
    assert 'id="editIsHiatus"' in html

    # Elementos de notificação
    assert 'id="btnNotificationBell"' in html or 'id="notifBell"' in html
    assert 'id="notificationBadge"' in html
    assert 'id="notificationModal"' in html
    assert 'id="btnTriggerManualCheck"' in html
```

- [ ] **Step 2: Executar teste para verificar que falha**

Run: `./.venv/bin/pytest tests/test_web_interface.py -v`
Expected: FAIL

- [ ] **Step 3: Implementar novos campos e notificações no `index.html`**

No `index.html`:
1. **Cabeçalho:** Adicionar ícone de sino de notificação ao lado do título ou botões de ação:
```html
<button id="notifBell" class="action-btn notif-bell" onclick="openNotificationModal()" title="Notificações">
  🔔<span id="notificationBadge" class="notif-badge" style="display:none;">0</span>
</button>
```
2. **Formulário de Cadastro e Modal de Edição:**
Adicionar seletor de dias da semana (botões `Seg`, `Ter`, `Qua`, `Qui`, `Sex`, `Sáb`, `Dom`), input `lastChapter` e checkbox `isHiatus`:
```html
<label>Dia de Atualização (Semanal)</label>
<div class="weekday-selector" id="addWeekdaySelector">
  <button type="button" class="weekday-btn" data-day="0" onclick="selectWeekday('add', 0)">Seg</button>
  <button type="button" class="weekday-btn" data-day="1" onclick="selectWeekday('add', 1)">Ter</button>
  <button type="button" class="weekday-btn" data-day="2" onclick="selectWeekday('add', 2)">Qua</button>
  <button type="button" class="weekday-btn" data-day="3" onclick="selectWeekday('add', 3)">Qui</button>
  <button type="button" class="weekday-btn" data-day="4" onclick="selectWeekday('add', 4)">Sex</button>
  <button type="button" class="weekday-btn" data-day="5" onclick="selectWeekday('add', 5)">Sáb</button>
  <button type="button" class="weekday-btn" data-day="6" onclick="selectWeekday('add', 6)">Dom</button>
</div>
<label>Último Episódio Lançado (opcional)</label>
<input type="number" id="lastChapter" placeholder="Ex: 245 (deixe vazio se ilimitado)" />
<div class="checkbox-row" style="margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
  <input type="checkbox" id="isHiatus" style="width: auto; margin-bottom: 0;" />
  <label for="isHiatus" style="margin-bottom: 0; cursor: pointer;">Obra em Hiato (lançamento suspenso)</label>
</div>
```
Replicar campos correspondentes em `#editModal` (`editLastChapter`, `editIsHiatus`, `editWeekdaySelector`).
3. **Modal de Notificações (`notificationModal`):**
```html
<div id="notificationModal" class="modal">
  <div class="modal-content">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
      <h3 style="font-size:1.15rem;">Notificações de Novos Capítulos</h3>
      <button class="action-btn" onclick="closeNotificationModal()">✕</button>
    </div>
    <div style="display:flex; gap:8px; margin-bottom:12px;">
      <button id="btnTriggerManualCheck" class="btn btn-secondary btn-sm" onclick="triggerManualCheck()">
        🔄 Verificar Atualizações Agora
      </button>
      <button id="btnClearNotifs" class="btn btn-secondary btn-sm" onclick="clearAllNotifications()">
        🗑️ Limpar todas
      </button>
    </div>
    <div id="notifStatusMsg" style="display:none; font-size:0.85rem; color:var(--primary); margin-bottom:8px;"></div>
    <div id="notificationList" style="max-height:300px; overflow-y:auto;"></div>
  </div>
</div>
```
4. **JavaScript:**
   - Adicionar funções de seleção de dia da semana (`selectedAddWeekday`, `selectedEditWeekday`).
   - Carregar e exibir notificações via `loadNotifications()`.
   - Implementar `triggerManualCheck()` com feedback.
   - Atualizar `renderList()` para exibir badges de dia da semana (ex: `Sex`), badge `⏸️ Hiato` e progresso `Capítulo X / Y` quando `lastChapter` estiver presente.
   - Restrições de navegação:
     - Em `changeSelectedChapter(delta)`: se `delta > 0` e `selectedManhua.lastChapter != null && selectedManhua.currentChapter >= selectedManhua.lastChapter`, bloquear e alertar.
     - Em `changeReaderChapter(delta)`: se `delta > 0` e `readerManhua.lastChapter != null && readerManhua.currentChapter >= readerManhua.lastChapter`, bloquear e alertar.
     - Desabilitar visualmente o botão `Próximo ▶` quando no último episódio.

- [ ] **Step 4: Executar testes de interface web**

Run: `./.venv/bin/pytest tests/test_web_interface.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add index.html tests/test_web_interface.py
git commit -m "feat(web): add weekday buttons, hiatus, lastChapter navigation limit and notifications modal"
```

---

### Task 4: Mobile App - Modelo, ApiService e Controller

**Files:**
- Modify: `mobile_app/lib/models/manhua.dart`
- Modify: `mobile_app/lib/services/api_service.dart`
- Modify: `mobile_app/lib/controllers/manhua_controller.dart`
- Test: `mobile_app/test/models/manhua_test.dart`
- Test: `mobile_app/test/services/api_service_notifications_test.dart`

**Interfaces:**
- Produces:
  - `Manhua` com `lastChapter`, `updateDay`, `isHiatus`
  - `ApiService`: `fetchNotifications()`, `deleteNotification(int id)`, `clearNotifications()`, `triggerManualCheck({bool checkAll = false})`
  - `ManhuaController`: `notifications`, `loadNotifications()`, `dismissNotification(int id)`, `clearAllNotifications()`, `triggerManualCheck()`

- [ ] **Step 1: Escrever teste de falha para o modelo Manhua com os novos campos**

Criar `mobile_app/test/models/manhua_test.dart`:
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/models/manhua.dart';

void main() {
  test('Manhua serializa e deserializa lastChapter, updateDay e isHiatus', () {
    final manhua = Manhua(
      id: 1,
      title: 'Solo Leveling',
      urlTemplate: 'https://asurascans.com/solo/{chapter}',
      currentChapter: 10,
      lastChapter: 15,
      updateDay: 4,
      isHiatus: true,
    );

    final json = manhua.toJson();
    expect(json['lastChapter'], 15);
    expect(json['updateDay'], 4);
    expect(json['isHiatus'], true);

    final parsed = Manhua.fromJson(json);
    expect(parsed.lastChapter, 15);
    expect(parsed.updateDay, 4);
    expect(parsed.isHiatus, true);
  });

  test('Manhua default values para campos novos', () {
    final parsed = Manhua.fromJson({
      'id': 2,
      'title': 'Test',
      'urlTemplate': 'https://test.com/{chapter}',
      'currentChapter': 1,
    });
    expect(parsed.lastChapter, isNull);
    expect(parsed.updateDay, isNull);
    expect(parsed.isHiatus, isFalse);
  });
}
```

- [ ] **Step 2: Executar teste do modelo para verificar falha**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/models/manhua_test.dart`
Expected: FAIL com erros de compilação (parâmetros desconhecidos).

- [ ] **Step 3: Atualizar `Manhua`, `ApiService` e `ManhuaController`**

1. Em `mobile_app/lib/models/manhua.dart`:
Adicionar campos `final int? lastChapter;`, `final int? updateDay;`, `final bool isHiatus;`.
Atualizar `fromJson`, `toJson` e `copyWith`.
2. Em `mobile_app/lib/services/api_service.dart`:
Adicionar métodos de notificações:
```dart
Future<List<Map<String, dynamic>>> fetchNotifications() async { ... }
Future<void> deleteNotification(int id) async { ... }
Future<void> clearNotifications() async { ... }
Future<Map<String, dynamic>> triggerManualCheck({bool checkAll = false}) async { ... }
```
E atualizar `addManhua` e `editManhua` para aceitar `int? lastChapter`, `int? updateDay`, `bool isHiatus`.
3. Em `mobile_app/lib/controllers/manhua_controller.dart`:
Adicionar gerenciamento de notificações:
```dart
List<Map<String, dynamic>> _notifications = [];
List<Map<String, dynamic>> get notifications => _notifications;

Future<void> loadNotifications() async { ... }
Future<void> dismissNotification(int id) async { ... }
Future<void> clearAllNotifications() async { ... }
Future<Map<String, dynamic>> triggerManualCheck() async { ... }
```

- [ ] **Step 4: Executar testes do modelo e flutter test**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mobile_app/lib/models/manhua.dart mobile_app/lib/services/api_service.dart mobile_app/lib/controllers/manhua_controller.dart mobile_app/test/models/manhua_test.dart
git commit -m "feat(mobile): add lastChapter, updateDay, isHiatus to model and notification api methods"
```

---

### Task 5: Mobile App - Diálogos, HomeScreen e Notificações

**Files:**
- Modify: `mobile_app/lib/screens/widgets/add_manhua_dialog.dart`
- Modify: `mobile_app/lib/screens/widgets/edit_manhua_dialog.dart`
- Modify: `mobile_app/lib/screens/home_screen.dart`
- Test: `mobile_app/test/widgets/manhua_dialogs_test.dart`
- Test: `mobile_app/test/home_screen_notifications_test.dart`

**Interfaces:**
- Produces:
  - Diálogos com grupo de 7 botões para o dia da semana, input de último episódio e switch/checkbox de hiato
  - Card de obra na `HomeScreen` exibindo dia de atualização, badge de hiato e progresso de episódios
  - Botão `+1` na `HomeScreen` desabilitado quando `manhua.lastChapter != null && manhua.currentChapter >= manhua.lastChapter`
  - Botão de sino de notificação na `AppBar` com `Badge` de contagem
  - Bottom sheet de notificações com opções de abrir leitor, dispensar, limpar todas e verificar agora

- [ ] **Step 1: Escrever teste de widget para desativação do botão +1 e campos dos diálogos**

Criar `mobile_app/test/home_screen_notifications_test.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/controllers/manhua_controller.dart';
import 'package:mobile_app/models/manhua.dart';
import 'package:mobile_app/screens/home_screen.dart';

class MockManhuaController extends ChangeNotifier implements ManhuaController {
  @override
  List<Manhua> manhuas = [
    Manhua(
      id: 1,
      title: 'Overgeared',
      urlTemplate: 'https://test.com/{chapter}',
      currentChapter: 245,
      lastChapter: 245, // No limite máximo
      updateDay: 4,
      isHiatus: false,
    ),
    Manhua(
      id: 2,
      title: 'Solo Leveling',
      urlTemplate: 'https://test.com/{chapter}',
      currentChapter: 10,
      lastChapter: 20, // Pode avançar
      updateDay: 1,
      isHiatus: false,
    ),
  ];

  @override
  bool isLoading = false;
  @override
  bool isOfflineMode = false;
  @override
  String? errorMessage;
  @override
  String baseUrl = 'http://test';
  @override
  List<Map<String, dynamic>> notifications = [
    {'id': 10, 'manhuaId': 2, 'title': 'Solo Leveling', 'chapter': 11}
  ];

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  testWidgets('HomeScreen desativa botão +1 quando currentChapter >= lastChapter', (tester) async {
    final mock = MockManhuaController();

    await tester.pumpWidget(
      MaterialApp(
        home: ChangeNotifierProvider<ManhuaController>.value(
          value: mock,
          child: const HomeScreen(),
        ),
      ),
    );

    // Botão +1 da obra 1 (Overgeared, 245/245) deve estar desabilitado
    final addButtons = find.byIcon(Icons.add_circle_outline);
    expect(addButtons, findsNWidgets(2));

    final IconButton overgearedAdd = tester.widget(addButtons.first);
    expect(overgearedAdd.onPressed, isNull);

    // Botão +1 da obra 2 (Solo Leveling, 10/20) deve estar ativo
    final IconButton soloAdd = tester.widget(addButtons.at(1));
    expect(soloAdd.onPressed, isNotNull);

    // Verifica presença do ícone de notificações
    expect(find.byIcon(Icons.notifications_outlined), findsOneWidget);
  });
}
```

- [ ] **Step 2: Executar teste para verificar que falha**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/home_screen_notifications_test.dart`
Expected: FAIL

- [ ] **Step 3: Implementar diálogos e HomeScreen com bloqueio e notificações**

1. Em `AddManhuaDialog` e `EditManhuaDialog`:
   - Adicionar botões compactos para os dias da semana (`Seg`, `Ter`, `Qua`, `Qui`, `Sex`, `Sáb`, `Dom`).
   - Adicionar `TextFormField` para `Último Episódio`.
   - Adicionar `SwitchListTile` para `Obra em Hiato`.
2. Em `HomeScreen`:
   - No card da obra:
     - Exibir badges de dia da semana (ex: `Sex`), badge `Hiato` quando `manhua.isHiatus`, e texto `Capítulo ${manhua.currentChapter}${manhua.lastChapter != null ? ' / ${manhua.lastChapter}' : ''}`.
     - No `IconButton(icon: Icon(Icons.add_circle_outline))` de avançar:
       `onPressed: (manhua.lastChapter != null && manhua.currentChapter >= manhua.lastChapter!) ? null : () => controller.changeChapterDelta(manhua.id, 1)`
   - Na `AppBar`:
     - Adicionar `IconButton` com `Badge.count(count: controller.notifications.length, child: const Icon(Icons.notifications_outlined))` que abre `_showNotificationsSheet(context)`.
   - Implementar bottom sheet com lista de notificações, botão de dispensar, botão de limpar todas e botão `"Verificar Atualizações Agora"`.

- [ ] **Step 4: Executar testes de widgets mobile**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/home_screen_notifications_test.dart`
Expected: PASS

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`
Expected: Todos os testes mobile passando.

- [ ] **Step 5: Commit**

```bash
git add mobile_app/lib/screens/ mobile_app/test/home_screen_notifications_test.dart
git commit -m "feat(mobile): add weekday chips, hiatus, chapter limit on home and notification sheet"
```

---

### Task 6: Mobile ReaderScreen Bloqueio de Navegação e Verificação Completa

**Files:**
- Modify: `mobile_app/lib/screens/reader_screen.dart`
- Test: `mobile_app/test/reader_screen_limit_test.dart`

**Interfaces:**
- Produces:
  - `ReaderScreen` bloqueando botão "Próximo" e swipe horizontal para frente quando `currentChapter >= lastChapter`
  - Exibição de `SnackBar` informativa ao tentar avançar além do limite

- [ ] **Step 1: Escrever teste de widget para bloqueio no ReaderScreen**

Criar `mobile_app/test/reader_screen_limit_test.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/controllers/manhua_controller.dart';
import 'package:mobile_app/models/manhua.dart';
import 'package:mobile_app/screens/reader_screen.dart';

class MockManhuaController extends ChangeNotifier implements ManhuaController {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  testWidgets('ReaderScreen desativa botão Próximo quando no último episódio', (tester) async {
    final manhua = Manhua(
      id: 1,
      title: 'Solo Leveling',
      urlTemplate: 'https://test.com/{chapter}',
      currentChapter: 15,
      lastChapter: 15,
    );

    await tester.pumpWidget(
      MaterialApp(
        home: ChangeNotifierProvider<ManhuaController>.value(
          value: MockManhuaController(),
          child: ReaderScreen(manhua: manhua),
        ),
      ),
    );

    // Botão Anterior ativo (capítulo 15 > 1)
    final prevBtn = tester.widget<ElevatedButton>(find.widgetWithText(ElevatedButton, 'Anterior'));
    expect(prevBtn.onPressed, isNotNull);

    // Botão Próximo deve estar desabilitado pois 15 == lastChapter
    final nextBtn = tester.widget<ElevatedButton>(find.widgetWithText(ElevatedButton, 'Próximo'));
    expect(nextBtn.onPressed, isNull);
  });
}
```

- [ ] **Step 2: Executar teste para verificar que falha**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test test/reader_screen_limit_test.dart`
Expected: FAIL (nextBtn.onPressed is not null)

- [ ] **Step 3: Implementar bloqueio de navegação no `ReaderScreen`**

Em `mobile_app/lib/screens/reader_screen.dart`:
1. No `onHorizontalDragEnd`:
```dart
if (velocity < -300) {
  // Próximo capítulo
  if (_currentManhua.lastChapter != null && _currentChapter >= _currentManhua.lastChapter!) {
    ScaffoldMessenger.of(context).hideCurrentSnackBar();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Você já está no último episódio disponível (${_currentManhua.lastChapter}).'),
        duration: const Duration(seconds: 2),
      ),
    );
  } else {
    _changeChapter(1);
  }
}
```
2. No botão `Próximo` da barra inferior:
```dart
onPressed: (_currentManhua.lastChapter != null && _currentChapter >= _currentManhua.lastChapter!)
    ? null
    : () => _changeChapter(1),
```

- [ ] **Step 4: Executar testes do ReaderScreen e suíte completa do Flutter**

Run: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`
Expected: All tests passed!

- [ ] **Step 5: Executar suíte completa do backend e reiniciar serviço do sistema**

Run: `./.venv/bin/pytest tests/`
Expected: All tests passed!

Run: `systemctl --user restart manhua-manager.service`
Run: `systemctl --user status manhua-manager.service --no-pager`
Expected: `active (running)`

- [ ] **Step 6: Commit**

```bash
git add mobile_app/lib/screens/reader_screen.dart mobile_app/test/reader_screen_limit_test.dart
git commit -m "feat(mobile): enforce lastChapter limit in ReaderScreen navigation"
```
