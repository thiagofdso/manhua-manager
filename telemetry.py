import os
import time
import uuid
import subprocess
import atexit
import json
import queue
import threading
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
        if getattr(self, "_exited", False):
            return False
        self._exited = True
        duration_ns = time.perf_counter_ns() - self.start_ns
        self.duration_ms = round(duration_ns / 1_000_000, 3)
        if exc_type is not None:
            self.outcome = "error"
            self.error_type = exc_type.__name__
        if self._token:
            try:
                _current_span_id.reset(self._token)
            except RuntimeError:
                pass
            self._token = None
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
        while self._running or self.queue.unfinished_tasks > 0:
            try:
                item = self.queue.get(timeout=self.flush_interval)
            except queue.Empty:
                continue

            batch = [item]
            while len(batch) < 100:
                try:
                    batch.append(self.queue.get_nowait())
                except queue.Empty:
                    break

            if batch:
                self._write_batch(batch)
                for _ in batch:
                    self.queue.task_done()

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
        while self.queue.unfinished_tasks > 0 and (time.time() - start) < timeout:
            time.sleep(0.01)

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

def span(operation: str, route: Optional[str] = None, domain: Optional[str] = None, **kwargs: Any) -> Span:
    return Span(operation=operation, route=route, domain=domain, **kwargs)

atexit.register(shutdown)
init_telemetry()
