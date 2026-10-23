"""Comix Provider for Manhua Manager.

Handles chapter data extraction, navigation, and proxying for comix.to.
"""

import os
import json
import re
import shutil
import subprocess
from typing import Optional, Dict, Any, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRAPER_SCRIPT = os.path.join(BASE_DIR, "comix_extractor.mjs")


def is_comix_url(url: str) -> bool:
    return "comix.to" in url.lower()


def parse_comix_url(url: str) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    """Extracts (slug, chapter_id, chapter_number) from a comix.to chapter or title URL."""
    m_ch = re.search(r'/title/([^/]+)/(\d+)-chapter-(\d+)', url)
    if m_ch:
        return m_ch.group(1), int(m_ch.group(2)), int(m_ch.group(3))

    m_title = re.search(r'/title/([^/]+)', url)
    if m_title:
        return m_title.group(1), None, None

    return None, None, None


def get_comix_chapter_data(target_url: str) -> Dict[str, Any]:
    """Executes comix_extractor.mjs in Xvfb and returns the chapter data."""
    if not os.path.exists(SCRAPER_SCRIPT):
        raise FileNotFoundError(f"Extractor script not found: {SCRAPER_SCRIPT}")

    has_xvfb = shutil.which("xvfb-run") is not None
    if has_xvfb:
        cmd = ["xvfb-run", "-a", "node", SCRAPER_SCRIPT, target_url]
    else:
        cmd = ["node", SCRAPER_SCRIPT, target_url]

    res = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
    if res.returncode != 0:
        err_msg = res.stderr.strip() or res.stdout.strip() or "Unknown error"
        raise RuntimeError(f"Comix extractor failed with code {res.returncode}: {err_msg}")

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
                    "chapterId": data.get("id"),
                    "next": data.get("next"),
                    "prev": data.get("prev"),
                }
            except json.JSONDecodeError:
                continue

    raise ValueError(f"Could not parse JSON from extractor output: {stdout[:300]}")
