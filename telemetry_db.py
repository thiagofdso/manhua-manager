import sqlite3
import json
import statistics
from datetime import datetime, timezone
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
        p95 = float(statistics.quantiles(durations, n=100, method="inclusive")[94]) if len(durations) >= 2 else (durations[0] if durations else 0.0)
        p99 = float(statistics.quantiles(durations, n=100, method="inclusive")[98]) if len(durations) >= 2 else (durations[0] if durations else 0.0)
        
        now_str = datetime.now(timezone.utc).isoformat()
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
            "calculated_at": now_str
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
