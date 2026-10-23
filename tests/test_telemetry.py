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
        # Enche a fila alem da capacidade
        for i in range(10):
            with telemetry.span(f"overflow.{i}"):
                pass
                
        # Deve ter descartado eventos sem lancar excecao
        assert telemetry.get_dropped_count() > initial_dropped
    finally:
        telemetry.shutdown(timeout=0.5)

