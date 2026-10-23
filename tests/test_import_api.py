import json
import pytest
from server import app

@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db = tmp_path / "test_db.json"
    initial_data = [
        {
            "id": 1,
            "title": "Existing Overgeared",
            "urlTemplate": "https://asurascans.com/comics/overgeared-11fe7da3/chapter/{chapter}",
            "currentChapter": 100,
            "lastChapter": 300,
            "updateDay": 4
        }
    ]
    with open(test_db, "w", encoding="utf-8") as f:
        json.dump(initial_data, f)

    monkeypatch.setattr("server.DB_FILE", str(test_db))
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

def test_get_import_domains(client):
    res = client.get("/api/import/domains")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)
    asura = next((d for d in data if d["domain"] == "asurascans.com"), None)
    assert asura is not None
    assert asura["supported"] is True

def test_browse_domain_with_duplicate_detection(client, monkeypatch):
    mock_data = {
        "items": [
            {
                "title": "Existing Overgeared",
                "urlTemplate": "https://asurascans.com/comics/overgeared-11fe7da3/chapter/{chapter}",
                "lastChapter": 350
            },
            {
                "title": "Brand New Series",
                "urlTemplate": "https://asurascans.com/comics/brand-new-11fe7da3/chapter/{chapter}",
                "lastChapter": 20
            }
        ],
        "page": 1,
        "totalPages": 3
    }

    class MockImporter:
        def search_or_browse(self, query=None, page=1):
            return mock_data

    monkeypatch.setattr("server.get_importer", lambda d: MockImporter())

    res = client.get("/api/import/browse?domain=asurascans.com")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert len(data["items"]) == 2
    # First item should be detected as already existing
    assert data["items"][0]["alreadyExists"] is True
    # Second item should be brand new
    assert data["items"][1]["alreadyExists"] is False

def test_post_import_prevents_overwrite_and_sets_defaults(client):
    payload = {
        "items": [
            {
                "title": "Existing Overgeared",
                "urlTemplate": "https://asurascans.com/comics/overgeared-11fe7da3/chapter/{chapter}",
                "lastChapter": 350
            },
            {
                "title": "Brand New Series",
                "urlTemplate": "https://asurascans.com/comics/brand-new-11fe7da3/chapter/{chapter}",
                "lastChapter": 20
            }
        ]
    }
    res = client.post("/api/import", json=payload)
    assert res.status_code == 200
    res_data = res.get_json()
    assert res_data["status"] == "ok"
    assert res_data["imported"] == 1
    assert res_data["skipped"] == 1

    # Check manhuas in DB
    list_res = client.get("/api/manhuas")
    manhuas = list_res.get_json()
    assert len(manhuas) == 2

    existing = next(m for m in manhuas if m["title"] == "Existing Overgeared")
    assert existing["currentChapter"] == 100  # Untouched!
    assert existing["updateDay"] == 4          # Untouched!

    new_work = next(m for m in manhuas if m["title"] == "Brand New Series")
    assert new_work["currentChapter"] == 1    # Default 1
    assert new_work["updateDay"] == 6         # Default Sunday (6)
    assert new_work["lastChapter"] == 20
    assert "{chapter}" in new_work["urlTemplate"]


def test_browse_all_cache_endpoint(client, tmp_path):
    from importers.registry import _IMPORTERS
    from importers.all_cache import AllCacheImporter

    # Mock AllCacheImporter pointing to tmp_path
    c_data = {
        "catalog": {
            "": {"1": [
                {"title": "Test Work From Cache", "urlTemplate": "https://test.com/chapter/{chapter}", "lastChapter": 12}
            ]}
        }
    }
    with open(tmp_path / "import_cache_asurascans_com.json", "w") as f:
        json.dump(c_data, f)

    original_importer = _IMPORTERS.get("all")
    _IMPORTERS["all"] = AllCacheImporter(cache_dir=str(tmp_path))
    try:
        res = client.get("/api/import/browse?domain=all")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "ok"
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Test Work From Cache"
        assert data["items"][0]["domainName"] == "Asura Scans"
        assert "alreadyExists" in data["items"][0]
    finally:
        if original_importer:
            _IMPORTERS["all"] = original_importer

