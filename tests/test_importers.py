import os
import json
import time
from unittest.mock import patch, MagicMock
from importers.registry import get_registered_domains, get_importer
from importers.asurascans import AsurascansImporter
from importers.ravenscans import RavenscansImporter
from importers.comix import ComixImporter
from importers.manhuaus import ManhuausImporter
from importers.arenascan import ArenascanImporter
from importers.manhuatop import ManhuatopImporter
from importers.mgeko import MgekoImporter
from importers.mangak import MangakImporter

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

    manhuaus = next((d for d in domains if d["domain"] == "manhuaus.com"), None)
    assert manhuaus is not None
    assert manhuaus["supported"] is True
    assert manhuaus["name"] == "ManhuaUS"

    arena = next((d for d in domains if d["domain"] == "arenascan.com"), None)
    assert arena is not None
    assert arena["supported"] is True
    assert arena["name"] == "ArenaScan"

    top = next((d for d in domains if d["domain"] == "manhuatop.org"), None)
    assert top is not None
    assert top["supported"] is True
    assert top["name"] == "ManhuaTop"

    mgeko = next((d for d in domains if d["domain"] == "mgeko.cc"), None)
    assert mgeko is not None
    assert mgeko["supported"] is True
    assert mgeko["name"] == "MGeko"

    mangak = next((d for d in domains if d["domain"] == "mangak.io"), None)
    assert mangak is not None
    assert mangak["supported"] is True
    assert mangak["name"] == "MangaK"

    importer = get_importer("mangak.io")
    assert isinstance(importer, MangakImporter)

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

def test_manhuaus_cache_ttl(tmp_path):
    cache_file = tmp_path / "import_cache_manhuaus_com.json"
    importer = ManhuausImporter(cache_file=str(cache_file))

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

