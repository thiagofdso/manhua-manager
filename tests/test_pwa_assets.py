# tests/test_pwa_assets.py
import pytest
import server
import os

@pytest.fixture
def client():
    server.app.config["TESTING"] = True
    with server.app.test_client() as client:
        yield client

def test_index_html_exists_and_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Manhua Tracker" in res.data
    assert b"manifest.json" in res.data

def test_manifest_and_sw_served(client):
    res_manifest = client.get("/manifest.json")
    assert res_manifest.status_code == 200
    assert b"Manhua Tracker" in res_manifest.data

    res_sw = client.get("/sw.js")
    assert res_sw.status_code == 200

def test_icons_exist(client):
    res_192 = client.get("/icon-192.png")
    assert res_192.status_code == 200
    res_512 = client.get("/icon-512.png")
    assert res_512.status_code == 200

def test_embedded_reader_and_edit_modal_in_index(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "readerView" in html
    assert "editModal" in html
    assert "openReader" in html
    assert "openEditModal" in html
    assert "iframe" in html
