import pytest

def test_web_index_contains_last_chapter_and_notification_elements():
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Campos nos formulários
    assert 'data-day' in html
    assert 'id="lastChapter"' in html
    assert 'id="isHiatus"' in html
    assert 'id="editLastChapter"' in html
    assert 'id="editIsHiatus"' in html

    # Elementos de notificação
    assert 'id="notifBell"' in html
    assert 'id="notificationBadge"' in html
    assert 'id="notificationModal"' in html
    assert 'id="btnTriggerManualCheck"' in html


def test_web_index_contains_download_last_chapter_validation():
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Validação no startBatchDownload e ajuste de max no openDownloadModal
    assert "m.lastChapter != null" in html
    assert "ultrapassar o último episódio disponível" in html

def test_import_elements_in_html():
    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()
    assert "openImportModal()" in content
    assert 'id="importModal"' in content
    assert 'id="importDomainSelect"' in content
    assert 'id="importSelectAll"' in content
    assert 'id="btnConfirmImport"' in content

