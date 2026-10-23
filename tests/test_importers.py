import os
import json
import time
from unittest.mock import patch, MagicMock
from importers.registry import get_registered_domains, get_importer
from importers.asurascans import AsurascansImporter

def test_registry_lists_domains():
    domains = get_registered_domains()
    asura = next((d for d in domains if d["domain"] == "asurascans.com"), None)
    assert asura is not None
    assert asura["supported"] is True
    assert asura["name"] == "Asura Scans"

    unsupported = next((d for d in domains if d["domain"] == "mangafire.to"), None)
    assert unsupported is not None
    assert unsupported["supported"] is False

def test_asurascans_parsing():
    sample_html = """
    <div class="series-card group" data-series-id="101">
      <a href="/comics/test-comic-11fe7da3">
        <img src="https://cdn.example.com/cover.webp" alt="Test Comic" />
      </a>
      <div class="p-3">
        <a href="/comics/test-comic-11fe7da3">
          <h3 class="text-sm font-semibold">Test Comic &amp; Adventure</h3>
        </a>
        <div class="flex items-center gap-2 mt-2">
          <span class="text-xs">45 <!-- --> <span>Chapters</span></span>
        </div>
      </div>
    </div>
    <nav id="pagination-nav">
      <button aria-label="Page 1">1</button>
      <button aria-label="Page 2">2</button>
    </nav>
    """
    importer = AsurascansImporter()
    items, total_pages = importer._parse_html(sample_html)
    assert len(items) == 1
    assert items[0]["title"] == "Test Comic & Adventure"
    assert items[0]["urlTemplate"] == "https://asurascans.com/comics/test-comic-11fe7da3/chapter/{chapter}"
    assert items[0]["lastChapter"] == 45
    assert total_pages == 2

def test_asurascans_cache_ttl(tmp_path):
    cache_file = tmp_path / "import_cache_asurascans_com.json"
    importer = AsurascansImporter(cache_file=str(cache_file))

    # Pre-populate cache with timestamp 8 days ago (expired)
    old_time = time.time() - (8 * 86400)
    old_data = {
        "timestamp": old_time,
        "catalog": {"": {"1": [{"title": "Old Comic", "urlTemplate": "old", "lastChapter": 10}]}},
        "totalPages": {"": {"1": 1}}
    }
    with open(cache_file, "w") as f:
        json.dump(old_data, f)

    assert importer._is_cache_valid() is False

    # Pre-populate with timestamp 2 days ago (valid)
    new_time = time.time() - (2 * 86400)
    old_data["timestamp"] = new_time
    with open(cache_file, "w") as f:
        json.dump(old_data, f)

    assert importer._is_cache_valid() is True
