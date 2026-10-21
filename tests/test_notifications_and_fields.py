import os
import json
import pytest
import server

@pytest.fixture(autouse=True)
def clean_test_env(tmp_path, monkeypatch):
    test_db = tmp_path / "test_database.json"
    test_notifs = tmp_path / "test_notifications.json"
    test_db.write_text("[]", encoding="utf-8")
    test_notifs.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(server, "DB_FILE", str(test_db))
    monkeypatch.setattr(server, "NOTIFICATIONS_FILE", str(test_notifs))
    server.app.config["TESTING"] = True

def test_add_manhua_with_last_chapter_and_update_day():
    client = server.app.test_client()
    res = client.post("/api/manhuas", json={
        "title": "Solo Leveling",
        "urlTemplate": "https://asurascans.com/comics/solo/chapter/{chapter}",
        "currentChapter": 10,
        "lastChapter": 15,
        "updateDay": 2,
        "isHiatus": False
    })
    assert res.status_code == 200
    data = res.get_json()["item"]
    assert data["lastChapter"] == 15
    assert data["updateDay"] == 2
    assert data["isHiatus"] is False

def test_patch_manhua_update_fields():
    client = server.app.test_client()
    add_res = client.post("/api/manhuas", json={
        "title": "Tower of God",
        "urlTemplate": "https://asurascans.com/comics/tog/chapter/{chapter}",
        "currentChapter": 1
    })
    item_id = add_res.get_json()["item"]["id"]

    patch_res = client.patch(f"/api/manhuas/{item_id}", json={
        "lastChapter": 500,
        "updateDay": 4,
        "isHiatus": True
    })
    assert patch_res.status_code == 200
    updated = patch_res.get_json()["item"]
    assert updated["lastChapter"] == 500
    assert updated["updateDay"] == 4
    assert updated["isHiatus"] is True

    # Test clearing lastChapter and updateDay with None
    patch_res2 = client.patch(f"/api/manhuas/{item_id}", json={
        "lastChapter": None,
        "updateDay": None,
        "isHiatus": False
    })
    assert patch_res2.status_code == 200
    updated2 = patch_res2.get_json()["item"]
    assert updated2.get("lastChapter") is None
    assert updated2.get("updateDay") is None
    assert updated2["isHiatus"] is False

def test_notifications_crud():
    client = server.app.test_client()
    # Initial list is empty
    assert client.get("/api/notifications").get_json() == []

    # Add notification directly
    notif = server.add_notification(100, "Tower of God", 501)
    assert notif["manhuaId"] == 100
    assert notif["chapter"] == 501
    assert "Novo episódio 501" in notif["message"]

    # Verify listing
    res = client.get("/api/notifications")
    items = res.get_json()
    assert len(items) == 1
    assert items[0]["id"] == notif["id"]

    # Delete specific notification
    del_res = client.delete(f"/api/notifications/{notif['id']}")
    assert del_res.status_code == 200
    assert client.get("/api/notifications").get_json() == []

    # Clear all notifications
    server.add_notification(101, "Overgeared", 244)
    server.add_notification(102, "Nano Machine", 150)
    assert len(client.get("/api/notifications").get_json()) == 2
    clear_res = client.delete("/api/notifications")
    assert clear_res.status_code == 200
    assert client.get("/api/notifications").get_json() == []
