# tests/test_server.py
import pytest
import json
import os
import tempfile
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
    with server.app.test_client() as client:
        yield client

def test_get_manhuas(client):
    res = client.get("/api/manhuas")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data) == 1
    assert data[0]["title"] == "Overgeared"
    assert data[0]["currentChapter"] == 197

def test_add_manhua(client):
    payload = {
        "title": "Solo Leveling",
        "urlTemplate": "https://exemplo.com/chapter-{chapter}/",
        "currentChapter": 10
    }
    res = client.post("/api/manhuas", json=payload)
    assert res.status_code == 200
    res_data = res.get_json()
    assert res_data["status"] == "ok"
    assert res_data["item"]["title"] == "Solo Leveling"

def test_patch_chapter_delta(client):
    res = client.patch("/api/manhuas/100", json={"delta": 1})
    assert res.status_code == 200
    data = res.get_json()
    assert data["item"]["currentChapter"] == 198

def test_patch_chapter_specific(client):
    res = client.patch("/api/manhuas/100", json={"chapter": 205})
    assert res.status_code == 200
    data = res.get_json()
    assert data["item"]["currentChapter"] == 205

def test_patch_full_edit(client):
    payload = {
        "title": "Overgeared (Renomeado)",
        "urlTemplate": "https://novo-site.com/obra/chapter-{chapter}/",
        "chapter": 200
    }
    res = client.patch("/api/manhuas/100", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["item"]["title"] == "Overgeared (Renomeado)"
    assert data["item"]["urlTemplate"] == "https://novo-site.com/obra/chapter-{chapter}/"
    assert data["item"]["currentChapter"] == 200

def test_delete_manhua(client):
    res = client.delete("/api/manhuas/100")
    assert res.status_code == 200
    list_res = client.get("/api/manhuas")
    assert len(list_res.get_json()) == 0

def test_get_chapter_images_endpoint(client):
    from unittest.mock import patch, MagicMock
    mock_html = """
    <html>
      <body>
        <img class="img-responsive" src="https://manhuatop.org/logo.png" />
        <img src="https://manhuatop.org/about_manhuatop.webp" class="wp-manga-chapter-img" />
        <img id="image-0" src="https://s2.manhuatop.org/chapter_197/page_1.jpg" class="wp-manga-chapter-img" />
        <img id="image-1" class="wp-manga-chapter-img" src="https://s2.manhuatop.org/chapter_197/page_2.jpg" />
      </body>
    </html>
    """.encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.read.return_value = mock_html
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = client.get("/api/chapter-images?url=https://manhuatop.org/manhua/test/chapter-1/")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "ok"
        assert len(data["images"]) == 2
        assert "page_1.jpg" in data["images"][0]
        assert "page_2.jpg" in data["images"][1]

def test_proxy_image_endpoint(client):
    from unittest.mock import patch, MagicMock
    mock_image_bytes = b"\xff\xd8\xff\xe0fake_jpeg_content"
    mock_resp = MagicMock()
    mock_resp.read.return_value = mock_image_bytes
    mock_resp.headers = {"Content-Type": "image/jpeg"}
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = client.get("/api/proxy-image?url=https://s2.manhuatop.org/test.jpg")
        assert res.status_code == 200
        assert res.data == mock_image_bytes
        assert res.content_type == "image/jpeg"

def test_extract_manhuatop_images():
    html = """
    <img src="https://manhuatop.org/about_manhuatop.webp" class="wp-manga-chapter-img" />
    <img src="https://s2.manhuatop.org/page1.jpg" class="wp-manga-chapter-img" />
    <img src="https://s2.manhuatop.org/page2.jpg" class="wp-manga-chapter-img" />
    """
    imgs = server.extract_manhuatop_images(html)
    assert imgs == ["https://s2.manhuatop.org/page1.jpg", "https://s2.manhuatop.org/page2.jpg"]

def test_extract_asurascans_images():
    html = """
    <img src="https://cdn.asurascans.com/asura-images/covers/overgeared.905990.webp" />
    <img src="https://cdn.asurascans.com/asura-images/chapters-merged/overgeared/162615/001.webp?v=1791877385" alt="Page 1" class="w-full" />
    <img src="https://cdn.asurascans.com/asura-images/chapters-merged/overgeared/162615/002.webp?v=1791877385" alt="Page 2" class="w-full" />
    """
    imgs = server.extract_asurascans_images(html)
    assert len(imgs) == 2
    assert imgs[0] == "https://cdn.asurascans.com/asura-images/chapters-merged/overgeared/162615/001.webp?v=1791877385"
    assert imgs[1] == "https://cdn.asurascans.com/asura-images/chapters-merged/overgeared/162615/002.webp?v=1791877385"

def test_extract_asurascans_images_unmerged_chapters_path():
    html = """
    <img src="https://cdn.asurascans.com/asura-images/covers/the-extras-academy-survival-guide.18d91e.webp" />
    <img src="https://cdn.asurascans.com/asura-images/chapters/the-extras-academy-survival-guide/74/001.webp?v=1791864274" />
    <img src="https://cdn.asurascans.com/asura-images/chapters/the-extras-academy-survival-guide/74/002.webp?v=1791864274" />
    """
    imgs = server.extract_asurascans_images(html)
    assert len(imgs) == 2
    assert imgs[0] == "https://cdn.asurascans.com/asura-images/chapters/the-extras-academy-survival-guide/74/001.webp?v=1791864274"
    assert imgs[1] == "https://cdn.asurascans.com/asura-images/chapters/the-extras-academy-survival-guide/74/002.webp?v=1791864274"

def test_extract_chapter_images_by_domain_dispatch():
    asura_html = '<img src="https://cdn.asurascans.com/asura-images/chapters-merged/test/1/001.webp" />'
    imgs = server.extract_chapter_images_by_domain(asura_html, "https://asurascans.com/comics/test/chapter/1")
    assert len(imgs) == 1
    assert "001.webp" in imgs[0]

def test_get_chapter_images_endpoint_asurascans(client):
    from unittest.mock import patch, MagicMock
    mock_html = """
    <html>
      <body>
        <astro-island props="{&quot;seriesSlug&quot;:[0,&quot;overgeared&quot;]}">
          <img src="https://cdn.asurascans.com/asura-images/chapters-merged/overgeared/162615/001.webp?v=1" />
          <img src="https://cdn.asurascans.com/asura-images/chapters-merged/overgeared/162615/002.webp?v=1" />
        </astro-island>
      </body>
    </html>
    """.encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.read.return_value = mock_html
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = client.get("/api/chapter-images?url=https://asurascans.com/comics/overgeared-11fe7da3/chapter/197")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "ok"
        assert len(data["images"]) == 2
        assert "001.webp" in data["images"][0]

def test_proxy_image_asurascans_referer(client):
    from unittest.mock import patch, MagicMock
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"fake-webp-binary"
    mock_resp.headers = {"Content-Type": "image/webp"}
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        res = client.get("/api/proxy-image?url=https://cdn.asurascans.com/asura-images/chapters-merged/test/1/001.webp")
        assert res.status_code == 200
        assert res.data == b"fake-webp-binary"
        req_arg = mock_urlopen.call_args[0][0]
        assert req_arg.get_header("Referer") == "https://asurascans.com/"

def test_extract_ravenscans_images_ts_reader():
    html = """
    <script type="text/javascript">
    ts_reader.run({
        "post_id": 773298,
        "sources": [
            {
                "source": "Server 1",
                "images": [
                    "https://cdn5.ravenscans.org/almighty-pig-slaughtering-knife/chapter-61/0.webp",
                    "https://cdn5.ravenscans.org/almighty-pig-slaughtering-knife/chapter-61/1.webp"
                ]
            }
        ]
    });
    </script>
    """
    imgs = server.extract_ravenscans_images(html)
    assert len(imgs) == 2
    assert imgs[0] == "https://cdn5.ravenscans.org/almighty-pig-slaughtering-knife/chapter-61/0.webp"
    assert imgs[1] == "https://cdn5.ravenscans.org/almighty-pig-slaughtering-knife/chapter-61/1.webp"

def test_extract_ravenscans_images_readerarea_fallback():
    html = """
    <div id="readerarea">
        <img class="ts-main-image" src="https://cdn5.ravenscans.org/almighty-pig-slaughtering-knife/chapter-61/0.webp" />
        <img class="ts-main-image lazy" src="https://ravenscans.org/wp-content/themes/mangareader/assets/img/readerarea.svg" data-src="https://cdn5.ravenscans.org/almighty-pig-slaughtering-knife/chapter-61/1.webp" />
    </div>
    """
    imgs = server.extract_ravenscans_images(html)
    assert len(imgs) == 2
    assert imgs[0] == "https://cdn5.ravenscans.org/almighty-pig-slaughtering-knife/chapter-61/0.webp"
    assert imgs[1] == "https://cdn5.ravenscans.org/almighty-pig-slaughtering-knife/chapter-61/1.webp"

def test_extract_chapter_images_by_domain_ravenscans():
    html = '<div id="readerarea"><img src="https://cdn5.ravenscans.org/knife/61/0.webp" /></div>'
    imgs = server.extract_chapter_images_by_domain(html, "https://ravenscans.org/almighty-pig-slaughtering-knife-chapter-61/")
    assert len(imgs) == 1
    assert "0.webp" in imgs[0]

def test_proxy_image_ravenscans_referer(client):
    from unittest.mock import patch, MagicMock
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"fake-webp-binary"
    mock_resp.headers = {"Content-Type": "image/webp"}
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        res = client.get("/api/proxy-image?url=https://cdn5.ravenscans.org/knife/61/0.webp")
        assert res.status_code == 200
        assert res.data == b"fake-webp-binary"
        req_arg = mock_urlopen.call_args[0][0]
        assert req_arg.get_header("Referer") == "https://ravenscans.org/"

def test_proxy_image_mangafire_referer(client):
    from unittest.mock import patch, MagicMock
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"fake-jpeg-binary"
    mock_resp.headers = {"Content-Type": "image/jpeg"}
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        res = client.get("/api/proxy-image?url=https://l1n.mfcdn1.xyz/mf/abc/h/p.jpg")
        assert res.status_code == 200
        assert res.data == b"fake-jpeg-binary"
        req_arg = mock_urlopen.call_args[0][0]
        assert req_arg.get_header("Referer") == "https://mangafire.to/"

def test_mangafire_parse_url():
    import mangafire_provider
    hid, ch = mangafire_provider.parse_mangafire_url(
        "https://mangafire.to/title/nk6zl-necromancer-the-ultimate-scourge/chapter/9427010"
    )
    assert hid == "nk6zl"
    assert ch == "9427010"

    hid2, ch2 = mangafire_provider.parse_mangafire_url(
        "https://mangafire.to/title/nk6zl-necromancer-the-ultimate-scourge/chapter/{chapter}"
    )
    assert hid2 == "nk6zl"
    assert ch2 == "{chapter}"

def test_get_chapter_images_mangafire_endpoint(client):
    from unittest.mock import patch
    fake_data = {
        "status": "ok",
        "count": 2,
        "images": [
            "https://l1n.mfcdn1.xyz/mf/p1.jpg",
            "https://l1n.mfcdn1.xyz/mf/p2.jpg"
        ],
        "chapter": 306,
        "chapterId": 9427010,
        "title": "Necromancer, the Ultimate Scourge!",
        "prev": {"id": 9426675, "number": 305, "url": "/title/nk6zl/chapter/9426675"},
        "next": {"id": 9442025, "number": 307, "url": "/title/nk6zl/chapter/9442025"}
    }

    with patch("mangafire_provider.get_mangafire_chapter_data", return_value=fake_data):
        res = client.get("/api/chapter-images?url=https://mangafire.to/title/nk6zl-necromancer/chapter/9427010")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "ok"
        assert data["chapter"] == 306
        assert data["chapterId"] == 9427010
        assert len(data["images"]) == 2
        assert data["next"]["id"] == 9442025

def test_mangafire_add_and_delta_navigation(client):
    from unittest.mock import patch
    fake_meta = {
        "id": 9427010,
        "number": 306,
        "next": {"id": 9442025, "number": 307, "url": "/title/nk6zl/chapter/9442025"},
        "prev": {"id": 9426675, "number": 305, "url": "/title/nk6zl/chapter/9426675"}
    }

    with patch("mangafire_provider.fetch_chapter_by_id", return_value=fake_meta):
        # 1. Add manhua with chapter ID URL
        res = client.post("/api/manhuas", json={
            "title": "Necromancer",
            "urlTemplate": "https://mangafire.to/title/nk6zl-necromancer/chapter/9427010",
            "currentChapter": 306
        })
        assert res.status_code == 200
        item = res.get_json()["item"]
        assert item["currentChapter"] == 306
        assert item["chapterId"] == 9427010
        assert item["urlTemplate"] == "https://mangafire.to/title/nk6zl-necromancer/chapter/{chapter}"
        assert item["nextChapter"]["id"] == 9442025
        assert item["prevChapter"]["id"] == 9426675
        item_id = item["id"]

        # 2. Advance to next chapter via delta +1
        delta_res = client.patch(f"/api/manhuas/{item_id}", json={"delta": 1})
        assert delta_res.status_code == 200
        updated = delta_res.get_json()["item"]
        assert updated["currentChapter"] == 307
        assert updated["chapterId"] == 9442025

        # 3. Reset to 306 and step back to previous chapter via delta -1
        client.patch(f"/api/manhuas/{item_id}", json={"chapter": 306})
        # Restore prevChapter in DB or test delta -1 from 306
        back_res = client.patch(f"/api/manhuas/{item_id}", json={"delta": -1})
        assert back_res.status_code == 200
        assert back_res.get_json()["item"]["currentChapter"] == 305
        assert back_res.get_json()["item"]["chapterId"] == 9426675


def test_comix_provider_parsing():
    import comix_provider
    url = "https://comix.to/title/q8qxd-the-jobless-guy-who-has-come-to-slay/11349222-chapter-231"
    assert comix_provider.is_comix_url(url)
    slug, ch_id, ch_num = comix_provider.parse_comix_url(url)
    assert slug == "q8qxd-the-jobless-guy-who-has-come-to-slay"
    assert ch_id == 11349222
    assert ch_num == 231


def test_comix_chapter_images_endpoint(client):
    from unittest.mock import patch
    fake_data = {
        "status": "ok",
        "images": [
            "https://rxn.markscorner.site/hi/bEqPbYfo1",
            "https://rxn.markscorner.site/hi/bEqPbYfo2"
        ],
        "chapter": 231,
        "chapterId": 11349222,
        "prev": {"id": 11323925, "number": 230, "url": "https://comix.to/title/q8qxd/11323925-chapter-230"},
        "next": {"id": 11385174, "number": 232, "url": "https://comix.to/title/q8qxd/11385174-chapter-232"}
    }

    with patch("comix_provider.get_comix_chapter_data", return_value=fake_data):
        res = client.get("/api/chapter-images?url=https://comix.to/title/q8qxd-the-jobless-guy-who-has-come-to-slay/11349222-chapter-231")
        assert res.status_code == 200
        data = res.get_json()
        assert data["chapter"] == 231
        assert data["chapterId"] == 11349222
        assert len(data["images"]) == 2
        assert data["next"]["id"] == 11385174


def test_comix_add_and_delta_navigation(client):
    from unittest.mock import patch
    fake_data = {
        "images": ["https://rxn.markscorner.site/hi/1"],
        "chapter": 231,
        "chapterId": 11349222,
        "prev": {"id": 11323925, "number": 230, "url": "https://comix.to/title/q8qxd/11323925-chapter-230"},
        "next": {"id": 11385174, "number": 232, "url": "https://comix.to/title/q8qxd/11385174-chapter-232"}
    }

    with patch("comix_provider.get_comix_chapter_data", return_value=fake_data):
        # 1. Add manhua with chapter ID URL
        res = client.post("/api/manhuas", json={
            "title": "The Jobless Guy",
            "urlTemplate": "https://comix.to/title/q8qxd-the-jobless-guy-who-has-come-to-slay/11349222-chapter-231",
            "currentChapter": 231
        })
        assert res.status_code == 200
        item = res.get_json()["item"]
        assert item["currentChapter"] == 231
        assert item["chapterId"] == 11349222
        assert item["urlTemplate"] == "https://comix.to/title/q8qxd-the-jobless-guy-who-has-come-to-slay/{chapter}"
        assert item["nextChapter"]["id"] == 11385174
        assert item["prevChapter"]["id"] == 11323925
        item_id = item["id"]

        # 2. Advance to next chapter via delta +1
        delta_res = client.patch(f"/api/manhuas/{item_id}", json={"delta": 1})
        assert delta_res.status_code == 200
        updated = delta_res.get_json()["item"]
        assert updated["currentChapter"] == 232
        assert updated["chapterId"] == 11385174

        # 3. Reset to 231 and step back to previous chapter via delta -1
        client.patch(f"/api/manhuas/{item_id}", json={"chapter": 231})
        back_res = client.patch(f"/api/manhuas/{item_id}", json={"delta": -1})
        assert back_res.status_code == 200
        assert back_res.get_json()["item"]["currentChapter"] == 230
        assert back_res.get_json()["item"]["chapterId"] == 11323925


def test_comix_proxy_image_no_referer(client):
    from unittest.mock import patch, MagicMock

    mock_resp = MagicMock()
    mock_resp.read.return_value = b"fake-webp-image"
    mock_resp.headers = {"Content-Type": "image/webp"}
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        res = client.get("/api/proxy-image?url=https://rxn.markscorner.site/hi/bEqPbYfo1")
        assert res.status_code == 200
        assert res.data == b"fake-webp-image"
        # Verify request had no Referer
        req = mock_urlopen.call_args[0][0]
        assert "Referer" not in req.headers


def test_extract_mangak_images():
    html = '''
    <script id="__NEXT_DATA__" type="application/json">
    {"props":{"pageProps":{"initialChapter":{"images":["https://rx.qvzra.org/img1.webp","https://rx.qvzrb.org/img2.webp"]}}}}
    </script>
    '''
    imgs = server.extract_mangak_images(html)
    assert len(imgs) == 2
    assert "img1.webp" in imgs[0]
    assert "img2.webp" in imgs[1]


def test_extract_mgeko_images():
    html = '''
    <div id="chapter-reader">
        <img id="image-0" src="https://imgsrv5.com/sv2/comic/page1.jpg" />
        <img id="image-1" src="https://imgsrv5.com/sv2/comic/page2.jpg" />
        <img src="https://imgsrv5.com/banner.png" />
    </div>
    '''
    imgs = server.extract_mgeko_images(html)
    assert len(imgs) == 2
    assert "page1.jpg" in imgs[0]
    assert "page2.jpg" in imgs[1]


def test_extract_levelingwithgods_images():
    html = '''
    <div class="entry-content">
        <img class="lazy" data-src="https://blogger.googleusercontent.com/img1.png" src="lazy_placeholder.gif" />
        <img src="https://blogger.googleusercontent.com/img1.png" />
        <img class="lazy" data-src="https://blogger.googleusercontent.com/img2.png" src="lazy_placeholder.gif" />
    </div>
    '''
    imgs = server.extract_levelingwithgods_images(html)
    assert len(imgs) == 2
    assert "img1.png" in imgs[0]
    assert "img2.png" in imgs[1]


def test_extract_pickmeupgacha_images():
    html = '''
    <div class="elementor-widget-container">
        <img data-src="https://abyssrift.com/Gacha/219/01.webp" />
        <img data-src="https://abyssrift.com/Gacha/219/02.webp" />
    </div>
    '''
    imgs = server.extract_pickmeupgacha_images(html)
    assert len(imgs) == 2
    assert "01.webp" in imgs[0]
    assert "02.webp" in imgs[1]


def test_extract_magicemperor_images():
    html = '''
    <div class="entry-content">
        <img src="https://cdn.black-clover.org/file/flanbox/magic-emperor/chapter-900/1.webp" />
        <img src="https://cdn.black-clover.org/file/flanbox/magic-emperor/chapter-900/2.webp" />
    </div>
    <!-- .entry-content -->
    '''
    imgs = server.extract_magicemperor_images(html)
    assert len(imgs) == 2
    assert "1.webp" in imgs[0]
    assert "2.webp" in imgs[1]


def test_extract_arenascan_images():
    html = '''
    <img src="https://arenascan.com/logo.png" />
    <img src="https://cdn.arenascan.com/arena-bucket/229402/63/1.webp" />
    <img src="https://cdn.arenascan.com/arena-bucket/229402/63/2.webp" />
    '''
    imgs = server.extract_arenascan_images(html)
    assert len(imgs) == 2
    assert "1.webp" in imgs[0]


def test_extract_html_navigation():
    # Next.js / mangak
    html_next = '''
    <script id="__NEXT_DATA__" type="application/json">
    {"props":{"pageProps":{"nextChapter":{"url":"/slug/chapter-225"},"previousChapter":{"url":"/slug/chapter-223"}}}}
    </script>
    '''
    nxt, prv = server.extract_html_navigation(html_next, "https://mangak.io/slug/chapter-224")
    assert nxt["number"] == 225
    assert prv["number"] == 223

    # mgeko
    html_mgeko = '''
    <a class=" chnav prev" href="/reader/en/test-chapter-21-eng-li/">Prev</a>
    <a class=" chnav next" href="/reader/en/test-chapter-23-eng-li/">Next</a>
    '''
    nxt_m, prv_m = server.extract_html_navigation(html_mgeko, "https://www.mgeko.cc/reader/en/test-chapter-22-eng-li/")
    assert nxt_m["number"] == 23
    assert prv_m["number"] == 21

    # Generic post navigation
    html_gen = '''
    <div class="next-post"><a href="https://example.com/chapter-101/">Next</a></div>
    <div class="prev-post"><a href="https://example.com/chapter-99/">Prev</a></div>
    '''
    nxt_g, prv_g = server.extract_html_navigation(html_gen, "https://example.com/chapter-100/")
    assert nxt_g["number"] == 101
    assert prv_g["number"] == 99


def test_proxy_image_mangak_and_manhuaus(client):
    from unittest.mock import patch, MagicMock

    mock_resp = MagicMock()
    mock_resp.read.return_value = b"fake-image"
    mock_resp.headers = {"Content-Type": "image/webp"}
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        # 1. Mangak image proxy has Referer: https://mangak.io/
        res = client.get("/api/proxy-image?url=https://rx.qvzra.org/image.webp")
        assert res.status_code == 200
        req = mock_urlopen.call_args[0][0]
        assert req.headers.get("Referer") == "https://mangak.io/"

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        with patch("manhuaus_provider.get_cached_clearance", return_value="fake_cf_token"):
            # 2. Manhuaus image proxy has cf_clearance Cookie and User-Agent
            res = client.get("/api/proxy-image?url=https://img.manhuaus.com/image.webp")
            assert res.status_code == 200
            req = mock_urlopen.call_args[0][0]
            assert req.headers.get("Referer") == "https://manhuaus.com/"
            assert "fake_cf_token" in req.headers.get("Cookie", "")


def test_manhuaus_add_and_update(client):
    from unittest.mock import patch

    fake_data = {
        "status": "ok",
        "images": ["https://img.manhuaus.com/1.webp", "https://img.manhuaus.com/2.webp"],
        "chapter": 278,
        "next": {"number": 279, "url": "https://manhuaus.com/manga/test/chapter-279/"},
        "prev": {"number": 277, "url": "https://manhuaus.com/manga/test/chapter-277/"}
    }

    with patch("manhuaus_provider.get_manhuaus_chapter_data", return_value=fake_data):
        res = client.post("/api/manhuas", json={
            "title": "Worthless Profession",
            "urlTemplate": "https://manhuaus.com/manga/worthless-profession-dragon-tamer/chapter-278/",
            "currentChapter": 278
        })
        assert res.status_code == 200
        item = res.get_json()["item"]
        assert item["currentChapter"] == 278
        assert item["urlTemplate"] == "https://manhuaus.com/manga/worthless-profession-dragon-tamer/chapter-{chapter}/"
        assert item["nextChapter"]["number"] == 279
        item_id = item["id"]

        # Delta +1
        delta_res = client.patch(f"/api/manhuas/{item_id}", json={"delta": 1})
        assert delta_res.status_code == 200
        assert delta_res.get_json()["item"]["currentChapter"] == 279


def test_get_manhuas_sorted_by_favorite_and_custom_order(client):
    items = [
        {"id": 1, "title": "Obra Comum A", "urlTemplate": "https://example.com/{chapter}", "currentChapter": 10, "updatedAt": 100, "isFavorite": False, "customOrder": 2},
        {"id": 2, "title": "Obra Favorita 1", "urlTemplate": "https://example.com/{chapter}", "currentChapter": 20, "updatedAt": 50, "isFavorite": True, "customOrder": 1},
        {"id": 3, "title": "Obra Comum B", "urlTemplate": "https://example.com/{chapter}", "currentChapter": 30, "updatedAt": 150, "isFavorite": False, "customOrder": 0},
        {"id": 4, "title": "Obra Favorita 0", "urlTemplate": "https://example.com/{chapter}", "currentChapter": 40, "updatedAt": 80, "isFavorite": True, "customOrder": 0},
    ]
    with open(server.DB_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f)

    res = client.get("/api/manhuas")
    assert res.status_code == 200
    data = res.get_json()
    ids = [m["id"] for m in data]
    assert ids == [4, 2, 3, 1]






