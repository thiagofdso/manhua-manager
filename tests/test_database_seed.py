# tests/test_database_seed.py
import json
import os

def test_initial_database_seed():
    db_path = os.path.join(os.path.dirname(__file__), "..", "database.json")
    assert os.path.exists(db_path), "database.json must exist"
    
    with open(db_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    assert isinstance(data, list)
    assert len(data) >= 1
    overgeared = next((item for item in data if "Overgeared" in item.get("title", "")), None)
    assert overgeared is not None
    assert overgeared["currentChapter"] >= 197
    assert "https://asurascans.com/comics/overgeared-11fe7da3/chapter/{chapter}" in overgeared["urlTemplate"]
