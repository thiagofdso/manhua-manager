# tests/test_service_and_shortcut.py
import os

def test_app_script_exists():
    script = os.path.join(os.path.dirname(__file__), "..", "app.sh")
    assert os.path.exists(script), "app.sh must exist"
    assert os.access(script, os.X_OK), "app.sh must be executable"

def test_service_template_exists():
    service_file = os.path.join(os.path.dirname(__file__), "..", "manhua-manager.service")
    assert os.path.exists(service_file), "manhua-manager.service must exist"
    content = open(service_file, "r", encoding="utf-8").read()
    assert "ExecStart=" in content
    assert "server.py" in content
    assert "Restart=always" in content

def test_desktop_shortcut_content():
    desktop_file = os.path.expanduser("~/Área de trabalho/manhua-tracker.desktop")
    if os.path.exists(os.path.expanduser("~/Área de trabalho")):
        assert os.path.exists(desktop_file), "Desktop shortcut must exist"
        content = open(desktop_file, "r", encoding="utf-8").read()
        assert "[Desktop Entry]" in content
        assert "Name=Manhua Tracker" in content
        assert "http://localhost:5000" in content
