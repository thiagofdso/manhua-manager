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
