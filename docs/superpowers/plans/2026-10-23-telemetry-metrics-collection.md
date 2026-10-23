# Telemetria Local e Coleta de Métricas - Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar coleta de telemetria local e métricas de desempenho assíncronas no backend Python do `manhua-manager`, gerando logs estruturados em JSONL, armazenamento histórico em SQLite e amostragem de recursos de hardware sem adicionar dependências externas ou latência perceptível ao servidor.

**Architecture:** Módulo central de telemetria (`telemetry.py`) com context manager para spans hierárquicos e precisão temporal com `time.perf_counter_ns()`. Os eventos finalizados são enfileirados em um buffer limitado (`queue.Queue`) e gravados em lote em JSONL por um worker em background com descarte gracioso em caso de saturação. Um módulo de banco (`telemetry_db.py`) gerencia tabelas históricas no SQLite para análise e percentis, enquanto `telemetry_sampler.py` usa `psutil` para monitorar consumo de processos (Python e descendentes Node/Brave). Hooks globais no Flask e instrumentações pontuais em I/O, proxy de imagens e provedores alimentam a telemetria.

**Tech Stack:** Python 3.14, Flask, SQLite3, psutil, JSONL, pytest.

## Global Constraints

- **Ambiente Python:** Utilize sempre `./.venv/bin/python` e `./.venv/bin/pytest tests/`. Nunca use o Python global do sistema.
- **Templates de Capítulos:** Manter preservado o placeholder `{chapter}` em URLs e rotas manipuladas.
- **Isolamento de Falhas:** Erros ou saturação na telemetria NUNCA devem propagar exceções ou falhar as requisições HTTP do usuário.
- **Não-Regressão:** Todos os 90 testes existentes em `tests/` devem continuar passando ao final de cada alteração.
- **Cardinalidade Baixa:** Rotas em `server.py` devem ser parametrizadas via `request.url_rule.rule` em vez de URLs brutas com IDs dinâmicos.

---

### Task 1: Estrutura de Diretórios, Gitignore e Dependências de Observabilidade

**Files:**
- Create: `requirements-observability.txt`
- Modify: `.gitignore`
- Create: `telemetry/.gitkeep`

**Interfaces:**
- Consumes: N/A
- Produces: Diretório `telemetry/` pronto para gravação com exclusão de dados gerados no `.gitignore`, e `psutil` instalado no `.venv`.

- [ ] **Step 1: Atualizar o .gitignore para ignorar artefatos de telemetria**

