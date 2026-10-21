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
