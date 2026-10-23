import os
import json
import time
from unittest.mock import patch, MagicMock
from importers.registry import get_registered_domains, get_importer
from importers.asurascans import AsurascansImporter
from importers.ravenscans import RavenscansImporter
from importers.comix import ComixImporter

def test_registry_lists_domains():
    domains = get_registered_domains()
    asura = next((d for d in domains if d["domain"] == "asurascans.com"), None)
    assert asura is not None
    assert asura["supported"] is True
    assert asura["name"] == "Asura Scans"

    raven = next((d for d in domains if d["domain"] == "ravenscans.org"), None)
    assert raven is not None
    assert raven["supported"] is True
    assert raven["name"] == "RavenScans"

    comix = next((d for d in domains if d["domain"] == "comix.to"), None)
    assert comix is not None
    assert comix["supported"] is True
    assert comix["name"] == "Comix"

    importer = get_importer("comix.to")
    assert isinstance(importer, ComixImporter)

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

def test_ravenscans_parsing():
    sample_html = """
    <div class="listupd">
      <div class="bsx">
        <a href="https://ravenscans.org/manga/nano-machine/" title="Nano Machine">
          <div class="tt">Nano Machine</div>
          <div class="epxs">Chapter 335</div>
        </a>
      </div>
      <div class="bsx">
        <a href="https://ravenscans.org/manga/our-strange-surrogate/" title="Our Strange Surrogate">
          <div class="tt">Our Strange Surrogate &amp; Co</div>
          <div class="epxs">Ch. 7</div>
        </a>
      </div>
    </div>
    <div class="pagination">
      <span aria-current="page" class="page-numbers current">1</span>
      <a class="page-numbers" href="/manga/?order=update&#038;page=2">2</a>
      <span class="page-numbers dots">&hellip;</span>
      <a class="page-numbers" href="/manga/?order=update&#038;page=137">137</a>
    </div>
    """
    importer = RavenscansImporter()
    items, total_pages = importer._parse_html(sample_html)
    assert len(items) == 2
    assert items[0]["title"] == "Nano Machine"
    assert items[0]["urlTemplate"] == "https://ravenscans.org/nano-machine-chapter-{chapter}/"
    assert items[0]["lastChapter"] == 335

    assert items[1]["title"] == "Our Strange Surrogate & Co"
    assert items[1]["urlTemplate"] == "https://ravenscans.org/our-strange-surrogate-chapter-{chapter}/"
    assert items[1]["lastChapter"] == 7

    assert total_pages == 137

def test_ravenscans_cache_ttl(tmp_path):
    cache_file = tmp_path / "import_cache_ravenscans_org.json"
    importer = RavenscansImporter(cache_file=str(cache_file))

    # Expired cache
    old_time = time.time() - (8 * 86400)
    old_data = {"timestamp": old_time, "catalog": {}, "totalPages": {}}
    with open(cache_file, "w") as f:
        json.dump(old_data, f)
    assert importer._is_cache_valid() is False

    # Valid cache
    valid_time = time.time() - (3 * 86400)
    old_data["timestamp"] = valid_time
    with open(cache_file, "w") as f:
        json.dump(old_data, f)
    assert importer._is_cache_valid() is True

def test_comix_cache_ttl(tmp_path):
    cache_file = tmp_path / "import_cache_comix_to.json"
    importer = ComixImporter(cache_file=str(cache_file))

    # Expired cache (8 days)
    old_time = time.time() - (8 * 86400)
    old_data = {"timestamp": old_time, "catalog": {}, "totalPages": {}}
    with open(cache_file, "w") as f:
        json.dump(old_data, f)
    assert importer._is_cache_valid() is False

    # Valid cache (3 days)
    valid_time = time.time() - (3 * 86400)
    old_data["timestamp"] = valid_time
    with open(cache_file, "w") as f:
        json.dump(old_data, f)
    assert importer._is_cache_valid() is True

def test_comix_search_or_browse_execution(tmp_path):
    cache_file = tmp_path / "import_cache_comix_to.json"
    fake_script = tmp_path / "comix_catalog_extractor.mjs"
    fake_script.write_text("// dummy")

    importer = ComixImporter(cache_file=str(cache_file), scraper_script=str(fake_script))

    mock_json = {
        "status": "ok",
        "page": 1,
        "totalPages": 24,
        "items": [
            {
                "title": "Mr. Zombie",
                "urlTemplate": "https://comix.to/title/j1ye-mr-zombie/{chapter}",
                "lastChapter": 196
            }
        ]
    }

    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = f"some log line\n{json.dumps(mock_json)}\n"

    with patch("subprocess.run", return_value=mock_res) as mock_run:
        result = importer.search_or_browse(page=1)
        assert mock_run.called
        assert len(result["items"]) == 1
        assert result["items"][0]["title"] == "Mr. Zombie"
        assert result["totalPages"] == 24
        assert result["page"] == 1

    # Verify cache was written
    assert os.path.exists(cache_file)
    with open(cache_file, "r") as f:
        saved_cache = json.load(f)
    assert "catalog" in saved_cache
    assert saved_cache["catalog"][""]["1"][0]["title"] == "Mr. Zombie"

    # Second call should hit cache and not call subprocess.run
    with patch("subprocess.run") as mock_run2:
        cached_result = importer.search_or_browse(page=1)
        assert not mock_run2.called
        assert cached_result["items"][0]["title"] == "Mr. Zombie"

