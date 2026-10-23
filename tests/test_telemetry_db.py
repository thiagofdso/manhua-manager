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