Adicionar regras em [`.gitignore`](file:///home/thiagofdso/Projetos/manhua-manager/.gitignore):
```gitignore
# Telemetria e Benchmarks
telemetry/events/
telemetry/runs/
telemetry/backups/
telemetry/*.sqlite3
telemetry/*.sqlite3-wal
telemetry/*.sqlite3-shm
```

- [ ] **Step 2: Criar requirements-observability.txt e diretórios base**

Criar arquivo `requirements-observability.txt`:
```text
psutil>=5.9.0
```

Executar comandos para criação de diretórios e instalação:
```bash
mkdir -p telemetry/events telemetry/runs telemetry/backups
touch telemetry/.gitkeep
./.venv/bin/python -m pip install -r requirements-observability.txt
```

- [ ] **Step 3: Verificar instalação do psutil e integridade dos testes existentes**

Executar:
```bash
./.venv/bin/python -c "import psutil; print(psutil.__version__)"
./.venv/bin/pytest tests/
```
Expected: Versão do `psutil` impressa e `90 passed in ...`.

- [ ] **Step 4: Commit das configurações iniciais**

```bash
git add .gitignore requirements-observability.txt telemetry/.gitkeep
git commit -m "chore: configure telemetry directories, gitignore and dependencies"
```

---

### Task 2: Core de Telemetria (`telemetry.py`) com Spans e Contexto

**Files:**
- Create: `telemetry.py`
- Test: `tests/test_telemetry.py`

**Interfaces:**
- Consumes: Biblioteca padrão (`time`, `contextvars`, `uuid`, `datetime`)
- Produces:
  - `telemetry.span(operation: str, route: str | None = None, domain: str | None = None, **kwargs)`
  - `telemetry.set_request_id(req_id: str | None) -> str`
  - `telemetry.get_current_context() -> dict`
  - `telemetry.set_benchmark_run_id(run_id: str | None)`

- [ ] **Step 1: Escrever teste unitário para spans, hierarquia e exceções**

Criar `tests/test_telemetry.py`:
```python
import pytest
import time
import telemetry

def test_telemetry_span_basic_lifecycle():
    telemetry.set_request_id("req-test-123")
    
    with telemetry.span("test.op", route="/api/test", domain="example.com") as s:
        time.sleep(0.01)
        s.set_attribute("items_count", 5)
        
    event = s.to_dict()
    assert event["schema_version"] == 1
    assert event["operation"] == "test.op"
    assert event["route"] == "/api/test"
    assert event["domain"] == "example.com"
    assert event["request_id"] == "req-test-123"
    assert event["span_id"] is not None
    assert event["parent_span_id"] is None
    assert event["duration_ms"] >= 10.0
    assert event["outcome"] == "success"
    assert event["items_count"] == 5

def test_telemetry_nested_spans():
    with telemetry.span("parent.op") as parent:
        with telemetry.span("child.op") as child:
            pass
            
    assert child.parent_span_id == parent.span_id

def test_telemetry_span_exception_capture():
    with pytest.raises(ValueError, match="simulated error"):
        with telemetry.span("error.op") as s:
            raise ValueError("simulated error")
            
    event = s.to_dict()
    assert event["outcome"] == "error"
    assert event["error_type"] == "ValueError"
```

- [ ] **Step 2: Executar teste e validar falha**

Run:
```bash
./.venv/bin/pytest tests/test_telemetry.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'telemetry'`.

- [ ] **Step 3: Implementar o núcleo de spans em `telemetry.py`**

Criar `telemetry.py`:
```python
import os
import time
import uuid
import subprocess
from datetime import datetime, timezone
from contextvars import ContextVar
from typing import Any, Dict, Optional

_current_request_id: ContextVar[Optional[str]] = ContextVar("current_request_id", default=None)
_current_span_id: ContextVar[Optional[str]] = ContextVar("current_span_id", default=None)
_current_benchmark_run_id: ContextVar[Optional[str]] = ContextVar("current_benchmark_run_id", default=None)

_cached_git_revision: Optional[str] = None

def get_git_revision() -> str:
    global _cached_git_revision
    if _cached_git_revision is None:
        try:
            out = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
            _cached_git_revision = out or "unknown"
        except Exception:
            _cached_git_revision = "unknown"
    return _cached_git_revision

def set_request_id(req_id: Optional[str] = None) -> str:
    rid = req_id or f"req-{uuid.uuid4().hex[:12]}"
    _current_request_id.set(rid)
    return rid

def set_benchmark_run_id(run_id: Optional[str]):
    _current_benchmark_run_id.set(run_id)

def get_current_context() -> Dict[str, Optional[str]]:
    return {
        "request_id": _current_request_id.get(),
        "span_id": _current_span_id.get(),
        "benchmark_run_id": _current_benchmark_run_id.get()
    }

class Span:
    def __init__(self, operation: str, route: Optional[str] = None, domain: Optional[str] = None, **initial_attrs: Any):
        self.schema_version = 1
        self.service = "manhua-manager-backend"
        self.implementation = "python"
        self.revision = get_git_revision()
        self.operation = operation
        self.route = route
        self.domain = domain
        self.request_id = _current_request_id.get()
        self.parent_span_id = _current_span_id.get()
        self.span_id = f"span-{uuid.uuid4().hex[:12]}"
        self.benchmark_run_id = _current_benchmark_run_id.get()
        
        self.start_ns = 0
        self.duration_ms = 0.0
        self.timestamp = ""
        self.outcome = "success"
        self.cache_state = "not_applicable"
        self.http_status: Optional[int] = None
        self.upstream_status: Optional[int] = None
        self.error_type: Optional[str] = None
        self.attributes: Dict[str, Any] = dict(initial_attrs)
        
        self._token = None

    def set_attribute(self, key: str, value: Any):
        self.attributes[key] = value

    def __enter__(self):
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.start_ns = time.perf_counter_ns()
        self._token = _current_span_id.set(self.span_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ns = time.perf_counter_ns() - self.start_ns
        self.duration_ms = round(duration_ns / 1_000_000, 3)
        if exc_type is not None:
            self.outcome = "error"
            self.error_type = exc_type.__name__
        if self._token:
            _current_span_id.reset(self._token)
        _emit_span(self)
        return False

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "schema_version": self.schema_version,
            "timestamp": self.timestamp,
            "service": self.service,
            "implementation": self.implementation,
            "revision": self.revision,
            "request_id": self.request_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation": self.operation,
            "route": self.route,
            "domain": self.domain,
            "duration_ms": self.duration_ms,
            "outcome": self.outcome,
            "cache_state": self.cache_state,
            "http_status": self.http_status,
            "upstream_status": self.upstream_status,
            "error_type": self.error_type,
            "benchmark_run_id": self.benchmark_run_id
        }
        data.update(self.attributes)
        return data

def _emit_span(span: Span):
    pass  # Será integrado ao buffer assíncrono na Task 3

def span(operation: str, route: Optional[str] = None, domain: Optional[str] = None, **kwargs: Any) -> Span:
    return Span(operation=operation, route=route, domain=domain, **kwargs)
```

- [ ] **Step 4: Executar testes de spans e validar passagem**

Run:
```bash
./.venv/bin/pytest tests/test_telemetry.py -v
```
Expected: `3 passed in ...`.

- [ ] **Step 5: Commit do Core de Telemetria**

```bash
git add telemetry.py tests/test_telemetry.py
git commit -m "feat(telemetry): implement span context manager and hierarchy"
```

---

### Task 3: Buffer Assíncrono com Descarte Seguro e Gravação JSONL em Background

**Files:**
- Modify: `telemetry.py`
- Modify: `tests/test_telemetry.py`

**Interfaces:**
- Consumes: `telemetry.Span` da Task 2
- Produces:
  - `telemetry.init_telemetry(events_dir=None, max_queue_size=10000, flush_interval=0.25)`
  - `telemetry.flush(timeout=2.0)`
  - `telemetry.get_dropped_count() -> int`
  - Gravação automática diária em `telemetry/events/events-YYYY-MM-DD.jsonl`

- [ ] **Step 1: Escrever teste para fila assíncrona, descarte por saturação e arquivo JSONL**

Adicionar ao `tests/test_telemetry.py`:
```python
import os
import json
import tempfile
import shutil

def test_telemetry_async_queue_and_file_writer():
    temp_dir = tempfile.mkdtemp()
    try:
        telemetry.init_telemetry(events_dir=temp_dir, max_queue_size=100, flush_interval=0.05)
        
        with telemetry.span("async.op", route="/test") as s:
            s.set_attribute("bytes_received", 1024)
            
        telemetry.flush(timeout=1.0)
        
        files = [f for f in os.listdir(temp_dir) if f.endswith(".jsonl")]
        assert len(files) == 1
        
        file_path = os.path.join(temp_dir, files[0])
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]
            
        assert len(lines) >= 1
        last = lines[-1]
        assert last["operation"] == "async.op"
        assert last["bytes_received"] == 1024
    finally:
        telemetry.shutdown(timeout=1.0)
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_telemetry_queue_overflow_drops_gracefully():
    telemetry.init_telemetry(events_dir=tempfile.gettempdir(), max_queue_size=2, flush_interval=10.0)
    try:
        initial_dropped = telemetry.get_dropped_count()
        # Enche a fila além da capacidade
        for i in range(10):
            with telemetry.span(f"overflow.{i}"):
                pass
                
        # Deve ter descartado eventos sem lançar exceção
        assert telemetry.get_dropped_count() > initial_dropped
    finally:
        telemetry.shutdown(timeout=0.5)
```

- [ ] **Step 2: Executar teste e validar falha**

Run:
```bash
./.venv/bin/pytest tests/test_telemetry.py -k "test_telemetry_async_queue_and_file_writer" -v
```
Expected: FAIL with `AttributeError: module 'telemetry' has no attribute 'init_telemetry'`.

- [ ] **Step 3: Implementar o worker e o buffer assíncrono em `telemetry.py`**

Adicionar em `telemetry.py`:
```python
import atexit
import json
import queue
import threading

class TelemetryEngine:
    def __init__(self, events_dir: str = "telemetry/events", max_queue_size: int = 10000, flush_interval: float = 0.25):
        self.events_dir = events_dir
        self.max_queue_size = max_queue_size
        self.flush_interval = flush_interval
        self.queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self.dropped_events_count = 0
        self._lock = threading.Lock()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
            os.makedirs(self.events_dir, exist_ok=True)
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="TelemetryWorker")
            self._worker_thread.start()

    def enqueue(self, event_dict: Dict[str, Any]):
        if not self._running:
            return
        try:
            self.queue.put_nowait(event_dict)
        except queue.Full:
            with self._lock:
                self.dropped_events_count += 1

    def _worker_loop(self):
        while self._running or not self.queue.empty():
            batch = []
            deadline = time.time() + self.flush_interval
            while time.time() < deadline and len(batch) < 100:
                try:
                    timeout = max(0.01, deadline - time.time())
                    item = self.queue.get(timeout=timeout)
                    batch.append(item)
                    self.queue.task_done()
                except queue.Empty:
                    break
            if batch:
                self._write_batch(batch)

    def _write_batch(self, batch: list):
        try:
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            filename = f"events-{today_str}.jsonl"
            filepath = os.path.join(self.events_dir, filename)
            with open(filepath, "a", encoding="utf-8") as f:
                for item in batch:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def flush(self, timeout: float = 2.0):
        start = time.time()
        while not self.queue.empty() and (time.time() - start) < timeout:
            time.sleep(0.05)

    def shutdown(self, timeout: float = 2.0):
        with self._lock:
            if not self._running:
                return
            self._running = False
        self.flush(timeout=timeout)
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=timeout)

_engine: Optional[TelemetryEngine] = None

def init_telemetry(events_dir: Optional[str] = None, max_queue_size: int = 10000, flush_interval: float = 0.25):
    global _engine
    if _engine is not None:
        _engine.shutdown()
    edir = events_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "telemetry", "events")
    _engine = TelemetryEngine(events_dir=edir, max_queue_size=max_queue_size, flush_interval=flush_interval)
    _engine.start()

def get_dropped_count() -> int:
    return _engine.dropped_events_count if _engine else 0

def flush(timeout: float = 2.0):
    if _engine:
        _engine.flush(timeout=timeout)

def shutdown(timeout: float = 2.0):
    global _engine
    if _engine:
        _engine.shutdown(timeout=timeout)
        _engine = None

def _emit_span(span: Span):
    if _engine:
        _engine.enqueue(span.to_dict())

atexit.register(shutdown)
init_telemetry()
```

- [ ] **Step 4: Executar todos os testes de `tests/test_telemetry.py`**

Run:
```bash
./.venv/bin/pytest tests/test_telemetry.py -v
```
Expected: `5 passed in ...`.

- [ ] **Step 5: Commit do buffer assíncrono**

```bash
git add telemetry.py tests/test_telemetry.py
git commit -m "feat(telemetry): add non-blocking event queue and jsonl background writer"
```

---

### Task 4: Banco SQLite de Benchmarks e Ingestão Idempotente (`telemetry_db.py`)

**Files:**
- Create: `telemetry_db.py`
- Test: `tests/test_telemetry_db.py`

**Interfaces:**
- Consumes: Arquivos JSONL gerados por `telemetry.py`
- Produces:
  - `init_db(db_path: str)`
  - `import_jsonl_file(db_path: str, file_path: str, run_id: str | None = None) -> int`
  - `compute_and_save_summary(db_path: str, run_id: str, operation: str) -> dict`
  - `get_summary(db_path: str, run_id: str) -> list[dict]`

- [ ] **Step 1: Escrever teste para o esquema SQLite, importação e agregação**

Criar `tests/test_telemetry_db.py`:
```python
import os
import json
import tempfile
import telemetry_db

def test_telemetry_db_lifecycle_and_idempotency():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_benchmarks.sqlite3")
    jsonl_path = os.path.join(temp_dir, "events.jsonl")
    
    events = [
        {
            "schema_version": 1,
            "timestamp": "2026-10-23T05:00:00Z",
            "service": "manhua-manager-backend",
            "implementation": "python",
            "revision": "e3a89f1",
            "request_id": "req-1",
            "span_id": "span-1",
            "parent_span_id": None,
            "operation": "chapter.extract",
            "route": None,
            "domain": "comix.to",
            "duration_ms": 100.0,
            "outcome": "success",
            "cache_state": "miss",
            "http_status": 200,
            "upstream_status": 200,
            "error_type": None,
            "bytes_received": 500,
            "image_count": 20,
            "benchmark_run_id": "run-001"
        },
        {
            "schema_version": 1,
            "timestamp": "2026-10-23T05:00:01Z",
            "service": "manhua-manager-backend",
            "implementation": "python",
            "revision": "e3a89f1",
            "request_id": "req-2",
            "span_id": "span-2",
            "parent_span_id": None,
            "operation": "chapter.extract",
            "route": None,
            "domain": "comix.to",
            "duration_ms": 200.0,
            "outcome": "success",
            "cache_state": "hit",
            "http_status": 200,
            "upstream_status": 200,
            "error_type": None,
            "bytes_received": 500,
            "image_count": 20,
            "benchmark_run_id": "run-001"
        }
    ]
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")
            
    telemetry_db.init_db(db_path)
    inserted = telemetry_db.import_jsonl_file(db_path, jsonl_path, run_id="run-001")
    assert inserted == 2
    
    # Re-importação deve ser idempotente (0 novos inseridos)
    re_inserted = telemetry_db.import_jsonl_file(db_path, jsonl_path, run_id="run-001")
    assert re_inserted == 0
    
    summary = telemetry_db.compute_and_save_summary(db_path, "run-001", "chapter.extract")
    assert summary["sample_count"] == 2
    assert summary["success_count"] == 2
    assert summary["p50_duration_ms"] == 150.0
    assert summary["p95_duration_ms"] == 195.0
```

- [ ] **Step 2: Executar teste e validar falha**

Run:
```bash
./.venv/bin/pytest tests/test_telemetry_db.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'telemetry_db'`.

- [ ] **Step 3: Implementar `telemetry_db.py` com esquema histórico**

Criar `telemetry_db.py`:
```python
import sqlite3
import json
import statistics
from typing import Optional, Dict, Any, List

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    start_time TEXT,
    end_time TEXT,
    revision TEXT,
    implementation TEXT,
    scenario TEXT,
    environment TEXT,
    valid INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS samples (
    span_id TEXT PRIMARY KEY,
    run_id TEXT,
    request_id TEXT,
    parent_span_id TEXT,
    operation TEXT NOT NULL,
    route TEXT,
    domain TEXT,
    timestamp TEXT,
    duration_ms REAL,
    outcome TEXT,
    cache_state TEXT,
    http_status INTEGER,
    upstream_status INTEGER,
    error_type TEXT,
    bytes_received INTEGER,
    image_count INTEGER,
    raw_json TEXT,
    FOREIGN KEY(run_id) REFERENCES runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_samples_op ON samples(operation);
CREATE INDEX IF NOT EXISTS idx_samples_run ON samples(run_id);
CREATE INDEX IF NOT EXISTS idx_samples_domain ON samples(domain);

CREATE TABLE IF NOT EXISTS resource_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    timestamp TEXT,
    pid INTEGER,
    process_name TEXT,
    cpu_percent REAL,
    memory_rss_mb REAL,
    memory_pss_mb REAL
);

CREATE TABLE IF NOT EXISTS summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    operation TEXT,
    sample_count INTEGER,
    success_count INTEGER,
    error_count INTEGER,
    p50_duration_ms REAL,
    p95_duration_ms REAL,
    p99_duration_ms REAL,
    min_duration_ms REAL,
    max_duration_ms REAL,
    calculated_at TEXT,
    UNIQUE(run_id, operation)
);
"""

def init_db(db_path: str):
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.executescript(SCHEMA_SQL)

def import_jsonl_file(db_path: str, file_path: str, run_id: Optional[str] = None) -> int:
    init_db(db_path)
    inserted = 0
    with open(file_path, "r", encoding="utf-8") as f, sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                span_id = ev.get("span_id")
                if not span_id:
                    continue
                actual_run_id = run_id or ev.get("benchmark_run_id")
                cursor.execute("""
                    INSERT OR IGNORE INTO samples (
                        span_id, run_id, request_id, parent_span_id, operation,
                        route, domain, timestamp, duration_ms, outcome, cache_state,
                        http_status, upstream_status, error_type, bytes_received,
                        image_count, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    span_id, actual_run_id, ev.get("request_id"), ev.get("parent_span_id"),
                    ev.get("operation"), ev.get("route"), ev.get("domain"), ev.get("timestamp"),
                    ev.get("duration_ms"), ev.get("outcome"), ev.get("cache_state"),
                    ev.get("http_status"), ev.get("upstream_status"), ev.get("error_type"),
                    ev.get("bytes_received"), ev.get("image_count"), line
                ))
                if cursor.rowcount > 0:
                    inserted += 1
            except Exception:
                continue
        conn.commit()
    return inserted

def compute_and_save_summary(db_path: str, run_id: str, operation: str) -> Dict[str, Any]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT duration_ms, outcome FROM samples
            WHERE (run_id = ? OR (? IS NULL AND run_id IS NULL)) AND operation = ?
            ORDER BY duration_ms ASC
        """, (run_id, run_id, operation))
        rows = cursor.fetchall()
        if not rows:
            return {}
            
        durations = [r["duration_ms"] for r in rows if r["duration_ms"] is not None]
        success_count = sum(1 for r in rows if r["outcome"] == "success")
        error_count = sum(1 for r in rows if r["outcome"] == "error")
        sample_count = len(rows)
        
        p50 = float(statistics.median(durations)) if durations else 0.0
        p95 = float(statistics.quantiles(durations, n=100)[94]) if len(durations) >= 2 else (durations[0] if durations else 0.0)
        p99 = float(statistics.quantiles(durations, n=100)[98]) if len(durations) >= 2 else (durations[0] if durations else 0.0)
        
        summary = {
            "run_id": run_id,
            "operation": operation,
            "sample_count": sample_count,
            "success_count": success_count,
            "error_count": error_count,
            "p50_duration_ms": round(p50, 3),
            "p95_duration_ms": round(p95, 3),
            "p99_duration_ms": round(p99, 3),
            "min_duration_ms": round(min(durations), 3) if durations else 0.0,
            "max_duration_ms": round(max(durations), 3) if durations else 0.0,
            "calculated_at": sqlite3.datetime.datetime.now().isoformat()
        }
        
        cursor.execute("""
            INSERT OR REPLACE INTO summaries (
                run_id, operation, sample_count, success_count, error_count,
                p50_duration_ms, p95_duration_ms, p99_duration_ms,
                min_duration_ms, max_duration_ms, calculated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            summary["run_id"], summary["operation"], summary["sample_count"],
            summary["success_count"], summary["error_count"], summary["p50_duration_ms"],
            summary["p95_duration_ms"], summary["p99_duration_ms"], summary["min_duration_ms"],
            summary["max_duration_ms"], summary["calculated_at"]
        ))
        conn.commit()
    return summary
```

- [ ] **Step 4: Executar testes de `tests/test_telemetry_db.py`**

Run:
```bash
./.venv/bin/pytest tests/test_telemetry_db.py -v
```
Expected: `1 passed in ...`.

- [ ] **Step 5: Commit do módulo de persistência SQLite**

```bash
git add telemetry_db.py tests/test_telemetry_db.py
git commit -m "feat(telemetry): add SQLite benchmarks schema, idempotent ingestion and summaries"
```

---

### Task 5: Amostrador de Recursos com `psutil` (`telemetry_sampler.py`)

**Files:**
- Create: `telemetry_sampler.py`
- Test: `tests/test_telemetry_sampler.py`

**Interfaces:**
- Consumes: `psutil`, `telemetry_db`
- Produces:
  - `sample_process_tree(pid: int | None = None) -> list[dict]`
  - `class ResourceSamplerThread(threading.Thread)`

- [ ] **Step 1: Escrever teste para amostragem de processos e filhos**

Criar `tests/test_telemetry_sampler.py`:
```python
import os
import time
import telemetry_sampler

def test_telemetry_sample_process_tree():
    current_pid = os.getpid()
    samples = telemetry_sampler.sample_process_tree(pid=current_pid)
    assert len(samples) >= 1
    
    root_sample = samples[0]
    assert root_sample["pid"] == current_pid
    assert "cpu_percent" in root_sample
    assert root_sample["memory_rss_mb"] > 0
    assert root_sample["memory_pss_mb"] is not None

def test_telemetry_sampler_thread_lifecycle():
    recorded = []
    def on_sample(batch):
        recorded.extend(batch)
        
    sampler = telemetry_sampler.ResourceSampler(callback=on_sample, interval=0.05)
    sampler.start()
    time.sleep(0.12)
    sampler.stop()
    
    assert len(recorded) >= 2
```

- [ ] **Step 2: Executar teste e validar falha**

Run:
```bash
./.venv/bin/pytest tests/test_telemetry_sampler.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'telemetry_sampler'`.

- [ ] **Step 3: Implementar `telemetry_sampler.py`**

Criar `telemetry_sampler.py`:
```python
import os
import time
import threading
import psutil
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Callable

def sample_process_tree(pid: Optional[int] = None) -> List[Dict[str, Any]]:
    target_pid = pid or os.getpid()
    results = []
    now_str = datetime.now(timezone.utc).isoformat()
    
    try:
        root_proc = psutil.Process(target_pid)
        procs = [root_proc] + root_proc.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return []
        
    for p in procs:
        try:
            with p.oneshot():
                p_pid = p.pid
                p_name = p.name()
                cpu = p.cpu_percent(interval=None)
                mem = p.memory_full_info() if hasattr(p, "memory_full_info") else p.memory_info()
                rss_mb = round(mem.rss / (1024 * 1024), 2)
                pss_mb = round(getattr(mem, "pss", mem.rss) / (1024 * 1024), 2)
                
                results.append({
                    "timestamp": now_str,
                    "pid": p_pid,
                    "process_name": p_name,
                    "cpu_percent": cpu,
                    "memory_rss_mb": rss_mb,
                    "memory_pss_mb": pss_mb
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return results

class ResourceSampler:
    def __init__(self, callback: Callable[[List[Dict[str, Any]]], None], interval: float = 1.0, target_pid: Optional[int] = None):
        self.callback = callback
        self.interval = interval
        self.target_pid = target_pid
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="ResourceSampler")
        self._thread.start()

    def _loop(self):
        while self._running:
            samples = sample_process_tree(self.target_pid)
            if samples:
                try:
                    self.callback(samples)
                except Exception:
                    pass
            time.sleep(self.interval)

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
```

- [ ] **Step 4: Executar testes de `tests/test_telemetry_sampler.py`**

Run:
```bash
./.venv/bin/pytest tests/test_telemetry_sampler.py -v
```
Expected: `2 passed in ...`.

- [ ] **Step 5: Commit do coletor de recursos**

```bash
git add telemetry_sampler.py tests/test_telemetry_sampler.py
git commit -m "feat(telemetry): implement psutil process tree sampler and monitor thread"
```

---

### Task 6: Instrumentação do Flask em `server.py` e Métricas de Storage

**Files:**
- Modify: `server.py`
- Create: `tests/test_server_telemetry.py`

**Interfaces:**
- Consumes: `telemetry.py`
- Produces:
  - Hooks `before_request` e `teardown_request` emitindo spans `http.server.request`.
  - Spans `storage.read` e `storage.write` em `load_data()` e `save_data()`.

- [ ] **Step 1: Escrever teste de integração para requisições HTTP e storage**

Criar `tests/test_server_telemetry.py`:
```python
import json
import telemetry
import server

def test_server_http_request_span_and_storage(client):
    events = []
    original_enqueue = telemetry._engine.enqueue
    telemetry._engine.enqueue = lambda ev: events.append(ev)
    try:
        response = client.get("/api/manhuas")
        assert response.status_code == 200
        
        telemetry.flush(timeout=0.5)
        
        # Procura span raiz HTTP e span de storage
        http_spans = [e for e in events if e["operation"] == "http.server.request"]
        storage_spans = [e for e in events if e["operation"] == "storage.read"]
        
        assert len(http_spans) >= 1
        http_span = http_spans[-1]
        assert http_span["route"] == "/api/manhuas"
        assert http_span["http_status"] == 200
        assert http_span["outcome"] == "success"
        
        assert len(storage_spans) >= 1
        storage_span = storage_spans[0]
        assert storage_span["outcome"] == "success"
        assert "item_count" in storage_span
    finally:
        telemetry._engine.enqueue = original_enqueue
```

- [ ] **Step 2: Executar teste e validar falha inicial**

Run:
```bash
./.venv/bin/pytest tests/test_server_telemetry.py -v
```
Expected: FAIL (spans não encontrados ou vazios).

- [ ] **Step 3: Modificar `server.py` para injetar os hooks e spans de storage**

Modificar [`server.py`](file:///home/thiagofdso/Projetos/manhua-manager/server.py):
Importar `telemetry`:
```python
import telemetry
```

Na função `load_data`:
```python
def load_data():
    with telemetry.span("storage.read", file="database.json") as s:
        if not os.path.exists(DB_FILE):
            s.set_attribute("item_count", 0)
            return []
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                s.set_attribute("item_count", len(data) if isinstance(data, list) else 0)
                return data
        except Exception:
            return []
```

Na função `save_data`:
```python
def save_data(data):
    with telemetry.span("storage.write", file="database.json") as s:
        s.set_attribute("item_count", len(data) if isinstance(data, list) else 0)
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
```

Adicionar hooks globais do Flask logo após `CORS(app)`:
```python
@app.before_request
def _telemetry_before_request():
    req_id = request.headers.get("X-Request-ID")
    telemetry.set_request_id(req_id)
    benchmark_id = request.headers.get("X-Benchmark-Run-ID")
    if benchmark_id:
        telemetry.set_benchmark_run_id(benchmark_id)
    
    # Rota parametrizada ou path bruto caso não corresponda a uma url_rule
    rule = request.url_rule.rule if request.url_rule else request.path
    s = telemetry.span("http.server.request", route=rule, method=request.method)
    s.__enter__()
    request._telemetry_span = s

@app.teardown_request
def _telemetry_teardown_request(exc=None):
    s = getattr(request, "_telemetry_span", None)
    if s:
        if exc:
            s.outcome = "error"
            s.error_type = exc.__class__.__name__
        s.__exit__(type(exc) if exc else None, exc, None)
```

No final do arquivo, garantir injeção de `status_code` no `after_request`:
```python
@app.after_request
def _telemetry_after_request(response):
    s = getattr(request, "_telemetry_span", None)
    if s:
        s.http_status = response.status_code
    return response
```

- [ ] **Step 4: Executar `tests/test_server_telemetry.py` e verificar aprovação**

Run:
```bash
./.venv/bin/pytest tests/test_server_telemetry.py -v
```
Expected: `1 passed in ...`.

- [ ] **Step 5: Executar toda a suíte de testes do projeto para garantir zero regressão**

Run:
```bash
./.venv/bin/pytest tests/
```
Expected: 91+ passed (todos os 90 existentes continuam passando).

- [ ] **Step 6: Commit da instrumentação do Flask e Storage**

```bash
git add server.py tests/test_server_telemetry.py
git commit -m "feat(telemetry): instrument HTTP request lifecycle and storage read/write in server.py"
```

---

### Task 7: Instrumentação do Proxy de Imagens e Provedores de Capítulos

**Files:**
- Modify: `server.py` (`/api/proxy-image`)
- Modify: `mangafire_provider.py`
- Modify: `comix_provider.py`
- Modify: `manhuaus_provider.py`
- Create: `tests/test_providers_telemetry.py`

**Interfaces:**
- Consumes: `telemetry.span`
- Produces: Spans `image.proxy` e `chapter.extract` emitidos com atributos de imagens, tempo TTFB e status upstream.

- [ ] **Step 1: Escrever teste para proxy de imagem e provedores**

Criar `tests/test_providers_telemetry.py`:
```python
import json
from unittest.mock import patch
import telemetry
import comix_provider

def test_comix_provider_emits_chapter_extract_span():
    events = []
    original_enqueue = telemetry._engine.enqueue
    telemetry._engine.enqueue = lambda ev: events.append(ev)
    try:
        with patch("comix_provider._extract_with_node", return_value=["https://img.comix.to/1.jpg"]):
            res = comix_provider.extract_chapter_images("https://comix.to/title/ch-1")
            assert len(res) == 1
            
        telemetry.flush(timeout=0.5)
        extract_spans = [e for e in events if e["operation"] == "chapter.extract"]
        assert len(extract_spans) >= 1
        s = extract_spans[-1]
        assert s["domain"] == "comix.to"
        assert s["outcome"] == "success"
        assert s["image_count"] == 1
    finally:
        telemetry._engine.enqueue = original_enqueue
```

- [ ] **Step 2: Executar teste e validar falha**

Run:
```bash
./.venv/bin/pytest tests/test_providers_telemetry.py -v
```
Expected: FAIL (span `chapter.extract` não emitido).

- [ ] **Step 3: Instrumentar `comix_provider.py`, `mangafire_provider.py`, `manhuaus_provider.py` e `/api/proxy-image`**

1. Em [`comix_provider.py`](file:///home/thiagofdso/Projetos/manhua-manager/comix_provider.py):
```python
import telemetry

def extract_chapter_images(chapter_url: str) -> list[str]:
    with telemetry.span("chapter.extract", domain="comix.to") as s:
        # código existente...
        images = _extract_with_node(chapter_url)
        s.set_attribute("image_count", len(images))
        return images
```

2. Em [`mangafire_provider.py`](file:///home/thiagofdso/Projetos/manhua-manager/mangafire_provider.py):
Envolver a função principal de extração com `telemetry.span("chapter.extract", domain="mangafire.to")` registrando `image_count`.

3. Em [`manhuaus_provider.py`](file:///home/thiagofdso/Projetos/manhua-manager/manhuaus_provider.py):
Envolver a função de extração com `telemetry.span("chapter.extract", domain="manhuaus.com")` registrando `image_count`.

4. Na rota `/api/proxy-image` de [`server.py`](file:///home/thiagofdso/Projetos/manhua-manager/server.py):
Envolver a busca externa em:
```python
with telemetry.span("image.proxy", domain=domain) as span:
    # requisição ao upstream e stream de retorno
    span.set_attribute("bytes_received", total_bytes)
```

- [ ] **Step 4: Executar `tests/test_providers_telemetry.py`**

Run:
```bash
./.venv/bin/pytest tests/test_providers_telemetry.py -v
```
Expected: `1 passed in ...`.

- [ ] **Step 5: Executar suíte completa de testes para validação final**

Run:
```bash
./.venv/bin/pytest tests/
```
Expected: Todos os testes (92+) passando com sucesso.

- [ ] **Step 6: Commit da instrumentação de provedores e proxy**

```bash
git add server.py comix_provider.py mangafire_provider.py manhuaus_provider.py tests/test_providers_telemetry.py
git commit -m "feat(telemetry): instrument chapter extraction across providers and image proxy"
```
