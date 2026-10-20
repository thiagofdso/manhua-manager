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