def test_manhuaus_search_or_browse_execution(tmp_path):
    cache_file = tmp_path / "import_cache_manhuaus_com.json"
    fake_script = tmp_path / "manhuaus_catalog_extractor.mjs"
    fake_script.write_text("// dummy")

    importer = ManhuausImporter(cache_file=str(cache_file), scraper_script=str(fake_script))

    mock_json = {
        "status": "ok",
        "page": 1,
        "totalPages": 112,
        "items": [
            {
                "title": "Magic Emperor",
                "urlTemplate": "https://manhuaus.com/manga/magic-emperor-0/chapter-{chapter}/",
                "lastChapter": 925
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
        assert result["items"][0]["title"] == "Magic Emperor"
        assert result["totalPages"] == 112
        assert result["page"] == 1

    # Verify cache was written
    assert os.path.exists(cache_file)
    with open(cache_file, "r") as f:
        saved_cache = json.load(f)
    assert "catalog" in saved_cache
    assert saved_cache["catalog"][""]["1"][0]["title"] == "Magic Emperor"

    # Second call should hit cache and not call subprocess.run
    with patch("subprocess.run") as mock_run2:
        cached_result = importer.search_or_browse(page=1)
        assert not mock_run2.called
        assert cached_result["items"][0]["title"] == "Magic Emperor"

def test_arenascan_parsing():
    sample_html = """
    <div class="listupd">
      <div class="bs">
        <div class="bsx">
          <a href="https://arenascan.com/manga/a-regressors-tale-of-cultivation/" title="A Regressor’s Tale of Cultivation">
            <div class="bigor">
              <div class="tt">A Regressor’s Tale of Cultivation</div>
              <div class="adds">
                <div class="epxs">Chapter 35</div>
              </div>
            </div>
          </a>
        </div>
      </div>
      <div class="bs">
        <div class="bsx">
          <a href="https://arenascan.com/manga/after-rebirth-i-used-mirror-reversal-for-vengeance/" title="After Rebirth, I Used Mirror Reversal For Vengeance">
            <div class="bigor">
              <div class="tt">After Rebirth, I Used Mirror Reversal For Vengeance</div>
              <div class="adds">
                <div class="epxs">Chapter 71</div>
              </div>
            </div>
          </a>
        </div>
      </div>
    </div>
    <div class="pagination">
      <span aria-current="page" class="page-numbers current">1</span>
      <a class="page-numbers" href="/manga/?order=update&#038;page=2">2</a>
      <span class="page-numbers dots">&hellip;</span>
      <a class="page-numbers" href="/manga/?order=update&#038;page=259">259</a>
      <a class="next page-numbers" href="/manga/?order=update&#038;page=2">Next</a>
    </div>
    """
    importer = ArenascanImporter()
    items, total_pages = importer._parse_html(sample_html)
    assert len(items) == 2
    assert items[0]["title"] == "A Regressor’s Tale of Cultivation"
    assert items[0]["urlTemplate"] == "https://arenascan.com/a-regressors-tale-of-cultivation-chapter-{chapter}/"
    assert items[0]["lastChapter"] == 35

    assert items[1]["title"] == "After Rebirth, I Used Mirror Reversal For Vengeance"
    assert items[1]["urlTemplate"] == "https://arenascan.com/after-rebirth-i-used-mirror-reversal-for-vengeance-chapter-{chapter}/"
    assert items[1]["lastChapter"] == 71

    assert total_pages == 259

def test_arenascan_cache_ttl(tmp_path):
    cache_file = tmp_path / "import_cache_arenascan_com.json"
    importer = ArenascanImporter(cache_file=str(cache_file))

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

def test_manhuatop_cache_ttl(tmp_path):
    cache_file = tmp_path / "import_cache_manhuatop_org.json"
    importer = ManhuatopImporter(cache_file=str(cache_file))

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

def test_manhuatop_search_or_browse_execution(tmp_path):
    cache_file = tmp_path / "import_cache_manhuatop_org.json"
    fake_script = tmp_path / "manhuatop_catalog_extractor.mjs"
    fake_script.write_text("// dummy")

    importer = ManhuatopImporter(cache_file=str(cache_file), scraper_script=str(fake_script))

    mock_json = {
        "status": "ok",
        "page": 1,
        "totalPages": 113,
        "items": [
            {
                "title": "Apex Future Martial Arts",
                "urlTemplate": "https://manhuatop.org/manhua/apex-future-martial-arts/chapter-{chapter}/",
                "lastChapter": 362
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
        assert result["items"][0]["title"] == "Apex Future Martial Arts"
        assert result["totalPages"] == 113
        assert result["page"] == 1

    # Verify cache was written
    assert os.path.exists(cache_file)
    with open(cache_file, "r") as f:
        saved_cache = json.load(f)
    assert "catalog" in saved_cache
    assert saved_cache["catalog"][""]["1"][0]["title"] == "Apex Future Martial Arts"

    # Second call should hit cache and not call subprocess.run
    with patch("subprocess.run") as mock_run2:
        cached_result = importer.search_or_browse(page=1)
        assert not mock_run2.called
        assert cached_result["items"][0]["title"] == "Apex Future Martial Arts"

def test_mgeko_cache_ttl(tmp_path):
    cache_file = tmp_path / "import_cache_mgeko_cc.json"
    importer = MgekoImporter(cache_file=str(cache_file))

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

def test_mgeko_parsing_and_details():
    sample_results_html = """
    <article class="comic-card">
      <div class="comic-card__content">
        <h3 class="comic-card__title">
          <a href="/manga/cenv-the-glutton/">
            The Glutton
          </a>
        </h3>
      </div>
    </article>
    """
    sample_detail_html = """
    <html>
      <body>
        <li class="chapter-list-item">
          <a href="/reader/en/cenv-the-glutton-chapter-53-eng-li/">
            53-eng-li
          </a>
        </li>
      </body>
    </html>
    """
    importer = MgekoImporter()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = sample_detail_html

    with patch("requests.get", return_value=mock_resp):
        items = importer._parse_results_html(sample_results_html)

    assert len(items) == 1
    assert items[0]["title"] == "The Glutton"
    assert items[0]["urlTemplate"] == "https://www.mgeko.cc/reader/en/cenv-the-glutton-chapter-{chapter}-eng-li/"
    assert items[0]["lastChapter"] == 53

def test_mangak_cache_ttl(tmp_path):
    cache_file = tmp_path / "import_cache_mangak_io.json"
    importer = MangakImporter(cache_file=str(cache_file))

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

def test_mangak_parsing():
    sample_data = {
        "props": {
            "pageProps": {
                "items": [
                    {
                        "name": "The New Employee Chairman Kang",
                        "slug": "the-new-employee-chairman-kang",
                        "latestChapters": [
                            {"name": "Chapter 92", "url": "/the-new-employee-chairman-kang/chapter-92"}
                        ]
                    }
                ],
                "pagination": {
                    "total": 10000,
                    "page": 1,
                    "total_pages": 416
                }
            }
        }
    }
    sample_html = f"""
    <html>
      <head>
        <script id="__NEXT_DATA__" type="application/json">{json.dumps(sample_data)}</script>
      </head>
      <body></body>
    </html>
    """
    importer = MangakImporter()
    items, total_pages = importer._parse_next_data(sample_html)
    assert len(items) == 1
    assert items[0]["title"] == "The New Employee Chairman Kang"
    assert items[0]["urlTemplate"] == "https://mangak.io/the-new-employee-chairman-kang/chapter-{chapter}"
    assert items[0]["lastChapter"] == 92
    assert total_pages == 416






