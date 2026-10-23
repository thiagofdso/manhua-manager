import json
import pytest
import telemetry
import server

@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db = tmp_path / "test_db.json"
    initial_data = [
        {
            "id": 100,
            "title": "Overgeared",
            "urlTemplate": "https://manhuatop.org/manhua/overgeared-org/chapter-{chapter}/",
            "currentChapter": 197,
            "updatedAt": 1000
        }
    ]
    test_db.write_text(json.dumps(initial_data), encoding="utf-8")
    monkeypatch.setattr(server, "DB_FILE", str(test_db))
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c

def test_server_http_request_span_and_storage(client):
    events = []
    original_enqueue = telemetry._engine.enqueue
    telemetry._engine.enqueue = lambda ev: events.append(ev)
    try:
        response = client.get("/api/manhuas")
        assert response.status_code == 200
        
        telemetry.flush(timeout=0.5)
        
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
