import json
from unittest.mock import patch, MagicMock
import telemetry
import comix_provider
import manhuaus_provider
import mangafire_provider
import server

def test_comix_provider_emits_chapter_extract_span():
    events = []
    original_enqueue = telemetry._engine.enqueue
    telemetry._engine.enqueue = lambda ev: events.append(ev)
    try:
        mock_output = MagicMock()
        mock_output.returncode = 0
        mock_output.stdout = json.dumps({
            "status": "ok",
            "number": 1,
            "id": 123,
            "images": ["https://img.comix.to/1.jpg"]
        })
        with patch("subprocess.run", return_value=mock_output), patch("os.path.exists", return_value=True):
            res = comix_provider.get_comix_chapter_data("https://comix.to/title/test/123-chapter-1")
            assert res["status"] == "ok"
            assert len(res["images"]) == 1
            
        telemetry.flush(timeout=0.5)
        extract_spans = [e for e in events if e["operation"] == "chapter.extract"]
        assert len(extract_spans) >= 1
        s = extract_spans[-1]
        assert s["domain"] == "comix.to"
        assert s["outcome"] == "success"
        assert s["image_count"] == 1
    finally:
        telemetry._engine.enqueue = original_enqueue

def test_manhuaus_provider_emits_chapter_extract_span():
    events = []
    original_enqueue = telemetry._engine.enqueue
    telemetry._engine.enqueue = lambda ev: events.append(ev)
    try:
        mock_output = MagicMock()
        mock_output.returncode = 0
        mock_output.stdout = json.dumps({
            "status": "ok",
            "number": 1,
            "images": ["https://img.manhuaus.com/1.jpg", "https://img.manhuaus.com/2.jpg"]
        })
        with patch("subprocess.run", return_value=mock_output), patch("os.path.exists", return_value=True):
            res = manhuaus_provider.get_manhuaus_chapter_data("https://manhuaus.com/manga/test/chapter-1")
            assert res["status"] == "ok"
            assert len(res["images"]) == 2
            
        telemetry.flush(timeout=0.5)
        extract_spans = [e for e in events if e["operation"] == "chapter.extract"]
        assert len(extract_spans) >= 1
        s = extract_spans[-1]
        assert s["domain"] == "manhuaus.com"
        assert s["outcome"] == "success"
        assert s["image_count"] == 2
    finally:
        telemetry._engine.enqueue = original_enqueue

def test_proxy_image_emits_image_proxy_span():
    events = []
    original_enqueue = telemetry._engine.enqueue
    telemetry._engine.enqueue = lambda ev: events.append(ev)
    try:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"fake-image-bytes"
        mock_resp.headers.get.return_value = "image/jpeg"
        mock_resp.__enter__.return_value = mock_resp
        
        with patch("urllib.request.urlopen", return_value=mock_resp):
            server.app.config["TESTING"] = True
            with server.app.test_client() as c:
                res = c.get("/api/proxy-image?url=https://mangafire.to/sample.jpg")
                assert res.status_code == 200
                
        telemetry.flush(timeout=0.5)
        proxy_spans = [e for e in events if e["operation"] == "image.proxy"]
        assert len(proxy_spans) >= 1
        s = proxy_spans[-1]
        assert s["domain"] == "mangafire.to"
        assert s["outcome"] == "success"
        assert s["bytes_received"] == len(b"fake-image-bytes")
    finally:
        telemetry._engine.enqueue = original_enqueue
