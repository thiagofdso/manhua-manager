"""Manhuaus Provider for Manhua Manager.

Handles chapter data extraction, navigation, and proxying for manhuaus.com.
"""

import os
import json
import re
import shutil
import subprocess
from typing import Optional, Dict, Any, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRAPER_SCRIPT = os.path.join(BASE_DIR, "manhuaus_extractor.mjs")
CLEARANCE_FILE = os.path.join(BASE_DIR, ".cache", "manhuaus_clearance.txt")


def is_manhuaus_url(url: str) -> bool:
    return "manhuaus.com" in url.lower()


def parse_manhuaus_url(url: str) -> Tuple[Optional[str], Optional[int]]:
    """Extracts (slug, chapter_number) from a manhuaus.com chapter or manga URL."""
    m_ch = re.search(r'/manga/([^/]+)/chapter-(\d+)', url, re.IGNORECASE)
    if m_ch:
        return m_ch.group(1), int(m_ch.group(2))

    m_title = re.search(r'/manga/([^/]+)', url, re.IGNORECASE)
    if m_title:
        return m_title.group(1), None

    return None, None


def get_cached_clearance() -> Optional[str]:
    """Reads cached cf_clearance cookie value if available."""
    if os.path.exists(CLEARANCE_FILE):
        try:
            with open(CLEARANCE_FILE, "r", encoding="utf-8") as f:
                val = f.read().strip()
                if val:
                    return val
        except Exception:
            pass
    return None


def get_manhuaus_chapter_data(target_url: str) -> Dict[str, Any]:
    """Executes manhuaus_extractor.mjs in Xvfb and returns the chapter data."""
    if not os.path.exists(SCRAPER_SCRIPT):
        raise FileNotFoundError(f"Extractor script not found: {SCRAPER_SCRIPT}")

    has_xvfb = shutil.which("xvfb-run") is not None
    if has_xvfb:
        cmd = ["xvfb-run", "-a", "node", SCRAPER_SCRIPT, target_url]
    else:
        cmd = ["node", SCRAPER_SCRIPT, target_url]

    res = subprocess.run(cmd, capture_output=True, text=True, timeout=50)
    if res.returncode != 0:
        err_msg = res.stderr.strip() or res.stdout.strip() or "Unknown error"
        raise RuntimeError(f"Manhuaus extractor failed with code {res.returncode}: {err_msg}")

    stdout = res.stdout.strip()
    for line in stdout.splitlines()[::-1]:
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                return {
                    "status": "ok",
                    "images": data.get("images", []),
                    "chapter": data.get("number"),
                    "next": data.get("next"),
                    "prev": data.get("prev"),
                    "clearance": data.get("clearance")
                }
            except json.JSONDecodeError:
                continue

    raise ValueError(f"Could not parse JSON from extractor output: {stdout[:300]}")
